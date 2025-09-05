# app/api/main.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from app.api.routers import gyms

# もし起動時のDB初期化やCORS設定などがあればこの上で import / 設定してください

openapi_tags = [
    {"name": "gyms", "description": "ジムの検索・詳細"},
    # {"name": "equipments", "description": "設備マスター"}  # あれば
]

app = FastAPI(
    title="Gym Equipment Directory API",
    version="0.1.0",
    description="ジム設備検索API（MVP）",
    openapi_tags=openapi_tags,
)

app.include_router(gyms.router)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title, version=app.version, description=app.description, routes=app.routes
    )
    schema["servers"] = [{"url": "http://localhost:8000", "description": "Local"}]
    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi
# ヘルスチェックなど任意
@app.get("/healthz", tags=["meta"])
def healthcheck():
    return {"ok": True}