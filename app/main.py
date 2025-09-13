import os

import sentry_sdk
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.starlette import StarletteIntegration
from slowapi.errors import RateLimitExceeded
from starlette.middleware.cors import CORSMiddleware

from app.api.routers.admin_reports import router as admin_reports_router
from app.api.routers.equipments import router as equipments_router
from app.api.routers.gyms import router as gyms_router
from app.api.routers.healthz import router as healthz_router
from app.api.routers.me_favorites import router as me_favorites_router
from app.api.routers.meta import router as meta_router
from app.api.routers.readyz import router as readyz_router
from app.api.routers.suggest import router as suggest_router
from app.logging import setup_logging
from app.middleware.rate_limit import rate_limit_middleware
from app.middleware.request_id import request_id_middleware
from app.middleware.security_headers import security_headers_middleware
from app.services.scoring import validate_weights


def create_app() -> FastAPI:
    # Initialize structured logging first
    setup_logging()

    # Initialize Sentry (no-op if DSN is missing)
    dsn = os.getenv("SENTRY_DSN")
    env = os.getenv("APP_ENV", "dev")
    release = os.getenv("RELEASE")
    # traces_sample_rate: clamp to [0.0, 0.2]
    try:
        rate_raw = float(os.getenv("SENTRY_TRACES_RATE", "0"))
    except ValueError:
        rate_raw = 0.0
    traces_rate = max(0.0, min(0.2, rate_raw))

    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            environment=env,
            release=release,
            integrations=[StarletteIntegration()],
            traces_sample_rate=traces_rate,
            send_default_pii=False,
        )

    app = FastAPI(title="Gym Equipment Directory")
    validate_weights()
    # Request-ID middleware (JSON access log)
    app.middleware("http")(request_id_middleware)
    # Security headers
    app.middleware("http")(security_headers_middleware)
    # Rate limiting (IP-based, method-specific)
    app.middleware("http")(rate_limit_middleware)

    # CORS from ALLOW_ORIGINS env (comma-separated)
    allow_origins = [o.strip() for o in os.getenv("ALLOW_ORIGINS", "").split(",") if o.strip()]
    if allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS", "HEAD"],
            allow_headers=["*"],
        )
    app.include_router(gyms_router)
    app.include_router(meta_router)
    app.include_router(equipments_router)
    app.include_router(suggest_router)
    app.include_router(healthz_router)
    app.include_router(readyz_router)
    app.include_router(admin_reports_router)
    app.include_router(me_favorites_router)

    # Simple health for tests and uptime checks
    @app.get("/health")
    def health():
        return {"status": "ok", "env": os.getenv("APP_ENV", "dev")}

    # Debug-only endpoint to raise an error (disabled in prod)
    if env != "prod":

        @app.get("/debug/error")
        def debug_error():  # pragma: no cover - behavior verified by 404 in prod test
            raise RuntimeError("intentional error for Sentry debug")

    # 429 handler: unified JSON {"error": {...}}
    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):  # type: ignore[unused-ignore]
        info = getattr(request.state, "rate_limit_info", None)
        if not isinstance(info, dict):
            info = {
                "method": request.method,
                "ip": (request.client.host if request.client else None) or "-",
                "limit": "-",
            }
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "rate_limited",
                    "message": "Too Many Requests",
                    "detail": info,
                }
            },
        )

    # Startup log
    structlog.get_logger(__name__).info("app_startup", env=os.getenv("APP_ENV", "dev"))
    # Also notify Sentry about startup (no-op if not initialized)
    try:
        sentry_sdk.capture_message("app_startup", level="info")
    except Exception:
        # Avoid any impact on app startup if Sentry fails
        pass
    return app


app = create_app()
