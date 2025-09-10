import os

from fastapi import FastAPI

from app.api.routers.gyms import router as gyms_router
from app.api.routers.meta import router as meta_router
from app.services.scoring import validate_weights


def create_app() -> FastAPI:
    app = FastAPI(title="Gym Equipment Directory")
    validate_weights()
    app.include_router(gyms_router)
    app.include_router(meta_router)
    return app


app = create_app()


@app.get("/health")
def health():
    return {"status": "ok", "env": os.getenv("APP_ENV", "dev")}
