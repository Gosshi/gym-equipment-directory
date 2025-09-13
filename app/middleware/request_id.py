from __future__ import annotations

import time
import uuid
from collections.abc import Callable

import sentry_sdk
import structlog
from fastapi import Request, Response

REQUEST_ID_HEADER = "X-Request-ID"


async def request_id_middleware(request: Request, call_next: Callable) -> Response:
    """Attach/propagate Request-ID and emit structured access log.

    - Prefer inbound X-Request-ID; generate UUID4 if absent
    - Bind request_id, path, method to contextvars so service logs include it
    - Emit one-line access log event="http_request" with basic metrics
    - Always set X-Request-ID on the response
    """
    logger = structlog.get_logger(__name__)

    # Request-ID: inbound header or generated
    rid = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())

    # Bind context for this request
    structlog.contextvars.bind_contextvars(
        request_id=rid, path=request.url.path, method=request.method
    )

    # Enrich Sentry scope with request info (tags + extras)
    try:
        sentry_sdk.set_tag("request_id", rid)
        sentry_sdk.set_tag("path", request.url.path)
        sentry_sdk.set_tag("method", request.method)
        sentry_sdk.set_extra("request_id", rid)
        sentry_sdk.set_extra("path", request.url.path)
        sentry_sdk.set_extra("method", request.method)
    except Exception:
        # Never let Sentry instrumentation break request processing
        pass

    start_ns = time.perf_counter_ns()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        # Log exception in JSON with stack before re-raising
        end_ns = time.perf_counter_ns()
        duration_ms = (end_ns - start_ns) / 1_000_000.0
        client_ip = (request.client.host if request.client else None) or "-"
        logger.error(
            "http_request",
            request_id=rid,
            path=request.url.path,
            method=request.method,
            status=status_code,
            duration_ms=round(duration_ms, 3),
            client_ip=client_ip,
            exc_info=True,
        )
        structlog.contextvars.clear_contextvars()
        raise

    # Access log on success
    end_ns = time.perf_counter_ns()
    duration_ms = (end_ns - start_ns) / 1_000_000.0
    client_ip = (request.client.host if request.client else None) or "-"
    logger.info(
        "http_request",
        request_id=rid,
        path=request.url.path,
        method=request.method,
        status=status_code,
        duration_ms=round(duration_ms, 3),
        client_ip=client_ip,
    )

    # Always return the Request-ID header
    response.headers[REQUEST_ID_HEADER] = rid

    # Clear per-request bindings to avoid leakage across tasks
    structlog.contextvars.clear_contextvars()
    return response
