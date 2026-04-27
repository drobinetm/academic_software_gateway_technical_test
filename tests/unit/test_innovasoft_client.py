"""Tests for the InnovasoftClient."""

from __future__ import annotations

import httpx
import pytest

from src.core.exceptions import UpstreamUnavailableError
from src.services.innovasoft_client import InnovasoftClient

BASE_URL = "https://upstream.test/Api/"


@pytest.mark.asyncio
async def test_url_building_strips_leading_slash(respx_mock):
    route = respx_mock.post("https://upstream.test/Api/api/Authenticate/login").mock(
        return_value=httpx.Response(200, json={"token": "abc"})
    )
    async with httpx.AsyncClient() as http:
        client = InnovasoftClient(http, BASE_URL, timeout=5)
        status_code, body, _ = await client.login({"username": "u", "password": "p"})
    assert status_code == 200
    assert b'"token"' in body
    assert route.called


@pytest.mark.asyncio
async def test_bearer_token_forwarded(respx_mock):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json=[])

    respx_mock.post("https://upstream.test/Api/api/Cliente/Listado").mock(side_effect=handler)
    async with httpx.AsyncClient() as http:
        client = InnovasoftClient(http, BASE_URL, timeout=5)
        await client.list_clients({"usuarioId": "u"}, bearer_token="tok-123")
    assert captured["auth"] == "Bearer tok-123"


@pytest.mark.asyncio
async def test_no_bearer_when_not_provided(respx_mock):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json=[])

    respx_mock.get("https://upstream.test/Api/api/Intereses/Listado").mock(side_effect=handler)
    async with httpx.AsyncClient() as http:
        client = InnovasoftClient(http, BASE_URL, timeout=5)
        await client.list_interests(bearer_token=None)
    assert captured["auth"] is None


@pytest.mark.asyncio
async def test_timeout_maps_to_upstream_unavailable(respx_mock):
    respx_mock.post("https://upstream.test/Api/api/Authenticate/login").mock(
        side_effect=httpx.TimeoutException("boom")
    )
    async with httpx.AsyncClient() as http:
        client = InnovasoftClient(http, BASE_URL, timeout=1)
        with pytest.raises(UpstreamUnavailableError) as exc:
            await client.login({"username": "u", "password": "p"})
    assert exc.value.status_code == 504
    assert exc.value.code == "upstream_timeout"


@pytest.mark.asyncio
async def test_network_error_maps_to_upstream_unavailable(respx_mock):
    respx_mock.post("https://upstream.test/Api/api/Authenticate/login").mock(
        side_effect=httpx.ConnectError("refused")
    )
    async with httpx.AsyncClient() as http:
        client = InnovasoftClient(http, BASE_URL, timeout=1)
        with pytest.raises(UpstreamUnavailableError) as exc:
            await client.login({"username": "u", "password": "p"})
    assert exc.value.status_code == 502
    assert exc.value.code == "upstream_unavailable"


@pytest.mark.asyncio
async def test_response_headers_filtered(respx_mock):
    respx_mock.post("https://upstream.test/Api/api/Authenticate/login").mock(
        return_value=httpx.Response(
            200,
            json={"token": "abc"},
            headers={"connection": "keep-alive", "x-keep": "1"},
        )
    )
    async with httpx.AsyncClient() as http:
        client = InnovasoftClient(http, BASE_URL, timeout=5)
        _, _, headers = await client.login({"username": "u", "password": "p"})
    lowered = {k.lower(): v for k, v in headers.items()}
    assert "connection" not in lowered
    assert "transfer-encoding" not in lowered
    assert lowered.get("x-keep") == "1"
