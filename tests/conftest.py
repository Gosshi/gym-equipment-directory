# tests/conftest.py
import importlib
import os
from collections.abc import Callable
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Import app after environment is configured so create_app reads correct DATABASE_URL
from app.main import app, create_app

# ==== 3) FastAPI 依存差し替え（使われ得る全候補を網羅） ====
# `app` / `create_app` は後で import する（下で環境変数を設定してから）
from app.models import Equipment, Gym, GymEquipment
from app.models.base import Base

# ==== 1) DSN を必須化（Postgresのみ） ====
# Load .env.test if available (pytest.ini env_file is not supported without plugin)
load_dotenv(".env.test", override=False)
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


@pytest.fixture
async def app_client(monkeypatch):
    # テスト用DBへ強制
    test_url = os.getenv("TEST_DATABASE_URL")
    if test_url:
        monkeypatch.setenv("DATABASE_URL", test_url)
    # スコア重みは合計1.0を強制（外部環境の影響を受けないよう固定）
    monkeypatch.setenv("SCORE_W_FRESH", "0.6")
    monkeypatch.setenv("SCORE_W_RICH", "0.4")
    # 既に import 済みの scoring モジュールを環境変数変更後の値で再読込
    try:
        import importlib as _imp

        import app.services.scoring as _scoring

        _imp.reload(_scoring)
    except Exception:
        pass
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ==== 2) Engine / Schema ====
@pytest_asyncio.fixture(scope="function")
async def engine():
    eng = create_async_engine(DB_URL, **_engine_kwargs(DB_URL))
    # モデルを確実に import してメタデータを埋める
    for m in ("source", "gym", "equipment", "gym_equipment", "report"):
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


# === ここから seed（autouse） ===


@pytest.fixture(scope="session", autouse=True)
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(autouse=True, scope="function")
async def seed_test_data(engine):
    """各テスト関数の:create_all直後に、同じengineに対してseedを流す。"""
    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with SessionLocal() as sess:
        # 既に入っていればスキップ
        exists = await sess.execute(
            Gym.__table__.select().where(Gym.slug == "dummy-funabashi-east")
        )
        if not exists.first():
            g1 = Gym(
                name="ダミージム 船橋イースト",
                slug="dummy-funabashi-east",
                pref="chiba",
                city="funabashi",
                address="千葉県船橋市…",
                last_verified_at_cached=datetime.utcnow() - timedelta(days=30),
            )
            g2 = Gym(
                name="ダミージム 船橋ウエスト",
                slug="dummy-funabashi-west",
                pref="chiba",
                city="funabashi",
                address="千葉県船橋市…",
                last_verified_at_cached=None,  # freshness=0 ケースもあった方が便利
            )
            sess.add_all([g1, g2])
            await sess.flush()

            # テストが使う典型スラッグ（bench-press / dumbbell）と衝突しないように seed-* にする
            e1 = Equipment(slug="seed-bench-press", name="ベンチプレス", category="free_weight")
            e2 = Equipment(slug="seed-lat-pulldown", name="ラットプルダウン", category="machine")
            sess.add_all([e1, e2])
            await sess.flush()

            sess.add_all(
                [
                    GymEquipment(gym_id=g1.id, equipment_id=e1.id),
                    GymEquipment(gym_id=g1.id, equipment_id=e2.id),
                    GymEquipment(gym_id=g2.id, equipment_id=e1.id),
                ]
            )
            await sess.commit()

    # Note: engine disposal is handled by the engine fixture's finalizer.
    # Do not dispose here; tests still need the active engine/session.
