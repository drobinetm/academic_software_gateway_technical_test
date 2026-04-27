from __future__ import annotations

import httpx
import pytest

from tests.conftest import UPSTREAM_BASE as UPSTREAM, VALID_CLIENTE_PAYLOAD


@pytest.mark.asyncio
async def test_validation_error_returns_422_without_calling_upstream(
    async_client, respx_mock
):
    bad = {**VALID_CLIENTE_PAYLOAD, "sexo": "X"}  # invalid: only M/F allowed
    response = await async_client.post(
        "/api/Cliente/Crear",
        json=bad,
        headers={"Authorization": "Bearer tok-1"},
    )
    assert response.status_code == 422
    assert not respx_mock.calls


@pytest.mark.asyncio
async def test_passthrough_get_unknown_path(async_client, respx_mock):
    respx_mock.get(f"{UPSTREAM}/api/Intereses/Listado").mock(
        return_value=httpx.Response(200, json=[{"id": "i-1"}])
    )
    response = await async_client.get("/api/Intereses/Listado")
    assert response.status_code == 200
    assert response.json() == [{"id": "i-1"}]


@pytest.mark.asyncio
async def test_propagates_status_and_headers(async_client, respx_mock):
    respx_mock.get(f"{UPSTREAM}/api/Some/Endpoint").mock(
        return_value=httpx.Response(
            418,
            json={"err": "teapot"},
            headers={"X-Custom": "yes"},
        )
    )
    response = await async_client.get("/api/Some/Endpoint")
    assert response.status_code == 418
    assert response.headers.get("x-custom") == "yes"
    assert response.json() == {"err": "teapot"}


@pytest.mark.asyncio
async def test_audit_create_records_operation(async_client, respx_mock, mongo_database):
    respx_mock.post(f"{UPSTREAM}/api/Cliente/Crear").mock(
        return_value=httpx.Response(200, json={"id": "cli-77"})
    )
    response = await async_client.post(
        "/api/Cliente/Crear",
        json=VALID_CLIENTE_PAYLOAD,
        headers={"Authorization": "Bearer tok-1"},
    )
    assert response.status_code == 200

    doc = await mongo_database["operaciones"].find_one({"accion": "CREAR"})
    assert doc is not None
    assert doc["cliente_id"] == "cli-77"
    assert doc["resultado"] == 200


@pytest.mark.asyncio
async def test_audit_update_records_operation(async_client, respx_mock, mongo_database):
    respx_mock.post(f"{UPSTREAM}/api/Cliente/Actualizar").mock(
        return_value=httpx.Response(200, json={"id": "cli-77"})
    )
    payload = {**VALID_CLIENTE_PAYLOAD, "id": "cli-77"}
    response = await async_client.post(
        "/api/Cliente/Actualizar",
        json=payload,
        headers={"Authorization": "Bearer tok-1"},
    )
    assert response.status_code == 200

    doc = await mongo_database["operaciones"].find_one({"accion": "ACTUALIZAR"})
    assert doc is not None
    assert doc["cliente_id"] == "cli-77"


@pytest.mark.asyncio
async def test_audit_delete_records_operation(async_client, respx_mock, mongo_database):
    respx_mock.delete(f"{UPSTREAM}/api/Cliente/Eliminar/cli-9").mock(
        return_value=httpx.Response(204)
    )
    response = await async_client.delete(
        "/api/Cliente/Eliminar/cli-9",
        headers={"Authorization": "Bearer tok-1"},
    )
    assert response.status_code == 204

    doc = await mongo_database["operaciones"].find_one({"accion": "ELIMINAR"})
    assert doc is not None
    assert doc["cliente_id"] == "cli-9"


@pytest.mark.asyncio
async def test_audit_resolves_username_from_session(
    async_client, respx_mock, mongo_database
):
    await mongo_database["sesiones"].insert_one(
        {
            "token": "tok-sess",
            "userid": "u-99",
            "username": "alice",
            "login_timestamp": "ts",
        }
    )
    respx_mock.post(f"{UPSTREAM}/api/Cliente/Crear").mock(
        return_value=httpx.Response(200, json={"id": "cli-1"})
    )

    response = await async_client.post(
        "/api/Cliente/Crear",
        json=VALID_CLIENTE_PAYLOAD,
        headers={"Authorization": "Bearer tok-sess"},
    )
    assert response.status_code == 200

    doc = await mongo_database["operaciones"].find_one({"accion": "CREAR"})
    assert doc is not None
    assert doc["usuario"] == "alice"


@pytest.mark.asyncio
async def test_listado_without_bearer_returns_401_no_upstream(async_client, respx_mock):
    response = await async_client.post(
        "/api/Cliente/Listado",
        json={"usuarioId": "u-1"},
    )
    assert response.status_code == 401
    assert not respx_mock.calls


@pytest.mark.asyncio
async def test_eliminar_without_bearer_returns_401(async_client, respx_mock):
    response = await async_client.delete("/api/Cliente/Eliminar/cli-1")
    assert response.status_code == 401
    assert not respx_mock.calls


@pytest.mark.asyncio
async def test_query_params_are_forwarded(async_client, respx_mock):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(request.url.params)
        return httpx.Response(200, json={"ok": True})

    respx_mock.get(f"{UPSTREAM}/api/Some/Search").mock(side_effect=handler)
    response = await async_client.get("/api/Some/Search?q=foo&page=2")
    assert response.status_code == 200
    assert captured["query"] == {"q": "foo", "page": "2"}
