import os

import structlog
from fastapi import FastAPI

from app.api.routers.admin_reports import router as admin_reports_router
from app.api.routers.equipments import router as equipments_router
from app.api.routers.gyms import router as gyms_router
from app.api.routers.healthz import router as healthz_router
from app.api.routers.me_favorites import router as me_favorites_router
from app.api.routers.meta import router as meta_router
from app.api.routers.readyz import router as readyz_router
from app.api.routers.suggest import router as suggest_router
from app.logging import setup_logging
from app.middleware.request_id import request_id_middleware
from app.services.scoring import validate_weights


def create_app() -> FastAPI:
    # Initialize structured logging first
    setup_logging()

    app = FastAPI(title="Gym Equipment Directory")
    validate_weights()
    # Request-ID middleware (JSON access log)
    app.middleware("http")(request_id_middleware)
    app.include_router(gyms_router)
    app.include_router(meta_router)
    app.include_router(equipments_router)
    app.include_router(suggest_router)
    app.include_router(healthz_router)
    app.include_router(readyz_router)
    app.include_router(admin_reports_router)
    app.include_router(me_favorites_router)
    # Startup log
    structlog.get_logger(__name__).info("app_startup", env=os.getenv("APP_ENV", "dev"))
    return app


app = create_app()


@app.get("/health")
def health():
    return {"status": "ok", "env": os.getenv("APP_ENV", "dev")}
