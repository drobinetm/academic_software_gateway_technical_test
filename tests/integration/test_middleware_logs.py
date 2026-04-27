from __future__ import annotations

import httpx
import pytest


@pytest.mark.asyncio
async def test_request_logged_to_mongo(
    async_client, respx_mock, mongo_database, settings
):
    respx_mock.get("https://upstream.test/Api/api/Intereses/Listado").mock(
        return_value=httpx.Response(200, json=[])
    )

    response = await async_client.get("/api/Intereses/Listado")
    assert response.status_code == 200

    docs = (
        await mongo_database[settings.request_logs_collection]
        .find({})
        .to_list(length=10)
    )
    matching = [d for d in docs if d["path"] == "/api/Intereses/Listado"]
    assert len(matching) == 1
    doc = matching[0]
    assert doc["method"] == "GET"
    assert doc["status_code"] == 200
    assert doc["duration_ms"] >= 0
    assert "timestamp" in doc


@pytest.mark.asyncio
async def test_excluded_paths_not_logged(async_client, mongo_database, settings):
    response = await async_client.get("/health")
    assert response.status_code == 200

    docs = (
        await mongo_database[settings.request_logs_collection]
        .find({"path": "/health"})
        .to_list(length=10)
    )
    assert docs == []


@pytest.mark.asyncio
async def test_request_log_records_failure_status(
    async_client, mongo_database, settings
):
    response = await async_client.post("/api/Authenticate/logout")
    assert response.status_code == 401

    docs = (
        await mongo_database[settings.request_logs_collection]
        .find({"path": "/api/Authenticate/logout"})
        .to_list(length=10)
    )
    assert len(docs) == 1
    assert docs[0]["status_code"] == 401
