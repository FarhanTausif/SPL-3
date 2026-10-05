from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dehalu.api.routes import router
from dehalu.core.settings import settings
from dehalu.state.database import create_tables


def create_app(create_schema_on_startup: bool = False) -> FastAPI:
    app = FastAPI(title="DeHalu API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    if create_schema_on_startup:

        @app.on_event("startup")
        def _startup() -> None:
            create_tables()

    return app


app = create_app()
