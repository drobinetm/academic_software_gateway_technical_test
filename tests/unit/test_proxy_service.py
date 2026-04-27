from __future__ import annotations

import httpx
import pytest

from src.core.exceptions import UpstreamUnavailableError
from src.services.proxy_service import ProxyService

BASE_URL = "https://upstream.test/Api/"


@pytest.mark.asyncio
async def test_forward_post_builds_url_and_returns_response(respx_mock):
    route = respx_mock.post("https://upstream.test/Api/api/Authenticate/login").mock(
        return_value=httpx.Response(200, json={"token": "abc"})
    )
    async with httpx.AsyncClient() as http:
        proxy = ProxyService(http, BASE_URL, timeout=5)
        status_code, body, _ = await proxy.forward(
            "POST", "api/Authenticate/login", body=b'{"u":"a"}'
        )
    assert status_code == 200
    assert b'"token"' in body
    assert route.called


@pytest.mark.asyncio
async def test_forward_get_passthrough(respx_mock):
    respx_mock.get("https://upstream.test/Api/api/Intereses/Listado").mock(
        return_value=httpx.Response(200, json=[])
    )
    async with httpx.AsyncClient() as http:
        proxy = ProxyService(http, BASE_URL, timeout=5)
        status_code, body, _ = await proxy.forward("GET", "api/Intereses/Listado")
    assert status_code == 200
    assert body == b"[]"


@pytest.mark.asyncio
async def test_forward_delete_passes_headers(respx_mock):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(204)

    respx_mock.delete("https://upstream.test/Api/api/Cliente/Eliminar/cli-1").mock(
        side_effect=handler
    )
    async with httpx.AsyncClient() as http:
        proxy = ProxyService(http, BASE_URL, timeout=5)
        status_code, _, _ = await proxy.forward(
            "DELETE",
            "api/Cliente/Eliminar/cli-1",
            headers={"Authorization": "Bearer tok-1"},
        )
    assert status_code == 204
    assert captured["auth"] == "Bearer tok-1"


@pytest.mark.asyncio
async def test_forward_strips_transport_headers(respx_mock):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        return httpx.Response(200, json={})

    respx_mock.post("https://upstream.test/Api/api/X").mock(side_effect=handler)
    async with httpx.AsyncClient() as http:
        proxy = ProxyService(http, BASE_URL, timeout=5)
        await proxy.forward(
            "POST",
            "api/X",
            body=b"{}",
            headers={
                "Host": "evil.example",
                "Connection": "keep-alive",
                "Content-Length": "999",
                "X-Keep": "1",
                "Authorization": "Bearer t",
            },
        )
    lowered = {k.lower(): v for k, v in captured["headers"].items()}
    assert "x-keep" in lowered
    assert lowered["authorization"] == "Bearer t"
    # httpx may set its own Host header, but our forwarded one mustn't be "evil.example".
    assert lowered.get("host") != "evil.example"
    # connection / content-length are managed by httpx, not by our forwarded headers.
    # Just ensure the caller's transport headers were not propagated as-is.


@pytest.mark.asyncio
async def test_forward_timeout_raises_upstream_unavailable(respx_mock):
    respx_mock.post("https://upstream.test/Api/api/x").mock(
        side_effect=httpx.TimeoutException("boom")
    )
    async with httpx.AsyncClient() as http:
        proxy = ProxyService(http, BASE_URL, timeout=1)
        with pytest.raises(UpstreamUnavailableError) as exc:
            await proxy.forward("POST", "api/x", body=b"{}")
    assert exc.value.status_code == 504
    assert exc.value.code == "upstream_timeout"


@pytest.mark.asyncio
async def test_forward_connect_error_raises_upstream_unavailable(respx_mock):
    respx_mock.post("https://upstream.test/Api/api/x").mock(
        side_effect=httpx.ConnectError("refused")
    )
    async with httpx.AsyncClient() as http:
        proxy = ProxyService(http, BASE_URL, timeout=1)
        with pytest.raises(UpstreamUnavailableError) as exc:
            await proxy.forward("POST", "api/x", body=b"{}")
    assert exc.value.status_code == 502
    assert exc.value.code == "upstream_unavailable"


@pytest.mark.asyncio
async def test_url_building_with_and_without_trailing_slash(respx_mock):
    """Both ``BASE`` and ``BASE/`` should produce the same final URL."""
    respx_mock.get("https://upstream.test/Api/api/x").mock(
        return_value=httpx.Response(200, json={})
    )
    async with httpx.AsyncClient() as http:
        proxy_with = ProxyService(http, "https://upstream.test/Api/", timeout=5)
        proxy_without = ProxyService(http, "https://upstream.test/Api", timeout=5)
        s1, _, _ = await proxy_with.forward("GET", "api/x")
        s2, _, _ = await proxy_without.forward("GET", "api/x")
    assert s1 == 200
    assert s2 == 200


@pytest.mark.asyncio
async def test_response_headers_filtered(respx_mock):
    respx_mock.post("https://upstream.test/Api/api/x").mock(
        return_value=httpx.Response(
            200,
            json={"ok": True},
            headers={"connection": "keep-alive", "x-keep": "1"},
        )
    )
    async with httpx.AsyncClient() as http:
        proxy = ProxyService(http, BASE_URL, timeout=5)
        _, _, headers = await proxy.forward("POST", "api/x", body=b"{}")
    lowered = {k.lower(): v for k, v in headers.items()}
    assert "connection" not in lowered
    assert "transfer-encoding" not in lowered
    assert lowered.get("x-keep") == "1"
