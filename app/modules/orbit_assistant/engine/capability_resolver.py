"""
Capability Resolver — Dynamic Role-Based Access Control
Central authority for intent authorization and capability visibility.
"""

from typing import List, Dict, Any
from fastapi import HTTPException, status
from .logger import get_logger

log = get_logger("capability_resolver")


# ─────────────────────────────────────────────
# GLOBAL INTENT POOL (MASTER LIST)
# Internal use only — never exposed to users
# ─────────────────────────────────────────────

GLOBAL_INTENTS = {
    # Core
    "GREETING",
    "YES",
    "CONFIRM",

    # User Management
    "REGISTER_USER",
    "UPDATE_USER",
    "DELETE_USER",
    "LIST_USERS",
    "LIST_MY_INFO",

    # Role & Permission Governance
    "LIST_ROLES",
    "UPDATE_ROLE",
    "UPDATE_PERMISSIONS",
    "ASSIGN_ROLE",

    # Department Management (FULL CRUD)
    "CREATE_DEPARTMENT",
    "LIST_DEPARTMENTS",
    "GET_DEPARTMENT",
    "UPDATE_DEPARTMENT",
    "DELETE_DEPARTMENT",

    # Project Management (FULL CRUD)
    "CREATE_PROJECT",
    "LIST_PROJECTS",
    "GET_PROJECT",
    "UPDATE_PROJECT",
    "DELETE_PROJECT",
    "START_PROJECT",

    # Task Management
    "CREATE_TASK",
    "LIST_TASKS",
    "GET_TASK",
    "UPDATE_TASK",
    "DELETE_TASK",
    "ASSIGN_TASK",
    "CLOSE_TASK",
    "LIST_MY_TASKS",
    "UPDATE_TASK_PROGRESS",
    "REPORT_BLOCKER",
    "REQUEST_HELP",

    # Meeting Management
    "CREATE_MEETING",
    "LIST_MEETINGS",
    "GET_MEETING",
    "UPDATE_MEETING",
    "DELETE_MEETING",
    "JOIN_MEETING",
    "INVITE_USER",

    # Communication
    "SEND_EMAIL",
    "SEND_NOTIFICATION",

    # HR Operations
    "HIRE_CANDIDATE",
    "LIST_CANDIDATES",
    "UPDATE_CANDIDATE_STATUS",

    # Analytics & Dashboards
    "SHOW_ORG_DASHBOARD",
    "SHOW_DEPARTMENT_DASHBOARD",
    "SHOW_TEAM_DASHBOARD",
    "SHOW_PERSONAL_DASHBOARD",
    "ORG_PERFORMANCE_SUMMARY",
    "DEPARTMENT_STATUS_REPORT",
    "TEAM_PROGRESS_REPORT",
    "AI_ORG_INSIGHTS",
    "SYSTEM_STATUS",

    # Execution Guidance AI
    "WHAT_ARE_MY_TASKS",
    "SHOW_EXECUTION_GUIDANCE",
    "SHOW_EXPECTED_OUTPUT",
    "SHOW_NEXT_STEP",
}


# ─────────────────────────────────────────────
# ROLE CAPABILITY REGISTRY (SINGLE SOURCE OF TRUTH)
# No module defines permissions independently
# ─────────────────────────────────────────────

ROLE_CAPABILITIES = {
    "SUPERADMIN": {
        "GREETING",
        "LIST_MY_INFO",

        "REGISTER_USER",
        "UPDATE_USER",
        "DELETE_USER",
        "LIST_USERS",

        "LIST_ROLES",
        "UPDATE_ROLE",
        "UPDATE_PERMISSIONS",
        "ASSIGN_ROLE",

        "CREATE_DEPARTMENT",
        "LIST_DEPARTMENTS",
        "GET_DEPARTMENT",
        "UPDATE_DEPARTMENT",
        "DELETE_DEPARTMENT",
        "ENTERPRISE_REASONING",
        "AI_ORG_INSIGHTS",

        "CREATE_PROJECT",
        "LIST_PROJECTS",
        "GET_PROJECT",
        "UPDATE_PROJECT",
        "DELETE_PROJECT",
        "START_PROJECT",

        "CREATE_TASK",
        "LIST_TASKS",
        "GET_TASK",
        "UPDATE_TASK",
        "DELETE_TASK",
        "ASSIGN_TASK",
        "CLOSE_TASK",
        "LIST_MY_TASKS",

        "SYSTEM_STATUS",
        "SEND_NOTIFICATION",
    },

    "ADMIN": {
        "GREETING",
        "LIST_MY_INFO",

        "LIST_USERS",
        "UPDATE_USER",
        "DELETE_USER",
        "LIST_DEPARTMENTS",
        "GET_DEPARTMENT",
        "LIST_ROLES",
        "UPDATE_ROLE",
        "UPDATE_PERMISSIONS",

        "LIST_PROJECTS",
        "GET_PROJECT",

        "LIST_TASKS",
        "GET_TASK",

        "LIST_MEETINGS",
        "GET_MEETING",

        "SHOW_ORG_DASHBOARD",
        "ORG_PERFORMANCE_SUMMARY",
        "AI_ORG_INSIGHTS",
        "DEPARTMENT_STATUS_REPORT",
        "TEAM_PROGRESS_REPORT",

        "SEND_EMAIL",
        "SEND_NOTIFICATION",
    },

    "HEAD": {
        "GREETING",
        "LIST_MY_INFO",

        "LIST_DEPARTMENTS",
        "GET_DEPARTMENT",

        "LIST_USERS",

        "LIST_PROJECTS",
        "GET_PROJECT",
        "UPDATE_PROJECT",

        "LIST_TASKS",
        "GET_TASK",

        "CREATE_MEETING",
        "UPDATE_MEETING",
        "LIST_MEETINGS",

        "SHOW_DEPARTMENT_DASHBOARD",
        "DEPARTMENT_STATUS_REPORT",
        "TEAM_PROGRESS_REPORT",

        "INVITE_USER",
        "SEND_EMAIL",
    },

    "MANAGER": {
        "GREETING",
        "LIST_MY_INFO",

        "CREATE_PROJECT",
        "LIST_PROJECTS",
        "GET_PROJECT",
        "UPDATE_PROJECT",
        "DELETE_PROJECT",
        "START_PROJECT",

        "CREATE_TASK",
        "LIST_TASKS",
        "GET_TASK",
        "UPDATE_TASK",
        "DELETE_TASK",
        "ASSIGN_TASK",
        "CLOSE_TASK",

        "LIST_MY_TASKS",
        "REPORT_BLOCKER",

        "CREATE_MEETING",
        "UPDATE_MEETING",
        "DELETE_MEETING",
        "INVITE_USER",
        "LIST_MEETINGS",

        "SHOW_TEAM_DASHBOARD",
        "TEAM_PROGRESS_REPORT",

        "SEND_EMAIL",
        "SEND_NOTIFICATION",
    },

    "EMPLOYEE": {
        "GREETING",
        "LIST_MY_INFO",

        "WHAT_ARE_MY_TASKS",
        "LIST_MY_TASKS",
        "GET_TASK",

        "UPDATE_TASK_PROGRESS",
        "REPORT_BLOCKER",
        "REQUEST_HELP",

        "JOIN_MEETING",
        "LIST_MEETINGS",
        "GET_MEETING",

        "SHOW_PERSONAL_DASHBOARD",
        "SHOW_EXECUTION_GUIDANCE",
        "SHOW_EXPECTED_OUTPUT",
    },

    "INTERN": {
        "GREETING",
        "LIST_MY_INFO",

        "WHAT_ARE_MY_TASKS",
        "LIST_MY_TASKS",
        "GET_TASK",

        "UPDATE_TASK_PROGRESS",
        "REQUEST_HELP",
        "SHOW_NEXT_STEP",
        "SHOW_EXECUTION_GUIDANCE",

        "JOIN_MEETING",
        "GET_MEETING",

        "SHOW_PERSONAL_DASHBOARD",
    },
}


# ─────────────────────────────────────────────
# CAPABILITY RESOLVER
# ─────────────────────────────────────────────

class CapabilityResolver:
    """
    Dynamic capability resolution based on user role.
    Enforces enterprise governance boundaries.
    """

    def __init__(self):
        self.global_intents = GLOBAL_INTENTS
        self.role_capabilities = ROLE_CAPABILITIES

    def get_user_capabilities(self, role: str) -> List[str]:
        """
        Get allowed capabilities for a user based on their role.

        Rules:
        1. Extract role from JWT token (passed as parameter)
        2. Read ROLE_CAPABILITIES[user.role]
        3. Return ONLY allowed intents
        4. NEVER expose GLOBAL_INTENTS
        5. NEVER merge capabilities across roles
        6. Assistant responses must reflect ONLY permitted actions

        Args:
            role: User's role from JWT token

        Returns:
            List of allowed intent strings for the role

        Raises:
            HTTPException: If role is not recognized
        """
        role_upper = role.upper() if role else ""

        if role_upper not in self.role_capabilities:
            log.error(f"Unknown role in capability resolution: {role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unknown role: {role}. Cannot resolve capabilities."
            )

        capabilities = self.role_capabilities[role_upper]
        log.info(f"Capability resolution: role={role_upper} capabilities={len(capabilities)}")

        return sorted(list(capabilities))

    def validate_intent(self, intent: str, role: str) -> Dict[str, Any]:
        """
        Validate if a user's role permits execution of an intent.

        Args:
            intent: The intent to validate
            role: User's role from JWT token

        Returns:
            Dict with 'allowed' boolean and optional 'reason' string
        """
        role_upper = role.upper() if role else ""

        if role_upper not in self.role_capabilities:
            log.error(f"Unknown role in intent validation: {role}")
            return {
                "allowed": False,
                "reason": f"Unknown role: {role}. Cannot validate intent."
            }

        allowed_intents = self.role_capabilities[role_upper]

        if intent in allowed_intents:
            log.info(f"Intent ALLOWED: role={role_upper} intent={intent}")
            return {"allowed": True, "reason": None}
        else:
            log.warning(f"Intent DENIED: role={role_upper} intent={intent}")
            return {
                "allowed": False,
                "reason": f"Role '{role}' is not permitted to execute '{intent}'. "
                         f"Required role capability not found."
            }

    def get_role_info(self, role: str) -> Dict[str, Any]:
        """
        Get role metadata including hierarchy level and capability count.

        Args:
            role: User's role from JWT token

        Returns:
            Dict with role information
        """
        role_upper = role.upper() if role else ""

        if role_upper not in self.role_capabilities:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unknown role: {role}"
            )

        hierarchy = {
            "SUPERADMIN": 1,
            "ADMIN": 2,
            "HEAD": 3,
            "MANAGER": 4,
            "EMPLOYEE": 5,
            "INTERN": 6,
        }

        return {
            "role": role_upper,
            "hierarchy_level": hierarchy.get(role_upper, 999),
            "capability_count": len(self.role_capabilities[role_upper]),
            "can_execute": sorted(list(self.role_capabilities[role_upper]))
        }


# ─────────────────────────────────────────────
# EXPORT SINGLETON
# ─────────────────────────────────────────────

capability_resolver = CapabilityResolver()
