"""
Custom exceptions for xdist coordination.
"""


class CoordinationError(Exception):
    """Base exception for coordination errors."""

    pass


class CoordinationTimeout(CoordinationError):
    """Raised when coordination operations timeout."""

    def __init__(self, operation: str, timeout: float):
        self.operation = operation
        self.timeout = timeout
        super().__init__(f"Coordination timeout: {operation} failed after {timeout}s")


class WorkerNotReady(CoordinationError):
    """Raised when a worker is not ready for operation."""

    def __init__(self, worker_id: str, reason: str = None):
        self.worker_id = worker_id
        self.reason = reason
        message = f"Worker {worker_id} not ready"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class ControllerNotReady(CoordinationError):
    """Raised when the controller hasn't initialized properly."""

    def __init__(self, reason: str = None):
        self.reason = reason
        message = "Controller not ready"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class CoordinationFileError(CoordinationError):
    """Raised when coordination file operations fail."""

    def __init__(self, filepath: str, operation: str, error: Exception):
        self.filepath = filepath
        self.operation = operation
        self.original_error = error
        super().__init__(
            f"Coordination file error: {operation} failed for {filepath}: {error}"
        )


class InvalidCoordinationState(CoordinationError):
    """Raised when coordination state is invalid or corrupted."""

    def __init__(self, state_type: str, details: str = None):
        self.state_type = state_type
        self.details = details
        message = f"Invalid coordination state: {state_type}"
        if details:
            message += f" - {details}"
        super().__init__(message)
