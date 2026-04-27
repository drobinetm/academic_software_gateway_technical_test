"""Interests (Intereses) proxy route."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Response

from src.api.routes._proxy_utils import proxy_response
from src.core.security import get_optional_bearer_token
from src.services.innovasoft_client import InnovasoftClient, get_innovasoft_client

router = APIRouter(prefix="/api/Intereses", tags=["Intereses"])


@router.get("/Listado")
async def list_interests(
    token: Optional[str] = Depends(get_optional_bearer_token),
    client: InnovasoftClient = Depends(get_innovasoft_client),
) -> Response:
    status_code, body, headers = await client.list_interests(token)
    return proxy_response(status_code, body, headers)
