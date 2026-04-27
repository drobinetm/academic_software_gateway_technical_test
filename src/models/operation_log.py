from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.utils.datetime_utils import utc_now_iso


class OperationAction(str, Enum):
    CREATE = "CREAR"
    UPDATE = "ACTUALIZAR"
    DELETE = "ELIMINAR"


class OperationLog(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    action: OperationAction = Field(..., alias="accion")
    user: str | None = Field(default=None, alias="usuario")
    client_id: str | None = Field(default=None, alias="cliente_id")
    timestamp: str = Field(default_factory=utc_now_iso)
    result: int = Field(..., alias="resultado")

    def to_document(self) -> dict[str, Any]:
        data = self.model_dump(by_alias=True)
        data["accion"] = self.action.value
        return data
