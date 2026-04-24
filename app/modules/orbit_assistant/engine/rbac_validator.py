"""
RBAC Validator — Role-Based Access Control enforcement.
Uses capability_resolver for centralized intent authorization.
"""

from typing import Any, Dict, List

from .logger import get_logger
from .capability_resolver import capability_resolver

log = get_logger("rbac_validator")


class RBACValidator:
    """
    Handles permission validation and capability inspection.
    Uses capability_resolver as single source of truth for RBAC.
    """

    # ─────────────────────────────────────────────
    # ROLE VALIDATION
    # ─────────────────────────────────────────────

    def validate_role(
        self,
        intent: str,
        role: str,
        config: dict = None,
    ) -> Dict[str, Any]:
        """
        Check if the user's role is permitted to execute intent.
        Uses capability_resolver for centralized authorization.
        Includes privilege escalation prevention.
        """

        # Security: Normalize role to uppercase for consistency
        role_normalized = role.upper() if role else ""
        
        # Security: Block attempts to escalate privileges
        privilege_escalation_intents = [
            "UPDATE_ROLE", "UPDATE_PERMISSIONS", "ASSIGN_ROLE",
            "UPDATE_USER", "DELETE_USER"
        ]
        
        if intent in privilege_escalation_intents:
            # Only super_admin and admin can modify roles/permissions
            if role_normalized not in ["SUPERADMIN", "ADMIN"]:
                log.warning(
                    f"Privilege escalation attempt blocked: role={role_normalized} intent={intent}"
                )
                return {
                    "allowed": False,
                    "action": intent,
                    "reason": "Only administrators can modify roles, permissions, or user accounts."
                }
        
        # Use capability_resolver for validation
        validation_result = capability_resolver.validate_intent(intent, role)

        if validation_result["allowed"]:
            print(f"[RBAC] Allowed intent: {intent} for role={role}")
            return {"allowed": True, "action": intent, "reason": None}
        else:
            print(f"[RBAC] Denied intent: {intent} for role={role}")
            return {
                "allowed": False,
                "action": intent,
                "reason": validation_result["reason"]
            }

    # ─────────────────────────────────────────────
    # CAPABILITIES VIEW
    # ─────────────────────────────────────────────

    def get_role_capabilities(
        self,
        role: str,
        config: dict = None,
    ) -> Dict[str, List[str]]:
        """
        Return allowed and restricted actions for a role.
        Uses capability_resolver for centralized capability resolution.
        """

        try:
            capabilities = capability_resolver.get_user_capabilities(role)
            global_intents = capability_resolver.global_intents

            restricted = [intent for intent in global_intents if intent not in capabilities]

            return {
                "capabilities": capabilities,
                "restricted": restricted,
            }
        except Exception as e:
            log.error(f"Error getting role capabilities: {str(e)}")
            return {
                "capabilities": [],
                "restricted": [],
            }


# ==========================================================
# EXPORT SINGLETON
# ==========================================================

rbac_validator = RBACValidator()