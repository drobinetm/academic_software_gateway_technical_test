from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.core.logging import get_logger
from src.models.session import SessionRecord

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorCollection

logger = get_logger(__name__)


class SessionService:
    """Persistence service for the `sesiones` collection."""

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection

    async def save_session(self, record: SessionRecord) -> None:
        await self._collection.update_one(
            {"token": record.token},
            {"$set": record.to_document()},
            upsert=True,
        )
        logger.info(
            "session_saved",
            extra={"username": record.username, "userid": record.userid},
        )

    async def delete_session_by_token(self, token: str) -> bool:
        result = await self._collection.delete_one({"token": token})
        deleted = result.deleted_count > 0
        logger.info("session_deleted", extra={"deleted": deleted})
        return deleted

    async def find_by_token(self, token: str) -> dict[str, Any] | None:
        return await self._collection.find_one({"token": token})
