from __future__ import annotations

import os
from collections.abc import Callable
from typing import TypedDict

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from limits import parse as parse_limit
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
from slowapi import Limiter


class RateLimitInfo(TypedDict, total=False):
    method: str
    ip: str
    limit: str


# Slowapi initialization (kept for consistency and future extension)
# We still use "limits" directly here to support method-specific limits
# without touching routers. slowapi depends on limits and provides the
# canonical exception type to integrate with FastAPI handlers.
limiter = Limiter(key_func=lambda request: _client_ip(request))

# In-memory storage is sufficient for this app and test context. If you need
# distributed limits later, switch to Redis/Memcached storage.
_storage = MemoryStorage()
_rate = MovingWindowRateLimiter(_storage)


def _client_ip(request: Request) -> str:
    # Prefer X-Forwarded-For if present (first hop), fall back to ASGI client
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "local"


def _enabled() -> bool:
    # Enable by default unless TESTING is set.
    # Allow overriding with RATE_LIMIT_ENABLED=1 even when TESTING.
    if os.getenv("RATE_LIMIT_ENABLED") in {"1", "true", "TRUE"}:
        return True
    if os.getenv("TESTING"):
        return False
    return True


def _limit_for_method(method: str) -> str | None:
    m = method.upper()
    if m in {"GET", "HEAD"}:
        return "60/minute"
    if m in {"POST", "PATCH", "DELETE"}:
        return "30/minute"
    # Do not rate-limit OPTIONS (CORS preflight) or others
    return None


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    # Skip if disabled
    if not _enabled():
        return await call_next(request)

    limit_str = _limit_for_method(request.method)
    if not limit_str:
        return await call_next(request)

    key = f"ip:{_client_ip(request)}|m:{request.method.upper()}"
    limit = parse_limit(limit_str)

    allowed = _rate.hit(limit, key)
    if not allowed:
        info: RateLimitInfo = {
            "method": request.method.upper(),
            "ip": _client_ip(request),
            "limit": limit_str,
        }
        request.state.rate_limit_info = info
        # Respond directly with JSON 429 to avoid dependency on slowapi's handler
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "rate_limited",
                    "message": "Too Many Requests",
                    "detail": info,
                }
            },
        )

    response = await call_next(request)
    # Optional exposed headers for clients (remaining not provided by MovingWindow)
    response.headers.setdefault("X-RateLimit-Limit", limit_str)
    return response
