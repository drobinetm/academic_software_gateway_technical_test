from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Response, status

from src.core.logging import get_logger
from src.core.security import get_bearer_token, get_optional_bearer_token
from src.db.mongodb import get_sessions_collection
from src.models.session import SessionRecord
from src.schemas.auth import LoginRequest, LogoutResponse, RegisterRequest
from src.services.proxy_service import ProxyService, get_proxy_service
from src.services.session_service import SessionService
from src.utils.proxy_utils import extract_session_fields, parse_json_body, proxy_response

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorCollection

logger = get_logger(__name__)

router = APIRouter(prefix="/api/Authenticate", tags=["Authenticate"])


@router.post("/login")
async def login(
    payload: LoginRequest,
    proxy: ProxyService = Depends(get_proxy_service),
    sessions: AsyncIOMotorCollection = Depends(get_sessions_collection),
) -> Response:
    body = payload.model_dump_json().encode("utf-8")
    status_code, response_body, headers = await proxy.forward(
        "POST",
        "api/Authenticate/login",
        body=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )

    if status_code == status.HTTP_200_OK:
        parsed = parse_json_body(response_body)
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

    return proxy_response(status_code, response_body, headers)


@router.post("/register")
async def register(
    payload: RegisterRequest,
    proxy: ProxyService = Depends(get_proxy_service),
) -> Response:
    body = payload.model_dump_json().encode("utf-8")
    status_code, response_body, headers = await proxy.forward(
        "POST",
        "api/Authenticate/register",
        body=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    return proxy_response(status_code, response_body, headers)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    token: str = Depends(get_bearer_token),
    sessions: AsyncIOMotorCollection = Depends(get_sessions_collection),
) -> LogoutResponse:
    service = SessionService(sessions)
    deleted = await service.delete_session_by_token(token)
    return LogoutResponse(deleted=deleted)
