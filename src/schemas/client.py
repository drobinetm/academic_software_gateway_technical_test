import base64
import binascii
from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
)


def _coerce_date(value: object) -> object:
    """Strip time component from ISO 8601 datetime strings before date parsing.

    The React frontend sends dates as full datetime strings (e.g.
    ``"1986-03-28T04:00:00.000Z"``). Pydantic v2 rejects datetimes with a
    non-zero time when coercing to ``date``. This validator normalises any
    string to its date portion so both ``"1986-03-28"`` and
    ``"1986-03-28T04:00:00.000Z"`` are accepted.
    """
    if isinstance(value, str) and "T" in value:
        return value.split("T")[0]
    return value


ISODate = Annotated[date, BeforeValidator(_coerce_date)]


class ClientListRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="allow",
        populate_by_name=True,
    )

    identification: str | None = Field(
        default=None, max_length=20, alias="identificacion"
    )
    name: str | None = Field(default=None, max_length=50, alias="nombre")
    user_id: str = Field(..., min_length=1, alias="usuarioId")


class _ClientBase(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="allow",
        populate_by_name=True,
    )

    name: str = Field(..., max_length=50, alias="nombre")
    last_name: str = Field(..., max_length=100, alias="apellidos")
    identification: str = Field(..., max_length=20, alias="identificacion")
    mobile_phone: str = Field(..., max_length=20, alias="celular")
    other_phone: str | None = Field(default=None, max_length=20, alias="otroTelefono")
    address: str = Field(..., max_length=200, alias="direccion")
    birth_date: ISODate = Field(..., alias="fNacimiento")
    affiliation_date: ISODate = Field(..., alias="fAfiliacion")
    gender: Literal["M", "F"] = Field(..., alias="sexo")
    personal_review: str = Field(..., max_length=200, alias="resennaPersonal")
    image: str | None = Field(default=None, alias="imagen")
    interest_fk: UUID = Field(..., alias="interesFK")
    user_id: str = Field(..., min_length=1, alias="usuarioId")

    @field_validator("image")
    @classmethod
    def _validate_image_base64(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        # Allow `data:image/png;base64,...` prefixes by stripping the metadata.
        candidate = (
            value.split(",", 1)[1]
            if value.startswith("data:") and "," in value
            else value
        )
        try:
            base64.b64decode(candidate, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("image must be a valid base64-encoded string") from exc
        return value

    @field_serializer("birth_date", "affiliation_date")
    def _serialize_dates(self, value: date) -> str:  # noqa: D401
        return value.isoformat()

    @field_serializer("interest_fk")
    def _serialize_uuid(self, value: UUID) -> str:
        return str(value)


class ClientCreateRequest(_ClientBase):
    pass


class ClientUpdateRequest(_ClientBase):
    id: str | None = None
