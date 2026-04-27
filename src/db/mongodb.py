"""MongoDB connection helpers and FastAPI dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

SESSIONS_COLLECTION = "sesiones"
OPERATIONS_COLLECTION = "operaciones"


def get_db(request: Request) -> "AsyncIOMotorDatabase":
    db = getattr(request.app.state, "mongodb_database", None)
    if db is None:
        raise RuntimeError("MongoDB database is not initialised on app.state")
    return db


def get_sessions_collection(request: Request) -> "AsyncIOMotorCollection":
    return get_db(request)[SESSIONS_COLLECTION]


def get_operations_collection(request: Request) -> "AsyncIOMotorCollection":
    return get_db(request)[OPERATIONS_COLLECTION]


async def ensure_indexes(database: "AsyncIOMotorDatabase") -> None:
    """Create required indexes (idempotent)."""
    await database[SESSIONS_COLLECTION].create_index("token", unique=True, name="uniq_token")
    await database[OPERATIONS_COLLECTION].create_index(
        [("usuario", 1), ("timestamp", -1)],
        name="usuario_timestamp_idx",
    )
