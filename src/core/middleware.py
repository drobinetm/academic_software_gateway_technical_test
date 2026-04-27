import time
from collections.abc import Iterable
from dataclasses import dataclass

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.core.exceptions import RequestLogError
from src.core.logging import get_logger
from src.services.request_log_service import RequestLogService

logger = get_logger(__name__)


_DEFAULT_EXCLUDED_PATHS = frozenset({"/docs", "/redoc", "/openapi.json", "/health", "/favicon.ico"})


@dataclass(frozen=True, slots=True)
class _RequestContext:
    method: str
    path: str
    status_code: int
    duration_ms: float
    query: str | None
    request_size: int | None
    response_size: int | None
    client_ip: str | None
    user_agent: str | None


class HTTPRequestLogMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        excluded_paths: Iterable[str] | None = None,
    ) -> None:
        super().__init__(app)
        self._excluded = (
            frozenset(excluded_paths) if excluded_paths is not None else _DEFAULT_EXCLUDED_PATHS
        )

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        path = request.url.path
        if self._is_excluded(path):
            return await call_next(request)

        start = time.perf_counter()
        request_size = self._safe_int(request.headers.get("content-length"))
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        query = request.url.query or None

        status_code = 500
        response: Response | None = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 3)
            response_size = (
                self._safe_int(response.headers.get("content-length")) if response else None
            )
            ctx = _RequestContext(
                method=request.method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
                query=query,
                request_size=request_size,
                response_size=response_size,
                client_ip=client_ip,
                user_agent=user_agent,
            )
            await self._safe_persist(request, ctx)

    def _is_excluded(self, path: str) -> bool:
        return path in self._excluded

    @staticmethod
    def _safe_int(value: str | None) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    async def _safe_persist(request: Request, ctx: _RequestContext) -> None:
        service: RequestLogService | None = getattr(request.app.state, "request_log_service", None)
        if service is None:
            return
        try:
            await service.log(
                method=ctx.method,
                path=ctx.path,
                status_code=ctx.status_code,
                duration_ms=ctx.duration_ms,
                query=ctx.query,
                request_size=ctx.request_size,
                response_size=ctx.response_size,
                client_ip=ctx.client_ip,
                user_agent=ctx.user_agent,
            )
        except Exception as exc:  # pragma: no cover
            logger.exception(
                "request_log_middleware_failed",
                extra={"error": str(RequestLogError(str(exc)))},
            )
