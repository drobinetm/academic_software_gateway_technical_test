"""FastAPI application entry point."""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.api.routes import auth as auth_routes
from src.api.routes import clients as clients_routes
from src.api.routes import interests as interests_routes
from src.core.config import Settings, get_settings
from src.core.exceptions import GatewayError, UpstreamUnavailableError
from src.core.logging import configure_logging, get_logger, request_id_ctx_var
from src.db.mongodb import ensure_indexes
from src.services.innovasoft_client import InnovasoftClient

logger = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request_id and emit structured access logs."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
        token = request_id_ctx_var.set(request_id)
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request_failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            raise
        else:
            duration_ms = (time.perf_counter() - start) * 1000
            response.headers["X-Request-Id"] = request_id
            logger.info(
                "request_completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            return response
        finally:
            request_id_ctx_var.reset(token)


def _build_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.log_level)
        logger.info(
            "startup",
            extra={
                "environment": settings.environment,
                "base_url": settings.innovasoft_base_url,
            },
        )

        http_client = httpx.AsyncClient(timeout=settings.api_timeout_seconds)
        mongo_client = AsyncIOMotorClient(settings.mongodb_uri)
        database = mongo_client[settings.mongodb_database]

        app.state.http_client = http_client
        app.state.mongodb_client = mongo_client
        app.state.mongodb_database = database
        app.state.innovasoft_client = InnovasoftClient(
            http_client,
            settings.innovasoft_base_url,
            settings.api_timeout_seconds,
        )

        try:
            await ensure_indexes(database)
        except Exception:  # pragma: no cover
            logger.exception("index_creation_failed")

        try:
            yield
        finally:
            logger.info("shutdown")
            await http_client.aclose()
            mongo_client.close()

    return lifespan


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(UpstreamUnavailableError)
    async def _upstream_handler(_: Request, exc: UpstreamUnavailableError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
        )

    @app.exception_handler(GatewayError)
    async def _gateway_handler(_: Request, exc: GatewayError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "code": "validation_error",
                "errors": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", extra={"error_type": type(exc).__name__})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error", "code": "internal_error"},
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Innovasoft Proxy Gateway",
        version="0.1.0",
        description="API Gateway between the React frontend and the Innovasoft API.",
        lifespan=_build_lifespan(settings),
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-Id"],
        )
    app.add_middleware(RequestContextMiddleware)

    _register_exception_handlers(app)

    app.include_router(auth_routes.router)
    app.include_router(clients_routes.router)
    app.include_router(interests_routes.router)

    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()
