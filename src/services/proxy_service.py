from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, TypeAlias
from urllib.parse import urljoin

import httpx
from fastapi import Request

from src.core.exceptions import StartupError, UpstreamUnavailableError
from src.core.logging import get_logger

if TYPE_CHECKING:  # pragma: no cover
    pass

logger = get_logger(__name__)

_STRIPPED_REQUEST_HEADERS = {
    "host",
    "content-length",
    "transfer-encoding",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "upgrade",
}

_STRIPPED_RESPONSE_HEADERS = {
    "content-length",
    "content-encoding",
    "transfer-encoding",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "upgrade",
}

ProxyResponse: TypeAlias = tuple[int, bytes, dict[str, str]]


class ProxyService:
    def __init__(
        self, http_client: httpx.AsyncClient, base_url: str, timeout: float
    ) -> None:
        self._http = http_client
        self._base_url = base_url if base_url.endswith("/") else f"{base_url}/"
        self._timeout = timeout

    def _build_url(self, path: str) -> str:
        # Strip leading slash so urljoin keeps the base path (e.g. /Api/).
        return urljoin(self._base_url, path.lstrip("/"))

    @staticmethod
    def _filter_request_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
        if not headers:
            return {}
        return {
            k: v
            for k, v in headers.items()
            if k.lower() not in _STRIPPED_REQUEST_HEADERS
        }

    @staticmethod
    def _filter_response_headers(headers: Mapping[str, str]) -> dict[str, str]:
        return {
            k: v
            for k, v in headers.items()
            if k.lower() not in _STRIPPED_RESPONSE_HEADERS
        }

    async def forward(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
    ) -> ProxyResponse:
        """Forward an arbitrary request to the upstream API.

        Args:
            method: HTTP verb (GET/POST/PUT/PATCH/DELETE).
            path: Path relative to the configured base URL (e.g.
                ``"api/Cliente/Listado"``).
            body: Raw request body to forward (already serialized).
            headers: Request headers from the caller. Transport headers are
                stripped before the upstream call.
            params: Optional query parameters.

        Returns:
            ``(status_code, body_bytes, response_headers)`` from the upstream.

        Raises:
            UpstreamUnavailableError: On connection errors (502) or timeouts (504).
        """
        url = self._build_url(path)
        forward_headers = self._filter_request_headers(headers)

        try:
            response = await self._http.request(
                method,
                url,
                content=body,
                headers=forward_headers,
                params=dict(params) if params else None,
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            logger.warning("upstream_timeout", extra={"url": url, "method": method})
            raise UpstreamUnavailableError(
                "Upstream request timed out",
                code="upstream_timeout",
                status_code=504,
            ) from exc
        except httpx.RequestError as exc:
            logger.warning(
                "upstream_request_error", extra={"url": url, "method": method}
            )
            raise UpstreamUnavailableError(
                "Upstream request failed",
                code="upstream_unavailable",
                status_code=502,
            ) from exc

        return (
            response.status_code,
            response.content,
            self._filter_response_headers(response.headers),
        )


def get_proxy_service(request: Request) -> ProxyService:
    service = getattr(request.app.state, "proxy_service", None)
    if service is None:
        raise StartupError("ProxyService is not initialised on app.state")
    return service
