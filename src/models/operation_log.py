"""Operation log document model.

Internal Python attributes use English names. The persisted MongoDB document
keeps the original Spanish field names (``accion``, ``usuario``, ``cliente_id``,
``resultado``) for backward compatibility with existing data, via Pydantic
aliases. Enum members use English names; their ``.value`` stays in Spanish so
documents already stored remain readable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class OperationAction(str, Enum):
    CREATE = "CREAR"
    UPDATE = "ACTUALIZAR"
    DELETE = "ELIMINAR"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OperationLog(BaseModel):
    """Audit record for a CRUD operation against a client."""

    model_config = ConfigDict(populate_by_name=True)

    action: OperationAction = Field(..., alias="accion")
    user: Optional[str] = Field(default=None, alias="usuario")
    client_id: Optional[str] = Field(default=None, alias="cliente_id")
    timestamp: str = Field(default_factory=_utc_now_iso)
    result: int = Field(..., alias="resultado")

    def to_document(self) -> Dict[str, Any]:
        data = self.model_dump(by_alias=True)
        data["accion"] = self.action.value
        return data
