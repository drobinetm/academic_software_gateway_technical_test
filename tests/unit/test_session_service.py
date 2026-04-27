"""Tests for SessionService."""

from __future__ import annotations

import pytest

from src.models.session import SessionRecord
from src.services.session_service import SessionService


@pytest.mark.asyncio
async def test_save_session_inserts(mongo_database):
    service = SessionService(mongo_database["sesiones"])
    await service.save_session(SessionRecord(token="t1", userid="u1", username="alice"))
    doc = await mongo_database["sesiones"].find_one({"token": "t1"})
    assert doc is not None
    assert doc["username"] == "alice"
    assert "login_timestamp" in doc


@pytest.mark.asyncio
async def test_save_session_upserts_same_token(mongo_database):
    service = SessionService(mongo_database["sesiones"])
    await service.save_session(SessionRecord(token="t1", username="alice"))
    await service.save_session(SessionRecord(token="t1", username="bob"))
    cursor = mongo_database["sesiones"].find({"token": "t1"})
    docs = [d async for d in cursor]
    assert len(docs) == 1
    assert docs[0]["username"] == "bob"


@pytest.mark.asyncio
async def test_delete_session_idempotent(mongo_database):
    service = SessionService(mongo_database["sesiones"])
    await service.save_session(SessionRecord(token="t1"))
    assert await service.delete_session_by_token("t1") is True
    # second delete is a no-op
    assert await service.delete_session_by_token("t1") is False
