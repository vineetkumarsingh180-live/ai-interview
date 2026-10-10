"""
Structured error handling: one JSON envelope (`ErrorResponse`) for every failure.

Services raise `ApiError` subclasses; framework and unexpected errors are converted here so no
response ever leaks a stack trace, SQL, or a bare text/plain 500.
"""

import logging
from typing import List, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("synapse.errors")

_STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    501: "not_implemented",
    503: "unavailable",
}


class ApiError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, detail: str, *, code: Optional[str] = None, status_code: Optional[int] = None):
        super().__init__(detail)
        self.detail = detail
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class NotFound(ApiError):
    status_code = 404
    code = "not_found"


class Conflict(ApiError):
    status_code = 409
    code = "conflict"


class ServiceUnavailable(ApiError):
    """A dependency (AI provider, database) cannot serve the request. Never answer with made-up data."""

    status_code = 503
    code = "unavailable"


def _body(detail: str, code: str, errors: Optional[List[dict]] = None) -> dict:
    out = {"detail": detail, "code": code}
    if errors:
        out["errors"] = errors
    return out


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status_code, content=_body(exc.detail, exc.code))

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(detail, _STATUS_CODES.get(exc.status_code, "error")),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        errors = []
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path")]
            errors.append({"field": ".".join(loc) or "request", "message": str(err.get("msg", "Invalid value"))})
        return JSONResponse(status_code=422, content=_body("Request validation failed", "validation_error", errors))

    @app.exception_handler(OperationalError)
    @app.exception_handler(InterfaceError)
    @app.exception_handler(DBAPIError)
    @app.exception_handler(OSError)
    async def _database_error(_: Request, exc: Exception):
        logger.error("Database error: %s", type(exc).__name__)
        return JSONResponse(
            status_code=503, content=_body("The database is unavailable.", "database_unavailable")
        )

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception):
        logger.exception("Unhandled error")
        return JSONResponse(status_code=500, content=_body("Internal server error", "internal_error"))
