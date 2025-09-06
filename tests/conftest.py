import os
import asyncio
from datetime import datetime
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import get_async_session

# pytest-asyncio: use strict mode
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def db_url():
    url = os.getenv("DATABASE_URL")
    if not url or "+asyncpg" not in url:
        # デフォルト（ローカル実行用）
        url = "postgresql+asyncpg://postgres:postgres@localhost:5432/gymdb"
    return url

@pytest.fixture(scope="session")
def async_engine(db_url):
    engine = create_async_engine(db_url, future=True)
    return engine

@pytest.fixture
async def session(async_engine):
    # 各テストをトランザクションで隔離
    async with async_engine.connect() as conn:
        trans = await conn.begin()
        try:
            async_session = AsyncSession(bind=conn, expire_on_commit=False)
            yield async_session
        finally:
            await async_session.close()
            await trans.rollback()

@pytest.fixture(autouse=True)
def override_session_dependency(session):
    async def _get_session_override():
        yield session
    app.dependency_overrides[get_async_session] = _get_session_override
    yield
    app.dependency_overrides.pop(get_async_session, None)
