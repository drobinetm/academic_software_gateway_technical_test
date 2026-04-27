from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.exceptions import RequestLogError
from src.core.logging import get_logger
from src.models.request_log import RequestLog

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorCollection

logger = get_logger(__name__)


class RequestLogService:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection

    async def log(  # pylint: disable=too-many-arguments
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        *,
        query: str | None = None,
        request_size: int | None = None,
        response_size: int | None = None,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        record = RequestLog(
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            query=query,
            request_size=request_size,
            response_size=response_size,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        try:
            await self._collection.insert_one(record.to_document())
        except Exception as exc:  # pragma: no cover
            logger.exception(
                "request_log_insert_failed",
                extra={"error": str(RequestLogError(str(exc)))},
            )
