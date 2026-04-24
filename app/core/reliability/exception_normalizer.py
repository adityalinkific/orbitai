from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from app.modules.orbit_assistant.engine.logger import get_logger

log = get_logger("exception_normalizer")


class NormalizedError(Exception):
    """Base class for normalized errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def normalize_exception(exc: Exception) -> Dict[str, Any]:
    """
    Normalize any exception into a standard error response.
    
    Args:
        exc: The exception to normalize
    
    Returns:
        Standardized error dictionary
    """
    # Already normalized
    if isinstance(exc, NormalizedError):
        return {
            "status": "error",
            "success": False,
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details
        }
    
    # HTTPException (FastAPI)
    if isinstance(exc, HTTPException):
        return {
            "status": "error",
            "success": False,
            "message": exc.detail,
            "error_code": f"HTTP_{exc.status_code}",
            "details": {}
        }
    
    # SQLAlchemy errors
    if isinstance(exc, IntegrityError):
        log.error(f"Database integrity error: {str(exc)}")
        return {
            "status": "error",
            "success": False,
            "message": "Database integrity violation. Record may already exist.",
            "error_code": "DB_INTEGRITY_ERROR",
            "details": {}
        }
    
    if isinstance(exc, OperationalError):
        log.error(f"Database operational error: {str(exc)}")
        return {
            "status": "error",
            "success": False,
            "message": "Database operation failed. Please try again.",
            "error_code": "DB_OPERATIONAL_ERROR",
            "details": {}
        }
    
    if isinstance(exc, SQLAlchemyError):
        log.error(f"Database error: {str(exc)}")
        return {
            "status": "error",
            "success": False,
            "message": "Database error occurred.",
            "error_code": "DB_ERROR",
            "details": {}
        }
    
    # Generic exception
    log.exception(f"Unhandled exception: {str(exc)}")
    return {
        "status": "error",
        "success": False,
        "message": "An unexpected error occurred.",
        "error_code": "INTERNAL_ERROR",
        "details": {}
    }


def create_http_exception(normalized_error: Dict[str, Any]) -> HTTPException:
    """Convert normalized error to HTTPException."""
    status_code = normalized_error.get("status_code", 500)
    return HTTPException(
        status_code=status_code,
        detail={
            "status": normalized_error.get("status", "error"),
            "success": False,
            "message": normalized_error.get("message", "An error occurred"),
            "error_code": normalized_error.get("error_code", "UNKNOWN_ERROR"),
            "details": normalized_error.get("details", {})
        }
    )


# Specific error classes
class ValidationError(NormalizedError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class NotFoundError(NormalizedError):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            error_code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "identifier": identifier}
        )


class ConflictError(NormalizedError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=409,
            details=details
        )


class UnauthorizedError(NormalizedError):
    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(
            message=message,
            error_code="UNAUTHORIZED",
            status_code=401
        )


class ForbiddenError(NormalizedError):
    def __init__(self, message: str = "Access forbidden"):
        super().__init__(
            message=message,
            error_code="FORBIDDEN",
            status_code=403
        )


class RateLimitError(NormalizedError):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429
        )


class ServiceUnavailableError(NormalizedError):
    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(
            message=message,
            error_code="SERVICE_UNAVAILABLE",
            status_code=503
        )
