"""Session document model."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionRecord(BaseModel):
    """Represents an authenticated session stored in MongoDB."""

    token: str
    userid: Optional[str] = None
    username: Optional[str] = None
    login_timestamp: str = Field(default_factory=_utc_now_iso)

    def to_document(self) -> Dict[str, Any]:
        return self.model_dump()
