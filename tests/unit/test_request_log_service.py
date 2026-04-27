from __future__ import annotations

import re

import pytest
from mongomock_motor import AsyncMongoMockClient

from src.services.request_log_service import RequestLogService

ISO_8601_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(\+\d{2}:\d{2}|Z)$"
)


@pytest.mark.asyncio
async def test_log_inserts_document_with_iso_timestamp():
    client = AsyncMongoMockClient()
    collection = client["testdb"]["request_logs"]
    service = RequestLogService(collection)

    await service.log(method="GET", path="/api/x", status_code=200, duration_ms=12.34)

    docs = await collection.find({}).to_list(length=10)
    assert len(docs) == 1
    doc = docs[0]
    assert doc["method"] == "GET"
    assert doc["path"] == "/api/x"
    assert doc["status_code"] == 200
    assert doc["duration_ms"] == 12.34
    assert ISO_8601_RE.match(doc["timestamp"])


@pytest.mark.asyncio
async def test_log_persists_optional_context():
    client = AsyncMongoMockClient()
    collection = client["testdb"]["request_logs"]
    service = RequestLogService(collection)

    await service.log(
        method="POST",
        path="/api/x",
        status_code=201,
        duration_ms=5.0,
        query="a=1",
        request_size=10,
        response_size=20,
        client_ip="127.0.0.1",
        user_agent="pytest",
    )

    doc = await collection.find_one({})
    assert doc["query"] == "a=1"
    assert doc["request_size"] == 10
    assert doc["response_size"] == 20
    assert doc["client_ip"] == "127.0.0.1"
    assert doc["user_agent"] == "pytest"


@pytest.mark.asyncio
async def test_log_swallows_collection_failure(caplog):
    class BoomCollection:
        async def insert_one(self, _doc):
            raise RuntimeError("mongo down")

    service = RequestLogService(BoomCollection())  # type: ignore[arg-type]
    await service.log("GET", "/x", 200, 1.0)
