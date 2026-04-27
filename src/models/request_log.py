from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.utils.datetime_utils import utc_now_iso


class RequestLog(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    method: str
    path: str
    status_code: int
    duration_ms: float
    timestamp: str = Field(default_factory=utc_now_iso)

    query: str | None = None
    request_size: int | None = None
    response_size: int | None = None
    client_ip: str | None = None
    user_agent: str | None = None

    def to_document(self) -> dict[str, Any]:
        return self.model_dump()
