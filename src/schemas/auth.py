import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

_PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{9,20}$")


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="allow")

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="allow")

    username: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=9, max_length=20)

    @field_validator("password")
    @classmethod
    def _validate_password_complexity(cls, value: str) -> str:
        if not _PASSWORD_REGEX.match(value):
            raise ValueError(
                "Password must be 9-20 characters and include at least one lowercase, "
                "one uppercase, and one digit."
            )
        return value


class LogoutResponse(BaseModel):
    detail: str = "Sesión cerrada correctamente"
    deleted: bool = False
