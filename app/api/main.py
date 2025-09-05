# app/api/main.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

# もし起動時のDB初期化やCORS設定などがあればこの上で import / 設定してください

from app.api.routers import gyms  # ← 追加（/gyms のルーター）

app = FastAPI(
    title="gym-equipment-directory API",
    version="0.1.0",
    description="Gyms search with equipment filters and pagination",
    contact={"name": "Your Team", "url": "https://example.com"},
    license_info={"name": "MIT"},
)

# ルーター登録
app.include_router(gyms.router)

# ヘルスチェックなど任意
@app.get("/healthz", tags=["meta"])
def healthcheck():
    return {"ok": True}
