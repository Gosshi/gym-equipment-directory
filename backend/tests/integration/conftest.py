"""Integration test fixtures that boot the app against a Postgres database."""

from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def integration_client() -> Iterator[TestClient]:
    """Provide a TestClient wired to the FastAPI app using TEST_DATABASE_URL."""
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

    with TestClient(app) as client:
        yield client
