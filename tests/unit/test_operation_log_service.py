"""Tests for OperationLogService."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.models.operation_log import OperationAction
from src.services.operation_log_service import OperationLogService


@pytest.mark.asyncio
async def test_record_create(mongo_database):
    service = OperationLogService(mongo_database["operaciones"])
    await service.record_operation(
        action=OperationAction.CREATE,
        user="alice",
        client_id="cli-1",
        result=200,
    )
    doc = await mongo_database["operaciones"].find_one({"cliente_id": "cli-1"})
    assert doc is not None
    assert doc["accion"] == "CREAR"
    assert doc["resultado"] == 200
    assert doc["usuario"] == "alice"


@pytest.mark.asyncio
async def test_record_update_delete(mongo_database):
    service = OperationLogService(mongo_database["operaciones"])
    await service.record_operation(
        action=OperationAction.UPDATE, user="u", client_id="c", result=200
    )
    await service.record_operation(
        action=OperationAction.DELETE, user="u", client_id="c", result=204
    )
    docs = [d async for d in mongo_database["operaciones"].find({"cliente_id": "c"})]
    assert {d["accion"] for d in docs} == {"ACTUALIZAR", "ELIMINAR"}


@pytest.mark.asyncio
async def test_record_failure_does_not_raise():
    failing = AsyncMock()
    failing.insert_one = AsyncMock(side_effect=RuntimeError("boom"))
    service = OperationLogService(failing)
    # Should not raise even when the underlying collection fails.
    await service.record_operation(
        action=OperationAction.CREATE,
        user="u",
        client_id="c",
        result=500,
    )
    failing.insert_one.assert_awaited_once()
