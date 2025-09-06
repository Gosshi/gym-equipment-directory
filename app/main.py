from fastapi import FastAPI
import os

from app.routers import gyms
from app.api.routers.meta import router as meta_router


app = FastAPI(title="Gym Equipment Directory")

@app.get("/health")
def health():
    return {"status": "ok", "env": os.getenv("APP_ENV", "dev")}

app.include_router(gyms.router)
app.include_router(meta_router)