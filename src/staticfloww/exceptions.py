class StaticflowwError(Exception):
    """Base exception for all StaticFlow errors."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

# --- Configuration & Setup ---
class ConfigurationError(StaticflowwError):
    """Raised when the gateway is misconfigured."""
    pass

# --- Routing & Extraction ---
class RoutingError(StaticflowwError):
    """Base for routing related issues."""
    pass

class RouteNotFoundError(RoutingError):
    """Raised when no route is registered for a given request type."""
    def __init__(self, request_type: str):
        super().__init__(f"No route registered for request type: {request_type}", status_code=404)

class ExtractionError(StaticflowwError):
    """Raised when a required section cannot be plucked from the God Schema."""
    def __init__(self, section_name: str):
        super().__init__(f"Required section '{section_name}' missing from payload", status_code=400)

# --- Validation ---
class ValidationError(StaticflowwError):
    """Base for validation issues."""
    pass

class RequestValidationError(ValidationError):
    """Raised when the extracted data fails request_model validation."""
    def __init__(self, details: str):
        super().__init__(f"Request validation failed: {details}", status_code=400)

class ResponseValidationError(ValidationError):
    """Raised when the upstream response fails response_model validation."""
    def __init__(self, details: str):
        super().__init__(f"Response validation failed: {details}", status_code=502)

# --- Upstream / Proxy ---
class ProxyError(StaticflowwError):
    """Base for upstream communication issues."""
    pass

class UpstreamTimeoutError(ProxyError):
    """Raised when an upstream request times out."""
    def __init__(self):
        super().__init__("Upstream request timed out", status_code=504)

class UpstreamConnectionError(ProxyError):
    """Raised when connection to upstream fails."""
    def __init__(self):
        super().__init__("Failed to connect to upstream service", status_code=502)

class UpstreamResponseError(ProxyError):
    """Raised when upstream returns a 4xx or 5xx status code."""
    def __init__(self, status_code: int, details: str):
        super().__init__(f"Upstream returned error {status_code}: {details}", status_code=status_code)

# --- Hooks & Logic ---
class HookError(StaticflowwError):
    """Raised when a before_request or after_response hook fails."""
    pass

# --- Authentication ---
class AuthError(StaticflowwError):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)
