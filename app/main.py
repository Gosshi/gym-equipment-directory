import os

from fastapi import FastAPI

from app.api.routers.gyms import router as gyms_router
from app.api.routers.meta import router as meta_router

app = FastAPI(title="Gym Equipment Directory")


@app.get("/health")
def health():
    return {"status": "ok", "env": os.getenv("APP_ENV", "dev")}


app.include_router(gyms_router)
app.include_router(meta_router)
