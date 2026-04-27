from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

from src.core.config import get_settings

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

SESSIONS_COLLECTION = "sesiones"
OPERATIONS_COLLECTION = "operaciones"


def get_db(request: Request) -> AsyncIOMotorDatabase:
    db = getattr(request.app.state, "mongodb_database", None)
    if db is None:
        raise RuntimeError("MongoDB database is not initialised on app.state")
    return db


def get_sessions_collection(request: Request) -> AsyncIOMotorCollection:
    return get_db(request)[SESSIONS_COLLECTION]


def get_operations_collection(request: Request) -> AsyncIOMotorCollection:
    return get_db(request)[OPERATIONS_COLLECTION]


def get_request_logs_collection(request: Request) -> AsyncIOMotorCollection:
    settings = get_settings()
    return get_db(request)[settings.request_logs_collection]


async def ensure_indexes(database: AsyncIOMotorDatabase) -> None:
    settings = get_settings()
    await database[SESSIONS_COLLECTION].create_index("token", unique=True, name="uniq_token")
    await database[OPERATIONS_COLLECTION].create_index(
        [("usuario", 1), ("timestamp", -1)],
        name="usuario_timestamp_idx",
    )

    request_logs = database[settings.request_logs_collection]
    ttl_seconds: int | None = settings.request_log_ttl_seconds
    if ttl_seconds is not None and ttl_seconds > 0:
        # TTL index requires a real BSON Date; we store ISO 8601 strings, so the
        # TTL only takes effect if callers later switch to native datetime.
        # Index is still useful as a regular timestamp index either way.
        await request_logs.create_index(
            [("timestamp", 1)],
            name="timestamp_ttl_idx",
            expireAfterSeconds=ttl_seconds,
        )
    else:
        await request_logs.create_index([("timestamp", -1)], name="timestamp_idx")
