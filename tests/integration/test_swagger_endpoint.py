from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_openapi_json_returns_200(async_client):
    response = await async_client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["openapi"].startswith("3.")
    assert "paths" in spec


@pytest.mark.asyncio
async def test_swagger_ui_returns_200(async_client):
    response = await async_client.get("/docs")
    assert response.status_code == 200
    assert b"swagger-ui" in response.content.lower()


@pytest.mark.asyncio
async def test_openapi_includes_authenticate_paths(async_client):
    """Either upstream-derived or FastAPI-native OpenAPI must list our auth routes."""
    response = await async_client.get("/openapi.json")
    spec = response.json()
    paths = spec.get("paths", {})
    # Logout is always present (handler explícito + merge inyecta en upstream OpenAPI).
    has_logout_path = "/api/Authenticate/logout" in paths or any(
        p.endswith("/api/Authenticate/logout") for p in paths
    )
    assert has_logout_path
