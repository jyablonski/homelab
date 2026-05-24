from functools import lru_cache
import importlib.metadata

from authlib.integrations.base_client import OAuthError
from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from auth import (
    SESSION_NEXT_URL,
    SESSION_USER,
    auth_required_response,
    is_public_path,
    oauth_client,
    prefixed_path,
    safe_next_url,
    userinfo_from_token,
    validate_sso_settings,
)
from config import Settings, get_settings
from jobs_api import run_to_response
from kubernetes_runner import KubernetesRunnerClient
from metrics import setup_metrics
from runner_client import RunnerClient

templates = Jinja2Templates(directory="src/templates")


@lru_cache
def get_runner_client() -> RunnerClient:
    return KubernetesRunnerClient(settings=get_settings())


def _fastapi_version() -> str:
    try:
        return importlib.metadata.version("fastapi")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    validate_sso_settings(active_settings)
    app = FastAPI(title=active_settings.app_name)

    app.mount("/static", StaticFiles(directory="src/static"), name="static")
    setup_metrics(app)

    @app.middleware("http")
    async def require_sso_session(request: Request, call_next):
        if (
            not active_settings.sso_enabled
            or is_public_path(request.url.path)
            or request.session.get(SESSION_USER)
        ):
            return await call_next(request)
        return auth_required_response(request, active_settings)

    if active_settings.sso_enabled:
        app.add_middleware(
            SessionMiddleware,
            secret_key=active_settings.session_secret_key,
            same_site="lax",
            https_only=active_settings.oidc_callback_url.startswith("https://"),
        )

    @app.get("/healthz", tags=["health"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/auth/login", include_in_schema=False)
    async def auth_login(request: Request):
        if not active_settings.sso_enabled:
            return RedirectResponse(
                prefixed_path(active_settings, "/"), status_code=303
            )

        request.session[SESSION_NEXT_URL] = safe_next_url(
            active_settings,
            request.query_params.get("next"),
        )
        return await oauth_client(active_settings).authorize_redirect(
            request,
            active_settings.oidc_callback_url,
        )

    @app.get("/auth/callback", include_in_schema=False)
    async def auth_callback(request: Request):
        if not active_settings.sso_enabled:
            return RedirectResponse(
                prefixed_path(active_settings, "/"), status_code=303
            )

        try:
            token = await oauth_client(active_settings).authorize_access_token(request)
        except OAuthError:
            return RedirectResponse(
                prefixed_path(active_settings, "/auth/login"),
                status_code=303,
            )

        user = userinfo_from_token(token)
        if not user["sub"]:
            return RedirectResponse(
                prefixed_path(active_settings, "/auth/login"),
                status_code=303,
            )
        request.session[SESSION_USER] = user
        next_url = request.session.pop(
            SESSION_NEXT_URL,
            prefixed_path(active_settings, "/"),
        )
        return RedirectResponse(next_url, status_code=303)

    @app.get("/auth/logout", include_in_schema=False)
    def auth_logout(request: Request):
        if not active_settings.sso_enabled:
            return RedirectResponse(
                prefixed_path(active_settings, "/"), status_code=303
            )
        request.session.clear()
        return RedirectResponse(prefixed_path(active_settings, "/"), status_code=303)

    @app.get("/", response_class=HTMLResponse, tags=["ui"])
    def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "runnables.html",
            {
                "cluster_name": active_settings.cluster_name,
                "namespace": active_settings.namespace,
                "fastapi_version": _fastapi_version(),
                "url_prefix": active_settings.url_prefix.rstrip("/"),
                "api_jobs_url": (f"{active_settings.url_prefix.rstrip('/')}/api/jobs"),
                "current_user": request.session.get(SESSION_USER)
                if active_settings.sso_enabled
                else None,
            },
        )

    @app.get("/api/jobs", tags=["jobs"])
    def list_jobs(
        runner: RunnerClient = Depends(get_runner_client),
    ) -> list[dict[str, object]]:
        return runner.list_jobs()

    @app.get("/api/jobs/{app}/{name}/runs", tags=["jobs"])
    def list_job_runs(
        app: str,
        name: str,
        runner: RunnerClient = Depends(get_runner_client),
    ) -> list[dict[str, object]]:
        return runner.list_job_runs(app=app, name=name)

    @app.post("/api/jobs/{app}/{name}/run", tags=["jobs"])
    def run_job(
        app: str,
        name: str,
        runner: RunnerClient = Depends(get_runner_client),
    ) -> dict[str, object]:
        return runner.run_job(app=app, name=name)

    @app.get("/api/runnables", tags=["runnables"])
    def list_runnables(
        runner: RunnerClient = Depends(get_runner_client),
    ) -> list[dict[str, object]]:
        return [runnable.__dict__ for runnable in runner.list_runnables()]

    @app.get(
        "/api/runnables/{namespace}/{cronjob_name}/runs",
        tags=["runnables"],
    )
    def list_runs(
        namespace: str,
        cronjob_name: str,
        runner: RunnerClient = Depends(get_runner_client),
    ) -> list[dict[str, object]]:
        return [
            run.__dict__
            for run in runner.list_runs(namespace=namespace, cronjob_name=cronjob_name)
        ]

    @app.post(
        "/api/runnables/{namespace}/{cronjob_name}/runs",
        tags=["runnables"],
    )
    def run_runnable(
        namespace: str,
        cronjob_name: str,
        runner: RunnerClient = Depends(get_runner_client),
    ) -> dict[str, object]:
        run = runner.run(namespace=namespace, cronjob_name=cronjob_name)
        return run_to_response(run)

    @app.post("/runs", tags=["ui"])
    def run_from_form(
        request: Request,
        namespace: str = Form(),
        cronjob_name: str = Form(),
        runner: RunnerClient = Depends(get_runner_client),
    ) -> RedirectResponse:
        runner.run(namespace=namespace, cronjob_name=cronjob_name)
        return RedirectResponse(request.url_for("index"), status_code=303)

    return app


app = create_app()
