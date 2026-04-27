import json
from typing import Any

from fastapi import Response


def proxy_response(status_code: int, body: bytes, headers: dict[str, str]) -> Response:
    media_type = headers.get("content-type") or headers.get("Content-Type")
    return Response(
        content=body,
        status_code=status_code,
        headers=headers,
        media_type=media_type,
    )


def parse_json_body(body: bytes) -> Any | None:
    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def extract_session_fields(parsed_body: Any) -> dict[str, str | None]:
    if not isinstance(parsed_body, dict):
        return {"token": None, "userid": None, "username": None}

    token = parsed_body.get("token") or parsed_body.get("accessToken") or parsed_body.get("jwt")
    userid = (
        parsed_body.get("userid")
        or parsed_body.get("userId")
        or parsed_body.get("id")
        or parsed_body.get("user_id")
    )
    username = parsed_body.get("username") or parsed_body.get("userName") or parsed_body.get("user")
    return {
        "token": str(token) if token else None,
        "userid": str(userid) if userid else None,
        "username": str(username) if username else None,
    }


def extract_client_id(parsed_body: Any) -> str | None:
    if not isinstance(parsed_body, dict):
        return None
    for key in ("id", "clienteId", "idCliente", "ClienteId", "Id"):
        if key in parsed_body and parsed_body[key] is not None:
            return str(parsed_body[key])
    data = parsed_body.get("data")
    if isinstance(data, dict):
        return extract_client_id(data)
    return None
