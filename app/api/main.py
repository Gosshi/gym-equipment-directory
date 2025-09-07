# app/api/main.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from app.api.routers import gyms, healthz, equipments, meta

# もし起動時のDB初期化やCORS設定などがあればこの上で import / 設定してください

openapi_tags = [
    {"name": "gyms", "description": "ジムの検索・詳細"},
    # {"name": "equipments", "description": "設備マスター"}  # あれば
]

app = FastAPI(
    title="Gym Equipment Directory API",
    version="0.1.0",
    description=(
        "ジムと設備の検索API（MVP）。\n"
        "- アプリは postgresql+asyncpg（非同期）\n"
        "- Alembic は postgresql+psycopg2（同期）\n"
        "- `gyms.last_verified_at_cached` はトリガーで自動更新\n"
    ),
    openapi_tags=openapi_tags,
)

tags_metadata = [
    {"name": "gyms", "description": "ジム検索および詳細取得"},
    {"name": "equipments", "description": "設備マスタの補完・検索"},
    {"name": "health", "description": "疎通・監視用"},
]
app.openapi_tags = tags_metadata

app.include_router(gyms.router, tags=["gyms"])
app.include_router(equipments.router, tags=["equipments"])
app.include_router(healthz.router, tags=["health"])
app.include_router(meta.router, tags=["meta"])


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
