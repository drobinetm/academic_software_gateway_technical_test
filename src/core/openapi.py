import json
import os
from typing import Any

import httpx

from src.core.config import Settings
from src.core.logging import get_logger

logger = get_logger(__name__)

_PASSWORD_PATTERN = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$"

_GATEWAY_TITLE = "Innovasoft S.A Proxy Gateway"
_GATEWAY_DESCRIPTION = (
    "Gateway FastAPI que actúa como proxy entre el frontend React y la API "
    "oficial de Innovasoft S.A. Todos los endpoints se exponen aquí sin cambios; "
    "`/api/Authenticate/logout` es terminal-local y solo elimina el documento de "
    "sesión en MongoDB."
)


async def fetch_upstream_openapi(url: str, timeout: float) -> dict[str, Any] | None:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
        response.raise_for_status()
        spec = response.json()
        if not isinstance(spec, dict):
            logger.warning("upstream_openapi_unexpected_shape")
            return None
        if "openapi" not in spec:
            # Swagger 2.0 (`swagger: "2.0"`) is not consumable by FastAPI as-is.
            logger.warning(
                "upstream_openapi_not_v3", extra={"keys": list(spec.keys())[:5]}
            )
            return None
        return spec
    except (httpx.HTTPError, ValueError):
        logger.warning("upstream_openapi_fetch_failed", extra={"url": url})
        return None


def load_cached_openapi(path: str) -> dict[str, Any] | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            spec = json.load(handle)
        if not isinstance(spec, dict) or "openapi" not in spec:
            return None
        return spec
    except (OSError, ValueError):
        logger.warning("openapi_cache_load_failed", extra={"path": path})
        return None


def merge_gateway_openapi(upstream: dict[str, Any]) -> dict[str, Any]:
    """Apply the gateway-specific overrides to an OpenAPI spec.

    - Rebrand ``info.title`` and ``info.description``.
    - Force ``servers`` to ``[{"url": "/"}]`` so "Try it out" hits the gateway.
    - Inject ``POST /api/Authenticate/logout`` (terminal-local).
    - Reinforce ``components.schemas.Register.password`` with the gateway regex.
    """
    spec = json.loads(json.dumps(upstream))  # deep copy via JSON round-trip

    info = spec.setdefault("info", {})
    info["title"] = _GATEWAY_TITLE
    info["description"] = _GATEWAY_DESCRIPTION

    spec["servers"] = [{"url": "/"}]

    paths = spec.setdefault("paths", {})
    paths.setdefault(
        "/api/Authenticate/logout",
        {
            "post": {
                "tags": ["Authenticate"],
                "summary": "Logout",
                "description": (
                    "Elimina el documento de sesión correspondiente en MongoDB. "
                    "Este endpoint NO se reenvía al upstream; es exclusivo del gateway."
                ),
                "security": [{"Bearer": []}],
                "responses": {
                    "200": {"description": "Sesión eliminada"},
                    "401": {"description": "Bearer token ausente o inválido"},
                },
            }
        },
    )

    components = spec.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    register = schemas.get("Register")
    if isinstance(register, dict):
        properties = register.setdefault("properties", {})
        password = properties.get("password")
        if isinstance(password, dict):
            password["minLength"] = 9
            password["maxLength"] = 20
            password["pattern"] = _PASSWORD_PATTERN

    return spec


async def build_openapi(settings: Settings) -> dict[str, Any] | None:
    """Build the merged OpenAPI spec at startup, with three-tier fallback."""
    spec = await fetch_upstream_openapi(
        settings.upstream_openapi_url, settings.upstream_openapi_fetch_timeout
    )
    if spec is None:
        spec = load_cached_openapi(settings.openapi_cache_path)
    if spec is None:
        return None
    return merge_gateway_openapi(spec)
