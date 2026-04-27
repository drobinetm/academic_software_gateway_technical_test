class GatewayError(Exception):
    code: str = "gateway_error"
    status_code: int = 500

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class UpstreamUnavailableError(GatewayError):
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
    code = "validation_error"
    status_code = 422


class StartupError(GatewayError):
    """Raised when a non-critical startup task fails (indexes, OpenAPI schema load).

    Swallowed at the call site so the application still starts.
    """

    code = "startup_error"
    status_code = 500


class RequestLogError(GatewayError):
    """Raised when persisting an HTTP request log entry to MongoDB fails.

    Swallowed at the call site so logging failures never affect responses.
    """

    code = "request_log_error"
    status_code = 500


class OperationLogError(GatewayError):
    """Raised when persisting a CRUD audit record to MongoDB fails.

    Swallowed at the call site so audit failures never affect responses.
    """

    code = "operation_log_error"
    status_code = 500


class AuditExtractionError(GatewayError):
    """Raised when a RouteSpec client_id_extractor callable fails.

    Swallowed at the call site; the audit record is still written with client_id=None.
    """

    code = "audit_extraction_error"
    status_code = 500
