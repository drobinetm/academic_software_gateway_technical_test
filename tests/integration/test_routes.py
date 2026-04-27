from __future__ import annotations

import httpx
import pytest

from tests.conftest import UPSTREAM_BASE as UPSTREAM


@pytest.mark.asyncio
async def test_cors_preflight_allows_vercel_frontend(async_client):
    response = await async_client.options(
        "/api/Authenticate/login",
        headers={
            "Origin": "https://frontend-under-test.vercel.app",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "https://frontend-under-test.vercel.app"
    )


@pytest.mark.asyncio
async def test_cors_preflight_allows_other_vercel_previews(async_client):
    response = await async_client.options(
        "/api/Authenticate/login",
        headers={
            "Origin": "https://academic-software-frontend-technica-git-main.vercel.app",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "https://academic-software-frontend-technica-git-main.vercel.app"
    )


@pytest.mark.asyncio
async def test_login_ok_persists_session(async_client, respx_mock, mongo_database):
    respx_mock.post(f"{UPSTREAM}/api/Authenticate/login").mock(
        return_value=httpx.Response(
            200,
            json={"token": "tok-123", "userid": "u-1", "username": "alice"},
        )
    )

    response = await async_client.post(
        "/api/Authenticate/login",
        json={"username": "alice", "password": "Whatever1"},
    )
    assert response.status_code == 200
    assert response.json()["token"] == "tok-123"

    doc = await mongo_database["sesiones"].find_one({"token": "tok-123"})
    assert doc is not None
    assert doc["username"] == "alice"
    assert doc["userid"] == "u-1"


@pytest.mark.asyncio
async def test_login_failed_does_not_persist(async_client, respx_mock, mongo_database):
    respx_mock.post(f"{UPSTREAM}/api/Authenticate/login").mock(
        return_value=httpx.Response(401, json={"detail": "bad creds"})
    )

    response = await async_client.post(
        "/api/Authenticate/login",
        json={"username": "alice", "password": "wrong"},
    )
    assert response.status_code == 401
    assert await mongo_database["sesiones"].count_documents({}) == 0


@pytest.mark.asyncio
async def test_register_invalid_email_returns_422(async_client, respx_mock):
    response = await async_client.post(
        "/api/Authenticate/register",
        json={"username": "u", "email": "not-email", "password": "StrongPwd1"},
    )
    assert response.status_code == 422
    assert not respx_mock.calls


@pytest.mark.asyncio
async def test_register_invalid_password_returns_422(async_client, respx_mock):
    response = await async_client.post(
        "/api/Authenticate/register",
        json={"username": "u", "email": "a@b.com", "password": "weakpass"},
    )
    assert response.status_code == 422
    assert not respx_mock.calls


@pytest.mark.asyncio
async def test_register_proxies_when_valid(async_client, respx_mock):
    respx_mock.post(f"{UPSTREAM}/api/Authenticate/register").mock(
        return_value=httpx.Response(200, json={"id": "u-1"})
    )
    response = await async_client.post(
        "/api/Authenticate/register",
        json={"username": "u", "email": "a@b.com", "password": "StrongPwd1"},
    )
    assert response.status_code == 200
    assert response.json() == {"id": "u-1"}


@pytest.mark.asyncio
async def test_logout_deletes_session(async_client, respx_mock, mongo_database):
    await mongo_database["sesiones"].insert_one(
        {
            "token": "tok-X",
            "userid": "u-1",
            "username": "alice",
            "login_timestamp": "ts",
        }
    )

    response = await async_client.post(
        "/api/Authenticate/logout",
        headers={"Authorization": "Bearer tok-X"},
    )
    assert response.status_code == 200
    assert response.json()["deleted"] is True
    assert await mongo_database["sesiones"].count_documents({}) == 0


@pytest.mark.asyncio
async def test_logout_without_token_returns_401(async_client):
    response = await async_client.post("/api/Authenticate/logout")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_listado_clientes_forwards_bearer(async_client, respx_mock):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json=[])

    respx_mock.post(f"{UPSTREAM}/api/Cliente/Listado").mock(side_effect=handler)

    response = await async_client.post(
        "/api/Cliente/Listado",
        json={"usuarioId": "u-1"},
        headers={"Authorization": "Bearer tok-1"},
    )
    assert response.status_code == 200
    assert captured["auth"] == "Bearer tok-1"


@pytest.mark.asyncio
async def test_cliente_listado_without_token_returns_401(async_client, respx_mock):
    response = await async_client.post(
        "/api/Cliente/Listado",
        json={"usuarioId": "u-1"},
    )
    assert response.status_code == 401
    assert not respx_mock.calls


from tests.conftest import VALID_CLIENTE_PAYLOAD


@pytest.mark.asyncio
async def test_create_client_logs_operation(async_client, respx_mock, mongo_database):
    respx_mock.post(f"{UPSTREAM}/api/Cliente/Crear").mock(
        return_value=httpx.Response(200, json={"id": "cli-99"})
    )

    response = await async_client.post(
        "/api/Cliente/Crear",
        json=VALID_CLIENTE_PAYLOAD,
        headers={"Authorization": "Bearer tok-1"},
    )
    assert response.status_code == 200

    doc = await mongo_database["operaciones"].find_one({"accion": "CREAR"})
    assert doc is not None
    assert doc["cliente_id"] == "cli-99"
    assert doc["resultado"] == 200
    assert doc["usuario"] == "u-1"


@pytest.mark.asyncio
async def test_update_client_logs_operation(async_client, respx_mock, mongo_database):
    respx_mock.post(f"{UPSTREAM}/api/Cliente/Actualizar").mock(
        return_value=httpx.Response(200, json={"id": "cli-99"})
    )

    payload = {**VALID_CLIENTE_PAYLOAD, "id": "cli-99"}
    response = await async_client.post(
        "/api/Cliente/Actualizar",
        json=payload,
        headers={"Authorization": "Bearer tok-1"},
    )
    assert response.status_code == 200

    doc = await mongo_database["operaciones"].find_one({"accion": "ACTUALIZAR"})
    assert doc is not None
    assert doc["cliente_id"] == "cli-99"


@pytest.mark.asyncio
async def test_delete_client_logs_operation(async_client, respx_mock, mongo_database):
    respx_mock.delete(f"{UPSTREAM}/api/Cliente/Eliminar/cli-42").mock(
        return_value=httpx.Response(204)
    )

    response = await async_client.delete(
        "/api/Cliente/Eliminar/cli-42",
        headers={"Authorization": "Bearer tok-1"},
    )
    assert response.status_code == 204

    doc = await mongo_database["operaciones"].find_one({"accion": "ELIMINAR"})
    assert doc is not None
    assert doc["cliente_id"] == "cli-42"
    assert doc["resultado"] == 204


@pytest.mark.asyncio
async def test_cliente_crear_logs_failure(async_client, respx_mock, mongo_database):
    respx_mock.post(f"{UPSTREAM}/api/Cliente/Crear").mock(
        return_value=httpx.Response(400, json={"detail": "bad"})
    )

    response = await async_client.post(
        "/api/Cliente/Crear",
        json=VALID_CLIENTE_PAYLOAD,
        headers={"Authorization": "Bearer tok-1"},
    )
    assert response.status_code == 400

    doc = await mongo_database["operaciones"].find_one({"accion": "CREAR"})
    assert doc is not None
    assert doc["resultado"] == 400


@pytest.mark.asyncio
async def test_intereses_listado_passthrough(async_client, respx_mock):
    respx_mock.get(f"{UPSTREAM}/api/Intereses/Listado").mock(
        return_value=httpx.Response(200, json=[{"id": "i-1", "nombre": "Tenis"}])
    )

    response = await async_client.get("/api/Intereses/Listado")
    assert response.status_code == 200
    assert response.json() == [{"id": "i-1", "nombre": "Tenis"}]


@pytest.mark.asyncio
async def test_upstream_timeout_returns_504(async_client, respx_mock):
    respx_mock.post(f"{UPSTREAM}/api/Authenticate/login").mock(
        side_effect=httpx.TimeoutException("slow")
    )

    response = await async_client.post(
        "/api/Authenticate/login",
        json={"username": "alice", "password": "Whatever1"},
    )
    assert response.status_code == 504
    body = response.json()
    assert body["code"] == "upstream_timeout"


@pytest.mark.asyncio
async def test_upstream_network_error_returns_502(async_client, respx_mock):
    respx_mock.post(f"{UPSTREAM}/api/Authenticate/login").mock(
        side_effect=httpx.ConnectError("refused")
    )

    response = await async_client.post(
        "/api/Authenticate/login",
        json={"username": "alice", "password": "Whatever1"},
    )
    assert response.status_code == 502
    assert response.json()["code"] == "upstream_unavailable"


@pytest.mark.asyncio
async def test_route_compatibility_smoke(async_client, respx_mock):
    respx_mock.post(f"{UPSTREAM}/api/Authenticate/login").mock(
        return_value=httpx.Response(200, json={"token": "t", "username": "u"})
    )
    respx_mock.post(f"{UPSTREAM}/api/Authenticate/register").mock(
        return_value=httpx.Response(200, json={})
    )
    respx_mock.post(f"{UPSTREAM}/api/Cliente/Listado").mock(
        return_value=httpx.Response(200, json=[])
    )
    respx_mock.get(f"{UPSTREAM}/api/Cliente/Obtener/cli-1").mock(
        return_value=httpx.Response(200, json={"id": "cli-1"})
    )
    respx_mock.get(f"{UPSTREAM}/api/Intereses/Listado").mock(
        return_value=httpx.Response(200, json=[])
    )

    assert (
        await async_client.post(
            "/api/Authenticate/login",
            json={"username": "u", "password": "p"},
        )
    ).status_code == 200
    assert (
        await async_client.post(
            "/api/Authenticate/register",
            json={"username": "u", "email": "a@b.com", "password": "StrongPwd1"},
        )
    ).status_code == 200
    assert (
        await async_client.post(
            "/api/Cliente/Listado",
            json={"usuarioId": "u"},
            headers={"Authorization": "Bearer t"},
        )
    ).status_code == 200
    assert (
        await async_client.get(
            "/api/Cliente/Obtener/cli-1",
            headers={"Authorization": "Bearer t"},
        )
    ).status_code == 200
    assert (await async_client.get("/api/Intereses/Listado")).status_code == 200
