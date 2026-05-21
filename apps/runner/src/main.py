from functools import lru_cache
import importlib.metadata

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
    app = FastAPI(title=active_settings.app_name)
    app.mount("/static", StaticFiles(directory="src/static"), name="static")
    setup_metrics(app)

    @app.get("/healthz", tags=["health"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

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
