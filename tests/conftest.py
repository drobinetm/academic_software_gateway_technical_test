"""Shared pytest fixtures."""

from __future__ import annotations

import os
from typing import AsyncIterator

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
from src.services.innovasoft_client import InnovasoftClient  # noqa: E402

UPSTREAM_BASE = "https://upstream.test/Api"


@pytest.fixture
def settings():
    get_settings.cache_clear()
    return get_settings()


@pytest_asyncio.fixture
async def mongo_database():
    client = AsyncMongoMockClient()
    db = client["innovasoft_proxy_test"]
    yield db
    # mongomock-motor cleans up automatically; nothing else needed.


@pytest_asyncio.fixture
async def app_instance(settings, mongo_database) -> AsyncIterator[FastAPI]:
    """Build a FastAPI app wired with mock Mongo and a real (mocked) httpx client."""
    app = create_app(settings)

    http_client = httpx.AsyncClient(timeout=settings.api_timeout_seconds)

    # Bypass the lifespan by setting state ourselves (we control teardown).
    app.state.http_client = http_client
    app.state.mongodb_client = None
    app.state.mongodb_database = mongo_database
    app.state.innovasoft_client = InnovasoftClient(
        http_client, settings.innovasoft_base_url, settings.api_timeout_seconds
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
