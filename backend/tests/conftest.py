import asyncio
import importlib
import os
import random
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import Any

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config as AlembicConfig
from dotenv import load_dotenv
from faker import Faker
from freezegun import freeze_time
from httpx import ASGITransport, AsyncClient, Request, Response
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

load_dotenv(".env.test", override=False)

TEST_DB_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
if not TEST_DB_URL:
    raise RuntimeError(
        "Set TEST_DATABASE_URL or DATABASE_URL for backend tests (postgresql+asyncpg://...)"
    )

os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("SEED_TEST_MODE", "1")

import app.db as app_db  # noqa: E402
from app.db import get_async_session  # noqa: E402
from app.main import create_app  # noqa: E402


@dataclass
class HttpExchangeRecorder:
    last_request: Request | None = None
    last_response: Response | None = None

    async def on_request(self, request: Request) -> None:
        self.last_request = request

    async def on_response(self, response: Response) -> None:
        await response.aread()
        self.last_response = response


def _make_sync_url(async_url: str) -> str:
    url = make_url(async_url)
    if "+asyncpg" in url.drivername:
        url = url.set(drivername=url.drivername.replace("+asyncpg", "+psycopg2"))
    return str(url)


async def _reset_schema(db_url: str) -> None:
    engine = create_async_engine(
        db_url,
        future=True,
        pool_pre_ping=True,
        poolclass=NullPool,
    )
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def frozen_time() -> Iterator[None]:
    with freeze_time("2025-01-01T00:00:00Z"):
        yield


@pytest.fixture(scope="session")
def db_url() -> str:
    return TEST_DB_URL


@pytest.fixture(scope="session")
def apply_migrations(db_url: str, frozen_time: None) -> Iterator[None]:
    asyncio.run(_reset_schema(db_url))
    cfg = AlembicConfig("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", _make_sync_url(db_url))
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    yield
    asyncio.run(_reset_schema(db_url))


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_engine(db_url: str, apply_migrations: None) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        db_url,
        future=True,
        pool_pre_ping=True,
        poolclass=NullPool,
    )
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    app_db.engine = engine
    app_db.SessionLocal = session_factory
    try:
        import app.api.deps as api_deps  # noqa: PLC0415

        api_deps.SessionLocal = session_factory
    except Exception:  # pragma: no cover - optional legacy deps
        pass
    try:
        import app.deps as legacy_deps  # noqa: PLC0415

        legacy_deps.SessionLocal = session_factory
    except Exception:  # pragma: no cover - optional legacy deps
        pass
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def seed_database(db_engine: AsyncEngine) -> None:
    import scripts.seed as seed_script

    result = seed_script.main([])
    if result != 0:
        raise RuntimeError(f"Seed script failed with exit code {result}")


@pytest.fixture(scope="session")
def fastapi_app(seed_database: None) -> Any:
    return create_app()


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest.fixture(scope="session")
def faker() -> Faker:
    faker = Faker("ja_JP")
    faker.seed_instance(20250101)
    random.seed(20250101)
    return faker


@pytest.fixture(scope="function")
def http_recorder(request: pytest.FixtureRequest) -> HttpExchangeRecorder:
    recorder = HttpExchangeRecorder()
    request.node._http_exchange = recorder  # type: ignore[attr-defined]
    return recorder


@pytest.fixture(scope="function", autouse=True)
def sql_debug(request: pytest.FixtureRequest, db_engine: AsyncEngine) -> Iterator[None]:
    statements: list[tuple[str, Any]] = []

    def _listener(conn, cursor, statement, parameters, context, executemany) -> None:  # noqa: ANN001
        statements.append((statement, parameters))

    event.listen(db_engine.sync_engine, "after_cursor_execute", _listener)
    request.node._sql_statements = statements  # type: ignore[attr-defined]
    try:
        yield
    finally:
        event.remove(db_engine.sync_engine, "after_cursor_execute", _listener)


@pytest_asyncio.fixture(loop_scope="function")
async def app_client(
    fastapi_app: Any,
    db_session: AsyncSession,
    http_recorder: HttpExchangeRecorder,
) -> AsyncIterator[AsyncClient]:
    app = fastapi_app
    os.environ.setdefault("SCORE_W_FRESH", "0.6")
    os.environ.setdefault("SCORE_W_RICH", "0.4")
    try:
        import app.services.scoring as scoring_module

        importlib.reload(scoring_module)
    except Exception:  # pragma: no cover - defensive reload guard
        pass

    async def _override_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_async_session] = _override_session
    event_hooks = {
        "request": [http_recorder.on_request],
        "response": [http_recorder.on_response],
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        event_hooks=event_hooks,
    ) as client:
        yield client
    app.dependency_overrides.clear()


def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[object]) -> None:
    if call.when != "call" or call.excinfo is None:
        return

    statements = getattr(item, "_sql_statements", None)
    if statements:
        print("\n--- SQL statements (last 20) ---")
        for statement, params in statements[-20:]:
            print(statement)
            if params:
                print(f"params={params}")

    recorder: HttpExchangeRecorder | None = getattr(item, "_http_exchange", None)
    if recorder and (recorder.last_request or recorder.last_response):
        print("\n--- HTTP exchange ---")
        if recorder.last_request:
            req = recorder.last_request
            print(f">>> {req.method} {req.url}")
            if req.content:
                try:
                    body = req.content.decode()
                except Exception:  # pragma: no cover - decoding fallback
                    body = str(req.content)
                print(f"Request body: {body}")
        if recorder.last_response:
            resp = recorder.last_response
            print(f"<<< {resp.status_code} {resp.reason_phrase}")
            text_body = resp.text
            if text_body:
                print(f"Response body: {text_body}")
