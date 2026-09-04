"""Consistent error responses."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("market_detective.api")


class AppError(Exception):
    def __init__(self, detail: str, *, code: str = "error",
                 status_code: int = status.HTTP_400_BAD_REQUEST) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, detail: str = "Not found", *, code: str = "not_found") -> None:
        super().__init__(detail, code=code, status_code=status.HTTP_404_NOT_FOUND)


class ConflictError(AppError):
    def __init__(self, detail: str, *, code: str = "conflict") -> None:
        super().__init__(detail, code=code, status_code=status.HTTP_409_CONFLICT)


class AuthError(AppError):
    def __init__(self, detail: str = "Not authenticated", *, code: str = "unauthenticated") -> None:
        super().__init__(detail, code=code, status_code=status.HTTP_401_UNAUTHORIZED)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code,
                            content={"detail": exc.detail, "code": exc.code})

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Request validation failed", "code": "validation_error",
                     "errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error", "code": "internal_error"},
        )
