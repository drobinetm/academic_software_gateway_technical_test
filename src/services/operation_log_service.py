from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.exceptions import OperationLogError
from src.core.logging import get_logger
from src.models.operation_log import OperationAction, OperationLog

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorCollection

logger = get_logger(__name__)


class OperationLogService:
    """Persistence service for the `operaciones` collection."""

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection

    async def record_operation(
        self,
        action: OperationAction,
        user: str | None,
        client_id: str | None,
        result: int,
    ) -> None:
        record = OperationLog(
            action=action,
            user=user,
            client_id=client_id,
            result=result,
        )
        try:
            await self._collection.insert_one(record.to_document())
            logger.info(
                "operation_recorded",
                extra={
                    "accion": action.value,
                    "usuario": user,
                    "client_id": client_id,
                    "resultado": result,
                },
            )
        except Exception as exc:  # pragma: no cover
            logger.exception(
                "operation_record_failed",
                extra={"error": str(OperationLogError(str(exc)))},
            )
