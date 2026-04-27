from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeAlias

from fastapi import APIRouter, Depends, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError

from src.core.exceptions import AuditExtractionError
from src.core.logging import get_logger
from src.core.security import _parse_bearer
from src.db.mongodb import OPERATIONS_COLLECTION, SESSIONS_COLLECTION, get_db
from src.models.operation_log import OperationAction
from src.schemas.client import (
    ClientCreateRequest,
    ClientListRequest,
    ClientUpdateRequest,
)
from src.services.operation_log_service import OperationLogService
from src.services.proxy_service import ProxyService, get_proxy_service
from src.services.session_service import SessionService
from src.utils.proxy_utils import extract_client_id, parse_json_body, proxy_response

if TYPE_CHECKING:  # pragma: no cover
    pass

logger = get_logger(__name__)

router = APIRouter(tags=["proxy"])


ClientIdExtractor: TypeAlias = Callable[[bytes, Mapping[str, str]], str | None]


@dataclass(frozen=True)
class RouteSpec:
    request_schema: type[BaseModel] | None = None
    audit_action: OperationAction | None = None
    client_id_extractor: ClientIdExtractor | None = None
    require_bearer: bool = False


def _client_id_from_response(
    body: bytes, _path_params: Mapping[str, str]
) -> str | None:
    return extract_client_id(parse_json_body(body))


def _client_id_from_path(_body: bytes, path_params: Mapping[str, str]) -> str | None:
    return path_params.get("id")


# Exact-match hooks: keyed by (HTTP method upper, path WITHOUT leading slash).
ROUTE_HOOKS_EXACT: dict[tuple[str, str], RouteSpec] = {
    ("POST", "api/Cliente/Listado"): RouteSpec(
        request_schema=ClientListRequest,
        require_bearer=True,
    ),
    ("POST", "api/Cliente/Crear"): RouteSpec(
        request_schema=ClientCreateRequest,
        audit_action=OperationAction.CREATE,
        client_id_extractor=_client_id_from_response,
        require_bearer=True,
    ),
    ("POST", "api/Cliente/Actualizar"): RouteSpec(
        request_schema=ClientUpdateRequest,
        audit_action=OperationAction.UPDATE,
        client_id_extractor=_client_id_from_response,
        require_bearer=True,
    ),
}

# Regex hooks: ordered list of (method, compiled pattern, RouteSpec).
ROUTE_HOOKS_REGEX: list[tuple[str, re.Pattern[str], RouteSpec]] = [
    (
        "DELETE",
        re.compile(r"^api/Cliente/Eliminar/(?P<id>[^/]+)$"),
        RouteSpec(
            audit_action=OperationAction.DELETE,
            client_id_extractor=_client_id_from_path,
            require_bearer=True,
        ),
    ),
]


def _resolve_spec(method: str, path: str) -> tuple[RouteSpec | None, dict[str, str]]:
    method_u = method.upper()
    spec = ROUTE_HOOKS_EXACT.get((method_u, path))
    if spec is not None:
        return spec, {}
    for verb, pattern, regex_spec in ROUTE_HOOKS_REGEX:
        if verb != method_u:
            continue
        match = pattern.match(path)
        if match:
            return regex_spec, match.groupdict()
    return None, {}


async def validate_request_body(request: Request) -> bytes:
    body = await request.body()
    full_path = request.path_params.get("full_path", "")
    method = request.method.upper()
    spec, _ = _resolve_spec(method, f"api/{full_path}")
    if spec is None or spec.request_schema is None:
        return body

    try:
        spec.request_schema.model_validate_json(body or b"{}")
    except ValidationError as exc:
        raise RequestValidationError(errors=exc.errors()) from exc
    return body


_ALLOWED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


@router.api_route("/api/{full_path:path}", methods=_ALLOWED_METHODS)
async def proxy_catchall(  # pylint: disable=too-many-locals
    full_path: str,
    request: Request,
    body: bytes = Depends(validate_request_body),
    proxy: ProxyService = Depends(get_proxy_service),
) -> Response:
    method = request.method.upper()
    upstream_path = f"api/{full_path}"
    spec, path_params = _resolve_spec(method, upstream_path)

    bearer_token = _parse_bearer(request.headers.get("authorization"))
    if spec is not None and spec.require_bearer and not bearer_token:
        return Response(
            content='{"detail":"Missing or invalid Bearer token","code":"unauthorized"}',
            status_code=401,
            media_type="application/json",
            headers={"WWW-Authenticate": "Bearer"},
        )

    status_code, response_body, response_headers = await proxy.forward(
        method,
        upstream_path,
        body=body or None,
        headers=dict(request.headers),
        params=dict(request.query_params) if request.query_params else None,
    )

    # Audit hook (CREATE / UPDATE / DELETE) — runs even on non-2xx upstream.
    if spec is not None and spec.audit_action is not None:
        await _record_audit(
            request=request,
            spec=spec,
            bearer_token=bearer_token,
            response_body=response_body,
            response_status=status_code,
            path_params=path_params,
            request_body=body,
        )

    return proxy_response(status_code, response_body, response_headers)


async def _resolve_username(
    bearer_token: str | None,
    request_body: bytes,
    sessions_coll,
) -> str | None:
    if bearer_token:
        session_doc = await SessionService(sessions_coll).find_by_token(bearer_token)
        if session_doc:
            username = session_doc.get("username") or session_doc.get("userid")
            if username:
                return str(username)

    if request_body:
        parsed = parse_json_body(request_body)
        if isinstance(parsed, dict):
            candidate = parsed.get("usuarioId") or parsed.get("user_id")
            if candidate:
                return str(candidate)

    return None


async def _resolve_client_id(
    spec: RouteSpec,
    response_body: bytes,
    path_params: Mapping[str, str],
    request_body: bytes,
) -> str | None:
    client_id: str | None = None

    if spec.client_id_extractor is not None:
        try:
            client_id = spec.client_id_extractor(response_body, path_params)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception(
                "audit_client_id_extraction_failed",
                extra={"error": str(AuditExtractionError(str(exc)))},
            )

    if (
        client_id is None
        and spec.audit_action == OperationAction.UPDATE
        and request_body
    ):
        parsed = parse_json_body(request_body)
        if isinstance(parsed, dict):
            cid = parsed.get("id") or parsed.get("Id")
            if cid:
                client_id = str(cid)

    return client_id


async def _record_audit(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    request: Request,
    spec: RouteSpec,
    bearer_token: str | None,
    response_body: bytes,
    response_status: int,
    path_params: Mapping[str, str],
    request_body: bytes,
) -> None:
    if spec.audit_action is None:
        return

    try:
        database = get_db(request)
    except RuntimeError:
        logger.warning("audit_skipped_no_database")
        return

    sessions_coll = database[SESSIONS_COLLECTION]
    operations_coll = database[OPERATIONS_COLLECTION]

    username = await _resolve_username(bearer_token, request_body, sessions_coll)
    client_id = await _resolve_client_id(spec, response_body, path_params, request_body)

    await OperationLogService(operations_coll).record_operation(
        action=spec.audit_action,
        user=username,
        client_id=client_id,
        result=response_status,
    )


__all__ = [
    "router",
    "ROUTE_HOOKS_EXACT",
    "ROUTE_HOOKS_REGEX",
    "RouteSpec",
    "validate_request_body",
]
