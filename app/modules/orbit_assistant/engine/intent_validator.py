"""
Intent Validator — Validates NLU output against Orbit configuration.
Ensures only supported intents execute.
"""

from typing import Dict, Any

from .logger import get_logger
from .error_handler import OrbitError, ErrorType

log = get_logger("intent_validator")


class IntentValidator:
    """
    Validates parsed intent + entities before execution.
    """

    # All intents that the executor can handle directly
    # (not in config.yaml but handled by executor)
    EXECUTOR_DIRECT_INTENTS = {
        "HELLO",
        "GREETING",
        "LIST_MY_INFO",
        "LIST_MANAGEABLE_TASKS",
        "UNKNOWN",
        "CLARIFICATION_REQUIRED",
        "YES",
        "CONFIRM",
        # Aliases & direct intents handled by executor
        "SHOW_PROJECT_DETAILS",
        "GET_PROJECT",
        "LIST_DEPARTMENT_DETAILS",
        "GET_DEPARTMENT",
        "SHOW_DEPARTMENT",
        "SHOW_TASK_DETAILS",
        "GET_TASK",
        "REGISTER_USER",
        "ADD_MEMBER",
        "UPDATE_EMAIL",
        "UPDATE_USER",
        "UPDATE_DEPARTMENT",
        "UPDATE_PERMISSIONS",
        "UPDATE_ROLE",
        "UPDATE_ROLE_PERMISSIONS",
        "LIST_MY_TASKS",
        "START_PROJECT",
        "CLOSE_TASK",
        "HIRE_CANDIDATE",
        "SEND_EMAIL",
        "SYSTEM_STATUS",
        "ENTERPRISE_REASONING",
        "DELETE_DEPARTMENT",
        "DELETE_USER",
        "CREATE_DEPARTMENT",
        "LIST_DEPARTMENTS",
        "LIST_USERS",
        "LIST_ROLES",
        "SEND_NOTIFICATION",
        "ASSIGN_ROLE",
    }

    def validate(self, parsed: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate intent returned from NLU.

        Args:
            parsed: NLU parsed output
            config: orbit config (intents + workflows)

        Returns:
            validated parsed dict
        """

        if not parsed:
            raise OrbitError(
                error_type=ErrorType.INVALID_INTENT,
                message="NLU returned empty response.",
            )

        intent = parsed.get("intent")
        entities = parsed.get("entities", {})
        print(f"[VALIDATOR] Checking intent: {intent}")

        if not intent:
            raise OrbitError(
                error_type=ErrorType.INVALID_INTENT,
                message="Intent missing from NLU output.",
            )

        # Build allowed intents
        allowed_intents = set(config.get("intents", {}).keys())
        allowed_workflows = set(config.get("workflows", {}).keys())

        all_allowed = allowed_intents | allowed_workflows | self.EXECUTOR_DIRECT_INTENTS

        if intent not in all_allowed:
            log.warning(f"Unsupported intent detected: {intent}")

            raise OrbitError(
                error_type=ErrorType.INVALID_INTENT,
                message=f"Orbit cannot execute '{intent.replace('_', ' ').lower()}' yet.",
                details={"intent": intent},
            )

        log.info(f"Intent validated successfully → {intent}")

        return {
            "intent": intent,
            "entities": entities,
            "confidence": parsed.get("confidence", 0.0),
        }


# ==========================================================
# EXPORT SINGLETON (THIS FIXES YOUR IMPORT ERROR)
# ==========================================================

intent_validator = IntentValidator()