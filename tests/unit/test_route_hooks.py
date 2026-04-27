from __future__ import annotations

import pytest

from src.api.routes.proxy import (
    ROUTE_HOOKS_EXACT,
    ROUTE_HOOKS_REGEX,
    RouteSpec,
    _resolve_spec,
)
from src.models.operation_log import OperationAction
from src.schemas.client import (
    ClientCreateRequest,
    ClientListRequest,
    ClientUpdateRequest,
)


def test_exact_lookup_listado_returns_listrequest_no_audit():
    spec, params = _resolve_spec("POST", "api/Cliente/Listado")
    assert spec is not None
    assert spec.request_schema is ClientListRequest
    assert spec.audit_action is None
    assert spec.require_bearer is True
    assert params == {}


def test_exact_lookup_crear_has_create_audit():
    spec, params = _resolve_spec("POST", "api/Cliente/Crear")
    assert spec is not None
    assert spec.request_schema is ClientCreateRequest
    assert spec.audit_action is OperationAction.CREATE
    assert spec.client_id_extractor is not None
    assert params == {}


def test_exact_lookup_actualizar_has_update_audit():
    spec, params = _resolve_spec("POST", "api/Cliente/Actualizar")
    assert spec is not None
    assert spec.request_schema is ClientUpdateRequest
    assert spec.audit_action is OperationAction.UPDATE
    assert params == {}


def test_regex_lookup_eliminar_extracts_id():
    spec, params = _resolve_spec("DELETE", "api/Cliente/Eliminar/cli-42")
    assert spec is not None
    assert spec.audit_action is OperationAction.DELETE
    assert spec.request_schema is None
    assert params == {"id": "cli-42"}


def test_regex_lookup_with_uuid_id():
    spec, params = _resolve_spec(
        "DELETE", "api/Cliente/Eliminar/11111111-1111-1111-1111-111111111111"
    )
    assert spec is not None
    assert params == {"id": "11111111-1111-1111-1111-111111111111"}


def test_unregistered_path_returns_none():
    spec, params = _resolve_spec("GET", "api/Intereses/Listado")
    assert spec is None
    assert params == {}


def test_method_mismatch_returns_none():
    spec, _ = _resolve_spec("GET", "api/Cliente/Listado")  # registered as POST
    assert spec is None


def test_method_normalization_is_uppercase():
    spec, _ = _resolve_spec("post", "api/Cliente/Crear")
    assert spec is not None


def test_regex_does_not_match_extra_segments():
    spec, _ = _resolve_spec("DELETE", "api/Cliente/Eliminar/cli-1/extra")
    assert spec is None


def test_route_spec_passthrough_defaults():
    spec = RouteSpec()
    assert spec.request_schema is None
    assert spec.audit_action is None
    assert spec.client_id_extractor is None
    assert spec.require_bearer is False


def test_registry_invariants():
    for key in ROUTE_HOOKS_EXACT:
        assert isinstance(key, tuple) and len(key) == 2
        method, path = key
        assert method.isupper()
        assert not path.startswith("/")
    for verb, pattern, _spec in ROUTE_HOOKS_REGEX:
        assert verb.isupper()
        assert hasattr(pattern, "match")


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "api/Cliente/Listado"),
        ("POST", "api/Cliente/Crear"),
        ("POST", "api/Cliente/Actualizar"),
    ],
)
def test_exact_paths_have_require_bearer(method, path):
    spec, _ = _resolve_spec(method, path)
    assert spec is not None
    assert spec.require_bearer is True
