# tests/conftest.py
import importlib
import os
from collections.abc import Callable

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# ==== 3) FastAPI 依存差し替え（使われ得る全候補を網羅） ====
from app.main import app  # DB_URL セット後に import
from app.models.base import Base

# ==== 1) DSN を必須化（Postgresのみ） ====
DB_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
assert DB_URL and DB_URL.startswith(("postgresql+asyncpg://", "postgresql+psycopg://")), (
    "Set TEST_DATABASE_URL like: postgresql+asyncpg://user:pass@host:port/gym_test"
)
# アプリ側も同じDSNを見る
os.environ["DATABASE_URL"] = DB_URL
os.environ["TESTING"] = "1"


def _engine_kwargs(_: str):
    # ループ跨ぎの事故を避けるため NullPool、pre_ping 有効
    return dict(future=True, echo=False, poolclass=NullPool, pool_pre_ping=True)


# ==== 2) Engine / Schema ====
@pytest_asyncio.fixture(scope="function")
async def engine():
    eng = create_async_engine(DB_URL, **_engine_kwargs(DB_URL))
    # モデルを確実に import してメタデータを埋める
    for m in ("source", "gym", "equipment", "gym_equipment"):
        try:
            importlib.import_module(f"app.models.{m}")
        except Exception:
            pass
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture(scope="function", name="session")
async def _session(engine):
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as s:
        yield s
        if s.in_transaction():
            await s.rollback()


def _install_overrides(app, session: AsyncSession):
    import importlib as _imp

    candidates: list[Callable] = []
    for modname in (
        "app.api.deps",
        "app.api.dependencies",
        "app.db",
        "app.database",
        "app.core.db",
        "app.infra.db",
        "app.api.routers.gyms",
        "app.api.routers.meta",
    ):
        try:
            m = _imp.import_module(modname)
        except Exception:
            continue
        # Depends で使われそうな関数名を総当たり
        for name in ("get_session", "get_db", "get_async_session", "get_db_session", "session_dep"):
            fn = getattr(m, name, None)
            if callable(fn):
                candidates.append(fn)
        # ベルト＆サスペンダー：モジュールが持つ engine / sessionmaker をテスト用へ付け替え
        for attr in ("engine", "async_engine", "engine_rw", "async_engine_rw"):
            if hasattr(m, attr):
                try:
                    setattr(m, attr, session.bind)
                except Exception:
                    pass
        for attr in ("SessionLocal", "AsyncSessionLocal", "async_session", "sessionmaker"):
            if hasattr(m, attr):
                try:
                    setattr(
                        m,
                        attr,
                        async_sessionmaker(
                            bind=session.bind, class_=AsyncSession, expire_on_commit=False
                        ),
                    )
                except Exception:
                    pass

    async def override_get_session():
        async with AsyncSession(bind=session.bind, expire_on_commit=False) as s2:
            yield s2

    for c in candidates:
        app.dependency_overrides[c] = override_get_session


@pytest_asyncio.fixture(autouse=True, scope="function")
async def _override_app_session(session):
    _install_overrides(app, session)
    try:
        yield
    finally:
        app.dependency_overrides.clear()
