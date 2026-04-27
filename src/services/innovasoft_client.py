"""HTTP client that proxies all calls to the Innovasoft API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple
from urllib.parse import urljoin

import httpx
from fastapi import Request

from src.core.exceptions import UpstreamUnavailableError
from src.core.logging import get_logger

logger = get_logger(__name__)

# Hop-by-hop headers we never want to forward back to the client.
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

# Response is (status_code, body_bytes, headers_dict).
ProxyResponse = Tuple[int, bytes, Dict[str, str]]


@dataclass(frozen=True)
class _Endpoints:
    login: str = "api/Authenticate/login"
    register: str = "api/Authenticate/register"
    list_clients: str = "api/Cliente/Listado"
    get_client: str = "api/Cliente/Obtener/{id}"
    create_client: str = "api/Cliente/Crear"
    update_client: str = "api/Cliente/Actualizar"
    delete_client: str = "api/Cliente/Eliminar/{id}"
    list_interests: str = "api/Intereses/Listado"


ENDPOINTS = _Endpoints()


class InnovasoftClient:
    """Thin async wrapper around the Innovasoft REST API."""

    def __init__(self, http_client: httpx.AsyncClient, base_url: str, timeout: float) -> None:
        self._http = http_client
        self._base_url = base_url if base_url.endswith("/") else f"{base_url}/"
        self._timeout = timeout

    # ----- URL construction -------------------------------------------------

    def _build_url(self, path: str) -> str:
        # Strip leading slash so urljoin keeps the base path (e.g. /Api/).
        return urljoin(self._base_url, path.lstrip("/"))

    @staticmethod
    def _filter_response_headers(headers: Mapping[str, str]) -> Dict[str, str]:
        return {k: v for k, v in headers.items() if k.lower() not in _STRIPPED_RESPONSE_HEADERS}

    @staticmethod
    def _auth_headers(bearer_token: Optional[str]) -> Dict[str, str]:
        return {"Authorization": f"Bearer {bearer_token}"} if bearer_token else {}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        bearer_token: Optional[str] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> ProxyResponse:
        url = self._build_url(path)
        headers: Dict[str, str] = {"Accept": "application/json"}
        headers.update(self._auth_headers(bearer_token))
        if extra_headers:
            headers.update({k: v for k, v in extra_headers.items() if v is not None})

        try:
            response = await self._http.request(
                method,
                url,
                json=json_body,
                headers=headers,
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
            logger.warning("upstream_request_error", extra={"url": url, "method": method})
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

    # ----- Endpoints --------------------------------------------------------

    async def login(self, payload: Dict[str, Any]) -> ProxyResponse:
        return await self._request("POST", ENDPOINTS.login, json_body=payload)

    async def register(self, payload: Dict[str, Any]) -> ProxyResponse:
        return await self._request("POST", ENDPOINTS.register, json_body=payload)

    async def list_clients(self, payload: Dict[str, Any], bearer_token: str) -> ProxyResponse:
        return await self._request(
            "POST",
            ENDPOINTS.list_clients,
            json_body=payload,
            bearer_token=bearer_token,
        )

    async def get_client(self, client_id: str, bearer_token: str) -> ProxyResponse:
        return await self._request(
            "GET",
            ENDPOINTS.get_client.format(id=client_id),
            bearer_token=bearer_token,
        )

    async def create_client(self, payload: Dict[str, Any], bearer_token: str) -> ProxyResponse:
        return await self._request(
            "POST",
            ENDPOINTS.create_client,
            json_body=payload,
            bearer_token=bearer_token,
        )

    async def update_client(self, payload: Dict[str, Any], bearer_token: str) -> ProxyResponse:
        return await self._request(
            "POST",
            ENDPOINTS.update_client,
            json_body=payload,
            bearer_token=bearer_token,
        )

    async def delete_client(self, client_id: str, bearer_token: str) -> ProxyResponse:
        return await self._request(
            "DELETE",
            ENDPOINTS.delete_client.format(id=client_id),
            bearer_token=bearer_token,
        )

    async def list_interests(self, bearer_token: Optional[str] = None) -> ProxyResponse:
        return await self._request(
            "GET",
            ENDPOINTS.list_interests,
            bearer_token=bearer_token,
        )


def get_innovasoft_client(request: Request) -> InnovasoftClient:
    """FastAPI dependency: returns the shared InnovasoftClient from app.state."""
    client = getattr(request.app.state, "innovasoft_client", None)
    if client is None:
        raise RuntimeError("InnovasoftClient is not initialised on app.state")
    return client
