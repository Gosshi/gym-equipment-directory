"""Retry / Backoff ユーティリティ (同期 & 非同期)。

環境変数 (デフォルト値):
    INGEST_RETRY_MAX_ATTEMPTS=3
    INGEST_RETRY_BASE_DELAY=0.5   # 秒
    INGEST_RETRY_MAX_DELAY=5.0    # 秒
    INGEST_RETRY_JITTER=0.2       # 0..jitter を追加

指数バックオフ: delay = min(base * (2 ** (attempt-1)), max_delay) + rand(0, jitter)

簡易利用例 (async):
    @async_retry()
    async def fetch():
        ...

同期版: sync_retry デコレータを使用。

将来改善:
    - 失敗種別ごとの待機戦略分岐
    - サーキットブレーカー連携
"""

from __future__ import annotations

import asyncio
import os
import random
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

import structlog

logger = structlog.get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
        if value <= 0:
            raise ValueError
        return value
    except ValueError:
        logger.warning("Invalid float for %s=%s; using default=%s", name, raw, default)
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
        if value < 1:
            raise ValueError
        return value
    except ValueError:
        logger.warning("Invalid int for %s=%s; using default=%s", name, raw, default)
        return default


def _compute_delay(attempt: int, base: float, max_delay: float, jitter: float) -> float:
    core = min(base * (2 ** (attempt - 1)), max_delay)
    return core + random.uniform(0.0, jitter)


def async_retry(
    *,
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float | None = None,
    jitter: float | None = None,
    retry_on: tuple[type[Exception], ...] = (Exception,),
    logger_=logger,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Async 関数用リトライデコレータ。"""
    max_attempts = max_attempts or _env_int("INGEST_RETRY_MAX_ATTEMPTS", 3)
    base_delay = base_delay or _env_float("INGEST_RETRY_BASE_DELAY", 0.5)
    max_delay = max_delay or _env_float("INGEST_RETRY_MAX_DELAY", 5.0)
    jitter = jitter or _env_float("INGEST_RETRY_JITTER", 0.2)

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_error: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retry_on as exc:  # type: ignore[misc]
                    last_error = exc
                    if attempt >= max_attempts:
                        break
                    delay = _compute_delay(attempt, base_delay, max_delay, jitter)
                    logger_.warning(
                        "async_retry attempt=%s/%s delay=%.2fs error=%s",
                        attempt,
                        max_attempts,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)
            assert last_error is not None
            raise last_error

        return wrapper

    return decorator


def sync_retry(
    *,
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float | None = None,
    jitter: float | None = None,
    retry_on: tuple[type[Exception], ...] = (Exception,),
    logger_=logger,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """同期関数用リトライデコレータ。"""
    max_attempts = max_attempts or _env_int("INGEST_RETRY_MAX_ATTEMPTS", 3)
    base_delay = base_delay or _env_float("INGEST_RETRY_BASE_DELAY", 0.5)
    max_delay = max_delay or _env_float("INGEST_RETRY_MAX_DELAY", 5.0)
    jitter = jitter or _env_float("INGEST_RETRY_JITTER", 0.2)

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_error: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as exc:  # type: ignore[misc]
                    last_error = exc
                    if attempt >= max_attempts:
                        break
                    delay = _compute_delay(attempt, base_delay, max_delay, jitter)
                    logger_.warning(
                        "sync_retry attempt=%s/%s delay=%.2fs error=%s",
                        attempt,
                        max_attempts,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
            assert last_error is not None
            raise last_error

        return wrapper

    return decorator


__all__ = [
    "async_retry",
    "sync_retry",
]
