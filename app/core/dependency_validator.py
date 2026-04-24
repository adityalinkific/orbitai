"""
Data Dependency Validation Layer

Validates all data dependencies before capability execution to ensure:
- Required entities exist
- Required IDs are valid
- Relationships are valid
- Ownership/department constraints are met
- RBAC constraints are satisfied
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.modules.auth.auth_model import User, Role
from app.modules.department.department_model import Department
from app.modules.project.project_model import Project
from app.modules.task.task_model import Task, TaskAssignment


class DependencyValidationError(Exception):
    """Raised when dependency validation fails."""
    pass


class DependencyValidator:
    """Validates data dependencies for capability execution."""
    
    @staticmethod
    async def validate_user_exists(db: AsyncSession, user_id: int) -> User:
        """Validate that a user exists."""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        if not user:
            raise DependencyValidationError(f"User with ID {user_id} not found")
        return user
    
    @staticmethod
    async def validate_role_exists(db: AsyncSession, role_id: int) -> Role:
        """Validate that a role exists."""
        stmt = select(Role).where(Role.id == role_id)
        result = await db.execute(stmt)
        role = result.scalars().first()
        if not role:
            raise DependencyValidationError(f"Role with ID {role_id} not found")
        return role
    
    @staticmethod
    async def validate_department_exists(db: AsyncSession, department_id: int) -> Department:
        """Validate that a department exists."""
        stmt = select(Department).where(Department.id == department_id)
        result = await db.execute(stmt)
        department = result.scalars().first()
        if not department:
            raise DependencyValidationError(f"Department with ID {department_id} not found")
        return department
    
    @staticmethod
    async def validate_project_exists(db: AsyncSession, project_id: int) -> Project:
        """Validate that a project exists."""
        stmt = select(Project).where(Project.id == project_id)
        result = await db.execute(stmt)
        project = result.scalars().first()
        if not project:
            raise DependencyValidationError(f"Project with ID {project_id} not found")
        return project
    
    @staticmethod
    async def validate_task_exists(db: AsyncSession, task_id: int) -> Task:
        """Validate that a task exists."""
        stmt = select(Task).where(Task.id == task_id)
        result = await db.execute(stmt)
        task = result.scalars().first()
        if not task:
            raise DependencyValidationError(f"Task with ID {task_id} not found")
        return task
    
    @staticmethod
    async def validate_task_assignment_exists(db: AsyncSession, assignment_id: int) -> TaskAssignment:
        """Validate that a task assignment exists."""
        stmt = select(TaskAssignment).where(TaskAssignment.id == assignment_id)
        result = await db.execute(stmt)
        assignment = result.scalars().first()
        if not assignment:
            raise DependencyValidationError(f"Task assignment with ID {assignment_id} not found")
        return assignment
    
    @staticmethod
    async def validate_department_ownership(
        db: AsyncSession, 
        user: User, 
        department_id: int,
        require_match: bool = False
    ) -> bool:
        """
        Validate department ownership/access.
        
        Args:
            db: Database session
            user: Current user
            department_id: Department ID to validate
            require_match: If True, user must belong to the department
        
        Returns:
            True if validation passes
            
        Raises:
            DependencyValidationError: If validation fails
        """
        if not department_id:
            raise DependencyValidationError("Department ID is required")
        
        # Validate department exists
        department = await DependencyValidator.validate_department_exists(db, department_id)
        
        # Check if user belongs to department (if required)
        if require_match and user.department_id != department_id:
            # Allow admins/managers to access other departments
            if user.role.role not in ["super_admin", "admin", "manager"]:
                raise DependencyValidationError(
                    f"User does not have access to department {department_id}"
                )
        
        return True
    
    @staticmethod
    async def validate_project_ownership(
        db: AsyncSession,
        user: User,
        project_id: int,
        require_ownership: bool = False
    ) -> bool:
        """
        Validate project ownership/access.
        
        Args:
            db: Database session
            user: Current user
            project_id: Project ID to validate
            require_ownership: If True, user must be the project manager
        
        Returns:
            True if validation passes
            
        Raises:
            DependencyValidationError: If validation fails
        """
        if not project_id:
            raise DependencyValidationError("Project ID is required")
        
        # Validate project exists
        project = await DependencyValidator.validate_project_exists(db, project_id)
        
        # Check ownership (if required)
        if require_ownership:
            if project.manager_id != user.id:
                # Allow admins to bypass ownership check
                if user.role.role not in ["super_admin", "admin"]:
                    raise DependencyValidationError(
                        f"User is not the manager of project {project_id}"
                    )
        
        # Check department access
        await DependencyValidator.validate_department_ownership(
            db, user, project.department_id, require_match=False
        )
        
        return True
    
    @staticmethod
    async def validate_task_ownership(
        db: AsyncSession,
        user: User,
        task_id: int,
        require_ownership: bool = False
    ) -> bool:
        """
        Validate task ownership/access.
        
        Args:
            db: Database session
            user: Current user
            task_id: Task ID to validate
            require_ownership: If True, user must be the task manager or creator
        
        Returns:
            True if validation passes
            
        Raises:
            DependencyValidationError: If validation fails
        """
        if not task_id:
            raise DependencyValidationError("Task ID is required")
        
        # Validate task exists
        task = await DependencyValidator.validate_task_exists(db, task_id)
        
        # Check ownership (if required)
        if require_ownership:
            if task.manager_id != user.id and task.created_by != user.id:
                # Allow admins to bypass ownership check
                if user.role.role not in ["super_admin", "admin"]:
                    raise DependencyValidationError(
                        f"User is not the manager or creator of task {task_id}"
                    )
        
        # Check department access
        await DependencyValidator.validate_department_ownership(
            db, user, task.department_id, require_match=False
        )
        
        # Check project access (if task has a project)
        if task.project_id:
            await DependencyValidator.validate_project_ownership(
                db, user, task.project_id, require_ownership=False
            )
        
        return True
    
    @staticmethod
    async def validate_task_assignment_access(
        db: AsyncSession,
        user: User,
        assignment_id: int,
        require_assignee: bool = False
    ) -> bool:
        """
        Validate task assignment access.
        
        Args:
            db: Database session
            user: Current user
            assignment_id: Assignment ID to validate
            require_assignee: If True, user must be the assignee
        
        Returns:
            True if validation passes
            
        Raises:
            DependencyValidationError: If validation fails
        """
        if not assignment_id:
            raise DependencyValidationError("Assignment ID is required")
        
        # Validate assignment exists
        assignment = await DependencyValidator.validate_task_assignment_exists(db, assignment_id)
        
        # Check if user is the assignee (if required)
        if require_assignee and assignment.user_id != user.id:
            # Allow admins/managers to bypass
            if user.role.role not in ["super_admin", "admin", "manager"]:
                raise DependencyValidationError(
                    f"User is not the assignee of assignment {assignment_id}"
                )
        
        # Check task access
        await DependencyValidator.validate_task_ownership(
            db, user, assignment.task_id, require_ownership=False
        )
        
        return True
    
    @staticmethod
    async def validate_user_registration_dependencies(
        db: AsyncSession,
        role_id: int,
        department_id: int,
        reporting_manager_id: Optional[int] = None
    ) -> bool:
        """
        Validate dependencies for user registration.
        
        Args:
            db: Database session
            role_id: Role ID for the new user
            department_id: Department ID for the new user
            reporting_manager_id: Optional reporting manager ID
        
        Returns:
            True if validation passes
            
        Raises:
            DependencyValidationError: If validation fails
        """
        # Validate role exists
        await DependencyValidator.validate_role_exists(db, role_id)
        
        # Validate department exists
        await DependencyValidator.validate_department_exists(db, department_id)
        
        # Validate reporting manager (if provided)
        if reporting_manager_id:
            await DependencyValidator.validate_user_exists(db, reporting_manager_id)
        
        return True
    
    @staticmethod
    async def validate_task_creation_dependencies(
        db: AsyncSession,
        user: User,
        department_id: int,
        project_id: Optional[int] = None,
        manager_id: Optional[int] = None
    ) -> bool:
        """
        Validate dependencies for task creation.
        
        Args:
            db: Database session
            user: Current user
            department_id: Department ID for the task
            project_id: Optional project ID
            manager_id: Optional manager ID
        
        Returns:
            True if validation passes
            
        Raises:
            DependencyValidationError: If validation fails
        """
        # Validate department access
        await DependencyValidator.validate_department_ownership(
            db, user, department_id, require_match=False
        )
        
        # Validate project (if provided)
        if project_id:
            await DependencyValidator.validate_project_ownership(
                db, user, project_id, require_ownership=False
            )
        
        # Validate manager (if provided)
        if manager_id:
            await DependencyValidator.validate_user_exists(db, manager_id)
        
        return True
    
    @staticmethod
    async def validate_project_creation_dependencies(
        db: AsyncSession,
        user: User,
        department_id: int,
        manager_id: Optional[int] = None
    ) -> bool:
        """
        Validate dependencies for project creation.
        
        Args:
            db: Database session
            user: Current user
            department_id: Department ID for the project
            manager_id: Optional manager ID
        
        Returns:
            True if validation passes
            
        Raises:
            DependencyValidationError: If validation fails
        """
        # Validate department access
        await DependencyValidator.validate_department_ownership(
            db, user, department_id, require_match=False
        )
        
        # Validate manager (if provided)
        if manager_id:
            await DependencyValidator.validate_user_exists(db, manager_id)
        
        return True


async def validate_capability_dependencies(
    capability: str,
    db: AsyncSession,
    user: User,
    entities: Dict[str, Any]
) -> bool:
    """
    Validate dependencies for a specific capability.
    
    Args:
        capability: The capability/intent name
        db: Database session
        user: Current user
        entities: Extracted entities from the request
        
    Returns:
        True if validation passes
        
    Raises:
        DependencyValidationError: If validation fails
    """
    validators = {
        "CREATE_TASK": lambda: DependencyValidator.validate_task_creation_dependencies(
            db, user,
            department_id=entities.get("department_id"),
            project_id=entities.get("project_id"),
            manager_id=entities.get("manager_id")
        ),
        "UPDATE_TASK": lambda: DependencyValidator.validate_task_ownership(
            db, user, entities.get("task_id"), require_ownership=False
        ),
        "DELETE_TASK": lambda: DependencyValidator.validate_task_ownership(
            db, user, entities.get("task_id"), require_ownership=True
        ),
        "ASSIGN_TASK": lambda: DependencyValidator.validate_task_ownership(
            db, user, entities.get("task_id"), require_ownership=False
        ),
        "CREATE_PROJECT": lambda: DependencyValidator.validate_project_creation_dependencies(
            db, user,
            department_id=entities.get("department_id"),
            manager_id=entities.get("manager_id")
        ),
        "UPDATE_PROJECT": lambda: DependencyValidator.validate_project_ownership(
            db, user, entities.get("project_id"), require_ownership=False
        ),
        "DELETE_PROJECT": lambda: DependencyValidator.validate_project_ownership(
            db, user, entities.get("project_id"), require_ownership=True
        ),
        "REGISTER_USER": lambda: DependencyValidator.validate_user_registration_dependencies(
            db,
            role_id=entities.get("role_id"),
            department_id=entities.get("department_id"),
            reporting_manager_id=entities.get("reporting_manager_id")
        ),
        "UPDATE_USER": lambda: DependencyValidator.validate_user_exists(
            db, entities.get("user_id")
        ),
        "DELETE_USER": lambda: DependencyValidator.validate_user_exists(
            db, entities.get("user_id")
        ),
    }
    
    validator = validators.get(capability)
    if validator:
        return await validator()
    
    # If no specific validator exists, assume validation passes
    return True
