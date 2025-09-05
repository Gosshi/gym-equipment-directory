# app/api/main.py
from fastapi import FastAPI

# もし起動時のDB初期化やCORS設定などがあればこの上で import / 設定してください

from app.api.routers import gyms  # ← 追加（/gyms のルーター）

app = FastAPI(
    title="gym-equipment-directory API",
    version="0.1.0",
    description="Gyms search with equipment filters and pagination",
)

# ルーター登録
app.include_router(gyms.router)

# ヘルスチェックなど任意
@app.get("/healthz", tags=["meta"])
def healthcheck():
    return {"ok": True}
