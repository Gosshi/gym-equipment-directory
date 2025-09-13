from __future__ import annotations

from collections.abc import Callable

from fastapi import Request, Response


async def security_headers_middleware(request: Request, call_next: Callable) -> Response:
    """Attach basic security headers to every response.

    - X-Content-Type-Options: nosniff
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: geolocation=(self)
    """
    response = await call_next(request)
    headers = response.headers
    headers.setdefault("X-Content-Type-Options", "nosniff")
    headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    headers.setdefault("Permissions-Policy", "geolocation=(self)")
    return response
