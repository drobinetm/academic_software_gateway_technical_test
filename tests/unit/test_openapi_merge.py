from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from src.core.openapi import (
    fetch_upstream_openapi,
    load_cached_openapi,
    merge_gateway_openapi,
)

_UPSTREAM_SAMPLE = {
    "openapi": "3.0.1",
    "info": {"title": "ApiPruebaReactJs", "version": "v1"},
    "servers": [{"url": "/Api"}],
    "paths": {
        "/api/Authenticate/login": {
            "post": {"tags": ["Authenticate"], "responses": {"200": {}}}
        }
    },
    "components": {
        "schemas": {
            "Register": {
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "email": {"type": "string"},
                    "password": {"type": "string"},
                },
            }
        }
    },
}


def test_merge_rebrands_title_and_servers():
    result = merge_gateway_openapi(_UPSTREAM_SAMPLE)
    assert result["info"]["title"] == "Innovasoft S.A Proxy Gateway"
    assert result["servers"] == [{"url": "/"}]


def test_merge_injects_logout_endpoint():
    result = merge_gateway_openapi(_UPSTREAM_SAMPLE)
    logout = result["paths"]["/api/Authenticate/logout"]["post"]
    assert "Authenticate" in logout["tags"]
    assert "200" in logout["responses"]


def test_merge_reinforces_password_schema():
    result = merge_gateway_openapi(_UPSTREAM_SAMPLE)
    pwd = result["components"]["schemas"]["Register"]["properties"]["password"]
    assert pwd["minLength"] == 9
    assert pwd["maxLength"] == 20
    assert "pattern" in pwd


def test_merge_does_not_mutate_input():
    snapshot = json.dumps(_UPSTREAM_SAMPLE, sort_keys=True)
    merge_gateway_openapi(_UPSTREAM_SAMPLE)
    assert json.dumps(_UPSTREAM_SAMPLE, sort_keys=True) == snapshot


@pytest.mark.asyncio
async def test_fetch_upstream_returns_none_on_network_error(respx_mock):
    respx_mock.get("https://upstream.example/swagger.json").mock(
        side_effect=httpx.ConnectError("refused")
    )
    spec = await fetch_upstream_openapi(
        "https://upstream.example/swagger.json", timeout=1
    )
    assert spec is None


@pytest.mark.asyncio
async def test_fetch_upstream_returns_none_on_swagger_2(respx_mock):
    respx_mock.get("https://upstream.example/swagger.json").mock(
        return_value=httpx.Response(200, json={"swagger": "2.0", "paths": {}})
    )
    spec = await fetch_upstream_openapi(
        "https://upstream.example/swagger.json", timeout=1
    )
    assert spec is None


@pytest.mark.asyncio
async def test_fetch_upstream_returns_spec_on_success(respx_mock):
    respx_mock.get("https://upstream.example/swagger.json").mock(
        return_value=httpx.Response(200, json=_UPSTREAM_SAMPLE)
    )
    spec = await fetch_upstream_openapi(
        "https://upstream.example/swagger.json", timeout=1
    )
    assert spec is not None
    assert spec["openapi"] == "3.0.1"


def test_load_cached_openapi_missing_returns_none(tmp_path):
    spec = load_cached_openapi(str(tmp_path / "does-not-exist.json"))
    assert spec is None


def test_load_cached_openapi_invalid_returns_none(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert load_cached_openapi(str(bad)) is None


def test_load_cached_openapi_swagger_2_returns_none(tmp_path):
    bad = tmp_path / "swagger2.json"
    bad.write_text(json.dumps({"swagger": "2.0"}), encoding="utf-8")
    assert load_cached_openapi(str(bad)) is None


def test_load_cached_openapi_real_cache_loads():
    repo_root = Path(__file__).resolve().parents[2]
    cache_path = repo_root / "static" / "innovasoft_openapi_cache.json"
    if not cache_path.exists():
        pytest.skip("Cache not present in this checkout")
    spec = load_cached_openapi(str(cache_path))
    assert spec is not None
    assert spec["openapi"].startswith("3.")
