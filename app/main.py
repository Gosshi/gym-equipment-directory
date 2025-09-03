from fastapi import FastAPI
import os

from app.routers import gyms  # ← 追加

app = FastAPI(title="Gym Equipment Directory")

@app.get("/health")
def health():
    return {"status": "ok", "env": os.getenv("APP_ENV", "dev")}

app.include_router(gyms.router)  # ← 追加
