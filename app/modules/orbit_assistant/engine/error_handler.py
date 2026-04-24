"""
Structured error handling for the Orbit Governance Assistant.
Normalizes failures across the entire execution pipeline.
"""

from enum import Enum
from typing import Any, Optional

from app.modules.orbit_assistant.engine.logger import get_logger

log = get_logger("error_handler")

# =====================================================

# ERROR TYPES

# =====================================================

class ErrorType(str, Enum):
    LLM_PARSE_FAILURE = "llm_parse_failure"
    API_TIMEOUT = "api_timeout"
    API_ERROR = "api_error"
    INVALID_PAYLOAD = "invalid_payload"
    PERMISSION_DENIED = "permission_denied"
    WORKFLOW_PARTIAL = "workflow_partial"
    AMBIGUOUS_MATCH = "ambiguous_match"
    INVALID_INTENT = "invalid_intent"
    UNKNOWN = "unknown"

# =====================================================

# CUSTOM ERROR

# =====================================================

class OrbitError(Exception):

    def __init__(
        self,
        error_type: ErrorType,
        message: str,
        details: Optional[dict] = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        self.retryable = retryable

# =====================================================

# ERROR HANDLER

# =====================================================

class ErrorHandler:

    def handle_error(self, error: Exception) -> dict[str, Any]:
        """
        Convert ANY exception into structured API response.
        """

        if isinstance(error, OrbitError):

            log.error(
                f"[{error.error_type.value}] {error.message}",
                extra={"details": error.details},
            )

            return {
                "success": False,
                "error_type": error.error_type.value,
                "message": self._user_message(error),
                "details": self._sanitize(error.details),
                "retryable": error.retryable,
            }

        # ---------- Unknown Exception ----------
        log.exception("Unhandled Orbit exception")

        return {
            "success": False,
            "error_type": ErrorType.UNKNOWN.value,
            "message": "An unexpected system error occurred.",
            "details": {},
            "retryable": True,
        }

    # -------------------------------------------------
    def _sanitize(self, details: dict) -> dict:
        """
        Prevent leaking internal IDs.
        """
        return {
            k: v
            for k, v in details.items()
            if not k.endswith("_id")
        }

    # -------------------------------------------------
    def _user_message(self, error: OrbitError) -> str:

        mapping = {
            ErrorType.LLM_PARSE_FAILURE:
                "I couldn't understand that request. Please rephrase.",

            ErrorType.API_TIMEOUT:
                self._retry_hint(error),

            ErrorType.API_ERROR:
                "Action failed. Please verify provided data.",

            ErrorType.INVALID_PAYLOAD:
                f"Missing information: {error.message.replace('_id','').replace('_',' ')}.",

            ErrorType.PERMISSION_DENIED:
                "You don't have permission to perform this action.",

            ErrorType.WORKFLOW_PARTIAL:
                "Workflow completed partially.",

            ErrorType.AMBIGUOUS_MATCH:
                f"Multiple matches found for {error.message}. Please be specific.",

            ErrorType.INVALID_INTENT:
                f"{error.message}",

            ErrorType.UNKNOWN:
                "Unexpected system error occurred.",
        }

        return mapping.get(error.error_type, error.message)

    # -------------------------------------------------
    def _retry_hint(self, error: OrbitError) -> str:
        return (
            "The service timed out. You can retry this action."
            if error.retryable
            else "The service timed out."
        )

# =====================================================

# REQUIRED SINGLETON EXPORT

# =====================================================

error_handler = ErrorHandler()
