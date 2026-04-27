"""Custom exceptions used by the gateway."""

from __future__ import annotations

from typing import Optional


class GatewayError(Exception):
    """Base error for gateway-controlled failures."""

    code: str = "gateway_error"
    status_code: int = 500

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class UpstreamUnavailableError(GatewayError):
    """Raised when the Innovasoft API cannot be reached or times out."""

    def __init__(
        self,
        message: str = "Upstream service unavailable",
        *,
        code: str = "upstream_unavailable",
        status_code: int = 502,
    ) -> None:
        super().__init__(message, code=code)
        self.status_code = status_code


class ValidationGatewayError(GatewayError):
    """Raised for domain validation issues controlled by the gateway."""

    code = "validation_error"
    status_code = 422
