"""Integration test fixtures that boot the app against a Postgres database."""

from __future__ import annotations

import contextlib
import importlib
import os
import sys
from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio

from scripts.seed_min_test import seed_minimal_dataset


@pytest_asyncio.fixture
async def integration_client() -> AsyncIterator[httpx.AsyncClient]:
    """Provide an AsyncClient wired to the FastAPI app using TEST_DATABASE_URL."""
    test_url = os.getenv("TEST_DATABASE_URL")
    if not test_url:
        pytest.skip("TEST_DATABASE_URL is required for integration tests")

    os.environ["DATABASE_URL"] = test_url
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("TESTING", "1")
    os.environ.setdefault("SENTRY_DSN", "")
    os.environ.setdefault("SCORE_W_FRESH", "0.6")
    os.environ.setdefault("SCORE_W_RICH", "0.4")

    # Reload DB/session providers to ensure they use the test database URL.
    db_module = sys.modules.get("app.db")
    if db_module is not None:
        old_engine = getattr(db_module, "engine", None)
        if old_engine is not None:
            try:
                old_engine.sync_engine.dispose()
            except Exception:  # noqa: BLE001 - best effort cleanup
                pass
        importlib.reload(db_module)
    else:
        db_module = importlib.import_module("app.db")

    for module_name in ("app.api.deps",):
        module = sys.modules.get(module_name)
        if module is not None:
            importlib.reload(module)
        else:
            importlib.import_module(module_name)

    main_module = importlib.import_module("app.main")
    main_module = importlib.reload(main_module)
    app = main_module.create_app()

    # Ensure the database contains the minimal dataset required for integration checks.
    await seed_minimal_dataset(database_url=test_url)

    lifespan_ctx = app.router.lifespan_context
    if lifespan_ctx is None:
        @contextlib.asynccontextmanager
        async def _lifespan():
            await app.router.startup()
            try:
                yield
            finally:
                await app.router.shutdown()

        lifespan_manager = _lifespan()
    else:
        lifespan_manager = lifespan_ctx(app)

    async with lifespan_manager:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
