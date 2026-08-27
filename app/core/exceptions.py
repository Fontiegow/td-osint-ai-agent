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
