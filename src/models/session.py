from typing import Any

from pydantic import BaseModel, Field

from src.utils.datetime_utils import utc_now_iso


class SessionRecord(BaseModel):
    token: str
    userid: str | None = None
    username: str | None = None
    login_timestamp: str = Field(default_factory=utc_now_iso)

    def to_document(self) -> dict[str, Any]:
        return self.model_dump()
