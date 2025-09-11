from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    # Normalize to a consistent JSON body
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def _validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Keep simple, unified error message (avoid verbose FastAPI default list)
    return JSONResponse(status_code=422, content={"detail": "Unprocessable Entity"})


def _unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    # Hide internal details by default
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


def install(app) -> None:
    # Register centralized exception handlers
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
