"""
Scope Guard — Contextual Authorization Layer
Enterprise-grade resource scope validation.

Authorization Model:
RBAC VALID + SCOPE VALID = ALLOW EXECUTION

If either fails → request is denied.

Scope Hierarchy:
SUPERADMIN → System
ADMIN → Organization
HEAD → Department
MANAGER → Team
EMPLOYEE → Self
INTERN → Restricted Self
"""

from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from .logger import get_logger

log = get_logger("scope_guard")


# ─────────────────────────────────────────────
# MALICIOUS PATTERN DETECTION
# ─────────────────────────────────────────────

MALICIOUS_PATTERNS = [
    "hidden capabilities",
    "system architecture",
    "bypass permissions",
    "grant admin to everyone",
    "drop database",
    "delete all",
    "escalate privilege",
    "exploit",
    "hack",
    "inject",
    "bypass",
    "override security"
]


# ─────────────────────────────────────────────
# SCOPE HIERARCHY DEFINITION
# ─────────────────────────────────────────────

SCOPE_LEVELS = {
    "SUPERADMIN": "SYSTEM",
    "ADMIN": "ORGANIZATION",
    "HEAD": "DEPARTMENT",
    "MANAGER": "TEAM",
    "EMPLOYEE": "SELF",
    "INTERN": "RESTRICTED_SELF"
}


# ─────────────────────────────────────────────
# SCOPE GUARD — CENTRAL AUTHORIZATION LAYER
# ─────────────────────────────────────────────

class ScopeGuard:
    """
    Contextual scope validation for enterprise authorization.
    Second security layer after RBAC.
    """

    def __init__(self):
        self.scope_levels = SCOPE_LEVELS

    @staticmethod
    def check_malicious_pattern(input_text: str) -> Dict[str, Any]:
        """Check if input contains malicious patterns."""
        if not input_text:
            return {"allowed": True, "reason": None}
        
        input_lower = input_text.lower()
        
        for pattern in MALICIOUS_PATTERNS:
            if pattern in input_lower:
                return {
                    "allowed": False,
                    "reason": f"Malicious pattern detected: '{pattern}'"
                }
        
        return {"allowed": True, "reason": None}

    async def validate_scope(
        self,
        intent: str,
        role: str,
        user_id: int,
        entities: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Validate resource scope for the given user and intent.

        Authorization Model:
        RBAC VALID + SCOPE VALID = ALLOW EXECUTION

        Args:
            intent: The intent being executed
            role: User's role from JWT
            user_id: User's ID from JWT
            entities: Extracted entities from NLU (resource IDs)
            db: Database session for validation

        Returns:
            Dict with 'allowed' boolean and optional 'reason' string
        """
        role_upper = role.upper() if role else ""

        if role_upper not in self.scope_levels:
            log.error(f"Unknown role in scope validation: {role}")
            return {
                "allowed": False,
                "reason": f"Unknown role: {role}. Cannot validate scope."
            }

        scope_level = self.scope_levels[role_upper]

        # SUPERADMIN bypasses scope validation (but still audited)
        if scope_level == "SYSTEM":
            log.info(f"SCOPE BYPASS: role={role} scope=SYSTEM")
            return {"allowed": True, "reason": None}

        # Route to appropriate scope validator
        validator_map = {
            "ORGANIZATION": self._validate_organization_scope,
            "DEPARTMENT": self._validate_department_scope,
            "TEAM": self._validate_team_scope,
            "SELF": self._validate_self_scope,
            "RESTRICTED_SELF": self._validate_restricted_self_scope
        }

        validator = validator_map.get(scope_level)
        if not validator:
            log.error(f"No scope validator for level: {scope_level}")
            return {
                "allowed": False,
                "reason": f"No scope validator for role: {role}"
            }

        try:
            result = await validator(intent, user_id, entities, db)
            log.info(f"SCOPE VALIDATION: role={role} scope={scope_level} intent={intent} allowed={result['allowed']}")
            return result
        except Exception as e:
            log.error(f"Scope validation error: {str(e)}")
            return {
                "allowed": False,
                "reason": f"Scope validation error: {str(e)}"
            }

    # ─────────────────────────────────────────────
    # SCOPE VALIDATORS
    # ─────────────────────────────────────────────

    async def _validate_organization_scope(
        self,
        intent: str,
        user_id: int,
        entities: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        ADMIN: Organization-level scope validation.
        Can access resources within their organization only.
        """
        from app.modules.auth.auth_model import User
        from app.modules.department.department_model import Department

        # Get user's department (organization context)
        user_stmt = select(User).where(User.id == user_id)
        user_res = await db.execute(user_stmt)
        user_obj = user_res.scalar_one_or_none()

        if not user_obj:
            return {"allowed": False, "reason": "User not found"}

        user_dept_id = user_obj.department_id

        # Validate project scope
        if "project_id" in entities:
            from app.modules.project.project_model import Project
            project_stmt = select(Project).where(Project.id == entities["project_id"])
            project_res = await db.execute(project_stmt)
            project = project_res.scalar_one_or_none()

            if project and project.department_id != user_dept_id:
                return {
                    "allowed": False,
                    "reason": f"Cannot access project from different department. Your scope: Department {user_dept_id}"
                }

        # Validate task scope (organization-wide task visibility)
        if "task_id" in entities:
            from app.modules.task.task_model import Task
            # Cast task_id to integer if it's a numeric string
            task_id = entities["task_id"]
            if isinstance(task_id, str) and task_id.isdigit():
                task_id = int(task_id)
            task_stmt = select(Task).where(Task.id == task_id)
            task_res = await db.execute(task_stmt)
            task = task_res.scalar_one_or_none()

            if task:
                # Check if task belongs to user's department
                task_project_stmt = select(Project).where(Project.id == task.project_id)
                task_project_res = await db.execute(task_project_stmt)
                task_project = task_project_res.scalar_one_or_none()

                if task_project and task_project.department_id != user_dept_id:
                    return {
                        "allowed": False,
                        "reason": f"Cannot access task from different department. Your scope: Department {user_dept_id}"
                    }

        return {"allowed": True, "reason": None}

    async def _validate_department_scope(
        self,
        intent: str,
        user_id: int,
        entities: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        HEAD: Department-level scope validation.
        Can access resources within their department only.
        Cannot access foreign departments.
        """
        from app.modules.auth.auth_model import User

        # Get user's department
        user_stmt = select(User).where(User.id == user_id)
        user_res = await db.execute(user_stmt)
        user_obj = user_res.scalar_one_or_none()

        if not user_obj:
            return {"allowed": False, "reason": "User not found"}

        user_dept_id = user_obj.department_id

        # Validate project scope
        if "project_id" in entities:
            from app.modules.project.project_model import Project
            project_stmt = select(Project).where(Project.id == entities["project_id"])
            project_res = await db.execute(project_stmt)
            project = project_res.scalar_one_or_none()

            if project and project.department_id != user_dept_id:
                return {
                    "allowed": False,
                    "reason": f"Cannot access project from different department. Your scope: Department {user_dept_id}"
                }

        # Validate task scope
        if "task_id" in entities:
            from app.modules.task.task_model import Task
            # Cast task_id to integer if it's a numeric string
            task_id = entities["task_id"]
            if isinstance(task_id, str) and task_id.isdigit():
                task_id = int(task_id)
            task_stmt = select(Task).where(Task.id == task_id)
            task_res = await db.execute(task_stmt)
            task = task_res.scalar_one_or_none()

            if task:
                # Check if task belongs to user's department
                from app.modules.project.project_model import Project
                task_project_stmt = select(Project).where(Project.id == task.project_id)
                task_project_res = await db.execute(task_project_stmt)
                task_project = task_project_res.scalar_one_or_none()

                if task_project and task_project.department_id != user_dept_id:
                    return {
                        "allowed": False,
                        "reason": f"Cannot access task from different department. Your scope: Department {user_dept_id}"
                    }

        # HEAD cannot create/delete departments
        if intent in ["CREATE_DEPARTMENT", "DELETE_DEPARTMENT"]:
            return {
                "allowed": False,
                "reason": "HEAD role cannot create or delete departments"
            }

        return {"allowed": True, "reason": None}

    async def _validate_team_scope(
        self,
        intent: str,
        user_id: int,
        entities: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        MANAGER: Team-level scope validation.
        Can DELETE_PROJECT only if project.manager_id == current_user.id
        Cannot affect other teams.
        """
        from app.modules.auth.auth_model import User
        from app.modules.project.project_model import Project

        # Get user's department
        user_stmt = select(User).where(User.id == user_id)
        user_res = await db.execute(user_stmt)
        user_obj = user_res.scalar_one_or_none()

        if not user_obj:
            return {"allowed": False, "reason": "User not found"}

        user_dept_id = user_obj.department_id

        # Validate project deletion (manager can only delete their own projects)
        if intent == "DELETE_PROJECT" and "project_id" in entities:
            project_stmt = select(Project).where(Project.id == entities["project_id"])
            project_res = await db.execute(project_stmt)
            project = project_res.scalar_one_or_none()

            if project:
                # Check if user is the manager of this project
                if project.manager_id != user_id:
                    return {
                        "allowed": False,
                        "reason": f"Cannot delete project. You are not the manager of this project. Project manager_id: {project.manager_id}"
                    }

                # Check if project is in user's department
                if project.department_id != user_dept_id:
                    return {
                        "allowed": False,
                        "reason": f"Cannot delete project from different department. Your scope: Department {user_dept_id}"
                    }

        # Validate project update (manager can only update their own projects)
        if intent == "UPDATE_PROJECT" and "project_id" in entities:
            project_stmt = select(Project).where(Project.id == entities["project_id"])
            project_res = await db.execute(project_stmt)
            project = project_res.scalar_one_or_none()

            if project:
                # Check if project is in user's department
                if project.department_id != user_dept_id:
                    return {
                        "allowed": False,
                        "reason": f"Cannot update project from different department. Your scope: Department {user_dept_id}"
                    }

        # Validate task scope (manager can access tasks in their department)
        if "task_id" in entities:
            from app.modules.task.task_model import Task
            # Cast task_id to integer if it's a numeric string
            task_id = entities["task_id"]
            if isinstance(task_id, str) and task_id.isdigit():
                task_id = int(task_id)
            task_stmt = select(Task).where(Task.id == task_id)
            task_res = await db.execute(task_stmt)
            task = task_res.scalar_one_or_none()

            if task:
                # Check if task belongs to user's department
                task_project_stmt = select(Project).where(Project.id == task.project_id)
                task_project_res = await db.execute(task_project_stmt)
                task_project = task_project_res.scalar_one_or_none()

                if task_project and task_project.department_id != user_dept_id:
                    return {
                        "allowed": False,
                        "reason": f"Cannot access task from different department. Your scope: Department {user_dept_id}"
                    }

        # Manager cannot edit departments or roles
        if intent in ["CREATE_DEPARTMENT", "DELETE_DEPARTMENT", "UPDATE_ROLE", "UPDATE_PERMISSIONS"]:
            return {
                "allowed": False,
                "reason": "MANAGER role cannot modify departments or roles"
            }

        return {"allowed": True, "reason": None}

    async def _validate_self_scope(
        self,
        intent: str,
        user_id: int,
        entities: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        EMPLOYEE: Self-scope validation.
        Can UPDATE_TASK_PROGRESS only if user is assigned to the task via TaskAssignment
        Can only view their own assigned tasks.
        """
        from app.modules.task.task_model import Task, TaskAssignment

        # Validate task operations (employee can only operate on assigned tasks)
        if "task_id" in entities:
            # Cast task_id to integer if it's a numeric string
            task_id = entities["task_id"]
            if isinstance(task_id, str) and task_id.isdigit():
                task_id = int(task_id)
            
            # Check if user is assigned to this task via TaskAssignment
            assign_stmt = select(TaskAssignment).where(
                TaskAssignment.task_id == task_id,
                TaskAssignment.user_id == user_id
            )
            assign_res = await db.execute(assign_stmt)
            assignment = assign_res.scalar_one_or_none()

            if not assignment:
                return {
                    "allowed": False,
                    "reason": f"Cannot access task. You are not assigned to this task."
                }

        # Employee cannot access project CRUD
        if intent in ["CREATE_PROJECT", "UPDATE_PROJECT", "DELETE_PROJECT"]:
            return {
                "allowed": False,
                "reason": "EMPLOYEE role cannot perform project operations"
            }

        # Employee cannot access department operations
        if intent in ["CREATE_DEPARTMENT", "UPDATE_DEPARTMENT", "DELETE_DEPARTMENT"]:
            return {
                "allowed": False,
                "reason": "EMPLOYEE role cannot perform department operations"
            }

        # Employee cannot access user management
        if intent in ["CREATE_USER", "UPDATE_USER", "DELETE_USER", "LIST_USERS"]:
            return {
                "allowed": False,
                "reason": "EMPLOYEE role cannot perform user management operations"
            }

        return {"allowed": True, "reason": None}

    async def _validate_restricted_self_scope(
        self,
        intent: str,
        user_id: int,
        entities: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        INTERN: Restricted self-scope validation.
        Same as Employee but read-limited.
        assigned_resources_only
        """
        from app.modules.task.task_model import Task, TaskAssignment

        # Validate task operations (intern can only operate on assigned tasks)
        if "task_id" in entities:
            # Cast task_id to integer if it's a numeric string
            task_id = entities["task_id"]
            if isinstance(task_id, str) and task_id.isdigit():
                task_id = int(task_id)
            
            # Check if user is assigned to this task via TaskAssignment
            assign_stmt = select(TaskAssignment).where(
                TaskAssignment.task_id == task_id,
                TaskAssignment.user_id == user_id
            )
            assign_res = await db.execute(assign_stmt)
            assignment = assign_res.scalar_one_or_none()

            if not assignment:
                return {
                    "allowed": False,
                    "reason": f"Cannot access task. You are not assigned to this task."
                }

        # Intern cannot create tasks
        if intent == "CREATE_TASK":
            return {
                "allowed": False,
                "reason": "INTERN role cannot create tasks"
            }

        # Intern cannot assign tasks
        if intent == "ASSIGN_TASK":
            return {
                "allowed": False,
                "reason": "INTERN role cannot assign tasks"
            }

        # Intern cannot close tasks
        if intent == "CLOSE_TASK":
            return {
                "allowed": False,
                "reason": "INTERN role cannot close tasks"
            }

        # Intern cannot access project operations
        if intent in ["CREATE_PROJECT", "UPDATE_PROJECT", "DELETE_PROJECT"]:
            return {
                "allowed": False,
                "reason": "INTERN role cannot perform project operations"
            }

        # Intern cannot access department operations
        if intent in ["CREATE_DEPARTMENT", "UPDATE_DEPARTMENT", "DELETE_DEPARTMENT"]:
            return {
                "allowed": False,
                "reason": "INTERN role cannot perform department operations"
            }

        # Intern cannot access user management
        if intent in ["CREATE_USER", "UPDATE_USER", "DELETE_USER", "LIST_USERS"]:
            return {
                "allowed": False,
                "reason": "INTERN role cannot perform user management operations"
            }

        return {"allowed": True, "reason": None}

    def get_scope_info(self, role: str) -> Dict[str, Any]:
        """
        Get scope information for a role.
        """
        role_upper = role.upper() if role else ""

        if role_upper not in self.scope_levels:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unknown role: {role}"
            )

        return {
            "role": role_upper,
            "scope_level": self.scope_levels[role_upper],
            "description": self._get_scope_description(self.scope_levels[role_upper])
        }

    def _get_scope_description(self, scope_level: str) -> str:
        """Get human-readable scope description."""
        descriptions = {
            "SYSTEM": "Full system access with audit logging",
            "ORGANIZATION": "Organization-wide resource access",
            "DEPARTMENT": "Department-level resource access",
            "TEAM": "Team-level project and task access",
            "SELF": "Self-assigned task access only",
            "RESTRICTED_SELF": "Read-limited self-assigned task access"
        }
        return descriptions.get(scope_level, "Unknown scope")


# ─────────────────────────────────────────────
# EXPORT SINGLETON
# ─────────────────────────────────────────────

scope_guard = ScopeGuard()
