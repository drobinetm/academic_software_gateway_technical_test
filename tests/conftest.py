import os
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
import pytest_asyncio
import respx
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

# Provide deterministic env BEFORE importing the app modules.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("INNOVASOFT_BASE_URL", "https://upstream.test/Api/")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DATABASE", "innovasoft_proxy_test")
os.environ.setdefault("API_TIMEOUT_SECONDS", "5")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("LOG_LEVEL", "WARNING")

from src.core.config import get_settings  # noqa: E402
from src.main import create_app  # noqa: E402
from src.services.proxy_service import ProxyService  # noqa: E402
from src.services.request_log_service import RequestLogService  # noqa: E402

UPSTREAM_BASE = "https://upstream.test/Api"

VALID_CLIENTE_PAYLOAD: dict[str, Any] = {
    "nombre": "Juan",
    "apellidos": "Perez",
    "identificacion": "1-1234-5678",
    "celular": "88880000",
    "otroTelefono": "22220000",
    "direccion": "Calle 1",
    "fNacimiento": "1990-05-12",
    "fAfiliacion": "2024-01-01",
    "sexo": "M",
    "resennaPersonal": "VIP",
    "imagen": None,
    "interesFK": "11111111-1111-1111-1111-111111111111",
    "usuarioId": "u-1",
}


@pytest.fixture
def settings():
    get_settings.cache_clear()
    return get_settings()


@pytest_asyncio.fixture
async def mongo_database():
    client = AsyncMongoMockClient()
    db = client["innovasoft_proxy_test"]
    yield db


@pytest_asyncio.fixture
async def app_instance(settings, mongo_database) -> AsyncIterator[FastAPI]:
    app = create_app(settings)

    http_client = httpx.AsyncClient(timeout=settings.api_timeout_seconds)

    # Bypass the lifespan by setting state ourselves (we control teardown).
    app.state.http_client = http_client
    app.state.mongodb_client = None
    app.state.mongodb_database = mongo_database
    app.state.proxy_service = ProxyService(
        http_client, settings.innovasoft_base_url, settings.api_timeout_seconds
    )
    app.state.request_log_service = RequestLogService(
        mongo_database[settings.request_logs_collection]
    )

    try:
        yield app
    finally:
        await http_client.aclose()


@pytest_asyncio.fixture
async def async_client(app_instance) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def respx_mock():
    with respx.mock(assert_all_called=False) as router:
        yield router


@pytest.fixture
def upstream_base() -> str:
    return UPSTREAM_BASE


@pytest.fixture
def valid_cliente_payload() -> dict[str, Any]:
    return dict(VALID_CLIENTE_PAYLOAD)
