from __future__ import annotations

from fastapi import FastAPI

from dehalu.api.routes import router
from dehalu.core.settings import get_settings
from dehalu.telemetry.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(router)
    return app

