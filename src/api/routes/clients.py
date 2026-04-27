"""Client (Cliente) proxy routes with audit logging."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Response

from src.api.routes._proxy_utils import extract_client_id, parse_json_body, proxy_response
from src.core.security import get_bearer_token
from src.db.mongodb import get_operations_collection, get_sessions_collection
from src.models.operation_log import OperationAction
from src.schemas.client import ClientCreateRequest, ClientListRequest, ClientUpdateRequest
from src.services.innovasoft_client import InnovasoftClient, get_innovasoft_client
from src.services.operation_log_service import OperationLogService
from src.services.session_service import SessionService

router = APIRouter(prefix="/api/Cliente", tags=["Cliente"])


async def _resolve_username(sessions, token: str, fallback: str | None = None) -> str | None:
    service = SessionService(sessions)
    doc = await service.find_by_token(token)
    if doc:
        return doc.get("username") or fallback
    return fallback


@router.post("/Listado")
async def list_clients(
    payload: ClientListRequest,
    token: str = Depends(get_bearer_token),
    client: InnovasoftClient = Depends(get_innovasoft_client),
) -> Response:
    status_code, body, headers = await client.list_clients(payload.model_dump(by_alias=True), token)
    return proxy_response(status_code, body, headers)


@router.get("/Obtener/{IdCliente}")
async def get_client(
    client_id: str = Path(..., alias="IdCliente"),
    token: str = Depends(get_bearer_token),
    client: InnovasoftClient = Depends(get_innovasoft_client),
) -> Response:
    status_code, body, headers = await client.get_client(client_id, token)
    return proxy_response(status_code, body, headers)


@router.post("/Crear")
async def create_client(
    payload: ClientCreateRequest,
    token: str = Depends(get_bearer_token),
    client: InnovasoftClient = Depends(get_innovasoft_client),
    operations=Depends(get_operations_collection),
    sessions=Depends(get_sessions_collection),
) -> Response:
    body_payload = payload.model_dump(mode="json", by_alias=True)
    status_code, body, headers = await client.create_client(body_payload, token)

    client_id = extract_client_id(parse_json_body(body))
    username = await _resolve_username(sessions, token, fallback=payload.user_id)
    await OperationLogService(operations).record_operation(
        action=OperationAction.CREATE,
        user=username,
        client_id=client_id,
        result=status_code,
    )
    return proxy_response(status_code, body, headers)


@router.post("/Actualizar")
async def update_client(
    payload: ClientUpdateRequest,
    token: str = Depends(get_bearer_token),
    client: InnovasoftClient = Depends(get_innovasoft_client),
    operations=Depends(get_operations_collection),
    sessions=Depends(get_sessions_collection),
) -> Response:
    body_payload = payload.model_dump(mode="json", by_alias=True)
    status_code, body, headers = await client.update_client(body_payload, token)

    client_id = payload.id or extract_client_id(parse_json_body(body))
    username = await _resolve_username(sessions, token, fallback=payload.user_id)
    await OperationLogService(operations).record_operation(
        action=OperationAction.UPDATE,
        user=username,
        client_id=client_id,
        result=status_code,
    )
    return proxy_response(status_code, body, headers)


@router.delete("/Eliminar/{IdCliente}")
async def delete_client(
    client_id: str = Path(..., alias="IdCliente"),
    token: str = Depends(get_bearer_token),
    client: InnovasoftClient = Depends(get_innovasoft_client),
    operations=Depends(get_operations_collection),
    sessions=Depends(get_sessions_collection),
) -> Response:
    status_code, body, headers = await client.delete_client(client_id, token)
    username = await _resolve_username(sessions, token)
    await OperationLogService(operations).record_operation(
        action=OperationAction.DELETE,
        user=username,
        client_id=client_id,
        result=status_code,
    )
    return proxy_response(status_code, body, headers)
