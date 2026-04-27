"""Authentication routes (login / register / logout)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.api.routes._proxy_utils import extract_session_fields, parse_json_body, proxy_response
from src.core.logging import get_logger
from src.core.security import get_optional_bearer_token
from src.db.mongodb import get_sessions_collection
from src.models.session import SessionRecord
from src.schemas.auth import LoginRequest, LogoutResponse, RegisterRequest
from src.services.innovasoft_client import InnovasoftClient, get_innovasoft_client
from src.services.session_service import SessionService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/Authenticate", tags=["Authenticate"])


@router.post("/login")
async def login(
    payload: LoginRequest,
    client: InnovasoftClient = Depends(get_innovasoft_client),
    sessions=Depends(get_sessions_collection),
) -> Response:
    status_code, body, headers = await client.login(payload.model_dump())

    if status_code == status.HTTP_200_OK:
        parsed = parse_json_body(body)
        fields = extract_session_fields(parsed)
        if fields["token"]:
            service = SessionService(sessions)
            await service.save_session(
                SessionRecord(
                    token=fields["token"],
                    userid=fields["userid"],
                    username=fields["username"] or payload.username,
                )
            )
        else:
            logger.warning("login_ok_without_token", extra={"username": payload.username})

    return proxy_response(status_code, body, headers)


@router.post("/register")
async def register(
    payload: RegisterRequest,
    client: InnovasoftClient = Depends(get_innovasoft_client),
) -> Response:
    status_code, body, headers = await client.register(payload.model_dump())
    return proxy_response(status_code, body, headers)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    token: Optional[str] = Depends(get_optional_bearer_token),
    sessions=Depends(get_sessions_collection),
) -> LogoutResponse:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    service = SessionService(sessions)
    deleted = await service.delete_session_by_token(token)
    return LogoutResponse(deleted=deleted)
