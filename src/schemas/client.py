"""Client-related request schemas.

Public Python attributes use English names; ``alias`` matches the Innovasoft
Swagger contract verbatim. ``populate_by_name`` is enabled so requests from the
frontend (which uses Innovasoft's Spanish field names) are accepted, and
``model_dump(by_alias=True)`` keeps the upstream payload byte-compatible.
"""

from __future__ import annotations

import base64
import binascii
from datetime import date
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class ClientListRequest(BaseModel):
    """Payload for POST /api/Cliente/Listado."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="allow",
        populate_by_name=True,
    )

    identification: Optional[str] = Field(default=None, max_length=20, alias="identificacion")
    name: Optional[str] = Field(default=None, max_length=50, alias="nombre")
    user_id: str = Field(..., min_length=1, alias="usuarioId")


class _ClientBase(BaseModel):
    """Shared fields for create/update operations."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="allow",
        populate_by_name=True,
    )

    name: str = Field(..., max_length=50, alias="nombre")
    last_name: str = Field(..., max_length=100, alias="apellidos")
    identification: str = Field(..., max_length=20, alias="identificacion")
    mobile_phone: str = Field(..., max_length=20, alias="celular")
    other_phone: Optional[str] = Field(default=None, max_length=20, alias="otroTelefono")
    address: str = Field(..., max_length=200, alias="direccion")
    birth_date: date = Field(..., alias="fNacimiento")
    affiliation_date: date = Field(..., alias="fAfiliacion")
    gender: Literal["M", "F"] = Field(..., alias="sexo")
    personal_review: str = Field(..., max_length=200, alias="resennaPersonal")
    image: Optional[str] = Field(default=None, alias="imagen")
    interest_fk: UUID = Field(..., alias="interesFK")
    user_id: str = Field(..., min_length=1, alias="usuarioId")

    @field_validator("image")
    @classmethod
    def _validate_image_base64(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return None
        # Allow `data:image/png;base64,...` prefixes by stripping the metadata.
        candidate = value.split(",", 1)[1] if value.startswith("data:") and "," in value else value
        try:
            base64.b64decode(candidate, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("image must be a valid base64-encoded string") from exc
        return value

    @field_serializer("birth_date", "affiliation_date")
    def _serialize_dates(self, value: date) -> str:  # noqa: D401
        return value.isoformat()  # YYYY-MM-DD

    @field_serializer("interest_fk")
    def _serialize_uuid(self, value: UUID) -> str:
        return str(value)


class ClientCreateRequest(_ClientBase):
    """Payload for POST /api/Cliente/Crear."""


class ClientUpdateRequest(_ClientBase):
    """Payload for POST /api/Cliente/Actualizar (carries an id)."""

    id: Optional[str] = None
