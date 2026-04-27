from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.schemas.auth import LoginRequest, RegisterRequest
from src.schemas.client import ClientCreateRequest

VALID_CLIENTE = {
    "nombre": "Juan",
    "apellidos": "Perez Lopez",
    "identificacion": "1-1234-5678",
    "celular": "88880000",
    "otroTelefono": "22220000",
    "direccion": "Calle 1, San Jose",
    "fNacimiento": "1990-05-12",
    "fAfiliacion": "2024-01-01",
    "sexo": "M",
    "resennaPersonal": "Cliente VIP",
    "imagen": None,
    "interesFK": "11111111-1111-1111-1111-111111111111",
    "usuarioId": "user-123",
}


def test_login_requires_fields():
    with pytest.raises(ValidationError):
        LoginRequest(username="", password="abc")


def test_register_password_valid():
    req = RegisterRequest(username="user", email="a@b.com", password="StrongPwd1")
    assert req.password == "StrongPwd1"


@pytest.mark.parametrize(
    "password",
    [
        "short1A",  # too short
        "alllowercase1",  # no uppercase
        "ALLUPPERCASE1",  # no lowercase
        "NoDigitsHere",  # no digit
        "X" * 21 + "1a",  # too long
    ],
)
def test_register_password_invalid(password):
    with pytest.raises(ValidationError):
        RegisterRequest(username="user", email="a@b.com", password=password)


def test_register_invalid_email():
    with pytest.raises(ValidationError):
        RegisterRequest(username="user", email="not-an-email", password="StrongPwd1")


def test_client_create_valid():
    cli = ClientCreateRequest(**VALID_CLIENTE)
    dumped = cli.model_dump(mode="json", by_alias=True)
    assert dumped["fNacimiento"] == "1990-05-12"
    assert dumped["sexo"] == "M"
    assert dumped["interesFK"] == "11111111-1111-1111-1111-111111111111"


def test_client_create_invalid_sex():
    payload = {**VALID_CLIENTE, "sexo": "X"}
    with pytest.raises(ValidationError):
        ClientCreateRequest(**payload)


def test_client_create_invalid_max_length():
    payload = {**VALID_CLIENTE, "nombre": "x" * 51}
    with pytest.raises(ValidationError):
        ClientCreateRequest(**payload)


def test_client_create_invalid_date():
    payload = {**VALID_CLIENTE, "fNacimiento": "not-a-date"}
    with pytest.raises(ValidationError):
        ClientCreateRequest(**payload)


def test_client_create_invalid_base64_image():
    payload = {**VALID_CLIENTE, "imagen": "not_base64!!"}
    with pytest.raises(ValidationError):
        ClientCreateRequest(**payload)


def test_client_create_valid_base64_image():
    payload = {**VALID_CLIENTE, "imagen": "aGVsbG8="}  # "hello"
    cli = ClientCreateRequest(**payload)
    assert cli.image == "aGVsbG8="
