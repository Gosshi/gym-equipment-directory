"""Minimal pytest fixtures for fast backend smoke tests."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure the FastAPI app boots in testing mode before it is imported.
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SENTRY_DSN", "")
# Ensure score weights sum to 1.0 even if the developer has custom env overrides set.
os.environ.setdefault("SCORE_W_FRESH", "0.6")
os.environ.setdefault("SCORE_W_RICH", "0.4")

from app.main import create_app  # noqa: E402 (import after env tweaks)


@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Return a FastAPI application instance configured for tests."""
    return create_app()


@pytest.fixture(scope="session")
def client(app: FastAPI) -> Iterator[TestClient]:
    """Provide a TestClient for smoke tests."""
    with TestClient(app) as test_client:
        yield test_client
