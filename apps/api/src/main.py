from fastapi import FastAPI

from config import Settings, get_settings
from metrics import setup_metrics
from routers import health, reminders
from version import __version__


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    app = FastAPI(
        title=active_settings.app_name,
        version=__version__,
        root_path=active_settings.root_path,
    )

    setup_metrics(app)
    app.include_router(health.router)
    app.include_router(reminders.router)

    @app.get("/", tags=["root"])
    def read_root() -> dict[str, str]:
        return {
            "name": active_settings.app_name,
            "environment": active_settings.environment,
            "version": __version__,
        }

    return app


app = create_app()
