from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core import exceptions as domain_exceptions


def _http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    # Normalize to a consistent JSON body
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def _validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Keep simple, unified error message (avoid verbose FastAPI default list)
    return JSONResponse(status_code=422, content={"detail": "Unprocessable Entity"})


def _unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    # Hide internal details by default
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


def _domain_error_handler(status_code: int, default_detail: str):
    def _handler(_: Request, exc: domain_exceptions.DomainError) -> JSONResponse:
        detail = str(exc) or default_detail
        return JSONResponse(status_code=status_code, content={"detail": detail})

    return _handler


def install(app) -> None:
    # Register centralized exception handlers
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(
        domain_exceptions.NotFoundError, _domain_error_handler(404, "Not Found")
    )
    app.add_exception_handler(
        domain_exceptions.ValidationError, _domain_error_handler(400, "Bad Request")
    )
    app.add_exception_handler(
        domain_exceptions.ConflictError, _domain_error_handler(409, "Conflict")
    )
    app.add_exception_handler(
        domain_exceptions.InfrastructureError,
        _domain_error_handler(503, "Service Unavailable"),
    )
    app.add_exception_handler(Exception, _unhandled_exception_handler)
