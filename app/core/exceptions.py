class OSINTBaseException(Exception):
    def __init__(self, message: str, code: str, status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class ConfigurationError(OSINTBaseException):
    def __init__(self, message: str):
        super().__init__(message, code="CONFIGURATION_ERROR", status_code=500)


class DatabaseError(OSINTBaseException):
    def __init__(self, message: str):
        super().__init__(message, code="DATABASE_UNAVAILABLE", status_code=503)


class ExternalServiceError(OSINTBaseException):
    def __init__(self, message: str, service_name: str):
        super().__init__(
            f"{service_name} error: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
        )


class ResourceNotFoundError(OSINTBaseException):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            f"{resource} with id '{identifier}' not found.",
            code="RESOURCE_NOT_FOUND",
            status_code=404,
        )

class AppException(Exception):
    """Base exception for the application."""
    pass

class LLMError(AppException):
    """Base exception for all LLM-related failures."""
    pass

class LLMConnectionError(LLMError):
    """Raised when the provider cannot be reached."""
    pass

class LLMTimeoutError(LLMConnectionError):
    """Raised when the provider takes too long to respond."""
    pass


class LLMProviderError(LLMError):
    """Raised when the provider returns a 5xx error or internal failure."""
    pass

class LLMInvalidResponseError(LLMError):
    """Raised when the provider returns a malformed response payload."""
    pass

class LLMStructuredOutputError(LLMError):
    """Raised when the LLM's text output fails Pydantic schema validation."""
    pass


class AppError(Exception):
    """Base exception class for application domain errors."""
    pass


class LLMConfigurationError(LLMError):
    """Raised when there is a configuration issue with the LLM factory or providers."""
    pass


class LLMAuthenticationError(LLMError):
    """Raised when provider authentication/authorization fails (e.g., HTTP 401/403)."""
    pass


class LLMRateLimitError(LLMError):
    """Raised when provider rate limits or quota thresholds are exceeded (e.g., HTTP 429)."""
    pass


class LLMResponseError(LLMError):
    """Raised when provider API returns an unexpected error format, server error (5xx), or invalid response."""
    pass