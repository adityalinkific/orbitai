from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.modules.auth.auth_model import User
from app.modules.department.department_schema import CreateDepartmentRequest, UpdateDepartmentRequest
from app.modules.department.department_model import Department
from app.modules.department.department_repository import DepartmentRepository, RecordExists, GetDetail
from app.core.response import success, error, not_found, conflict
from app.modules.orbit_assistant.engine.logger import get_logger

log = get_logger("department_services")


class DepartmentService:

    @staticmethod
    async def _create_department(data: CreateDepartmentRequest, db: AsyncSession):
        """Create a new department with standard response format."""
        # Accept either Pydantic model or dict payload
        try:
            if hasattr(data, 'model_dump'):
                payload = data.model_dump()
            else:
                payload = dict(data) if data is not None else {}
        except Exception:
            payload = data or {}

        name_val = payload.get('name') if isinstance(payload, dict) else getattr(data, 'name', None)

        # If department already exists, return existing department info (idempotent create)
        if name_val and await RecordExists._check(db, Department.name == name_val):
            existing = await GetDetail._get_one(db, Department, Department.name == name_val)
            if existing:
                return success(
                    message="Department already exists. Returning existing department.",
                    data={"id": existing.id, "name": existing.name}
                )
            return success(message="Department already exists.", data={})

        dept_head_id = payload.get('department_head_id') if isinstance(payload, dict) else getattr(data, 'department_head_id', None)
        if dept_head_id is not None:
            if not await RecordExists._check(db, User.id == dept_head_id):
                return error(message="Invalid department head selected.", data={})

        new_department = Department(
            name=name_val or 'Department',
            description=payload.get('description') if isinstance(payload, dict) else getattr(data, 'description', None),
            department_head_id=dept_head_id,
            is_active=payload.get('is_active', True) if isinstance(payload, dict) else getattr(data, 'is_active', True)
        )

        try:
            repo = DepartmentRepository()
            department = await repo.create(db, new_department)
            return success(
                message="Department created successfully",
                data={"id": department.id, "name": department.name}
            )
        except Exception as e:
            await db.rollback()
            log.error(f"Error creating department: {str(e)}")
            return error(message=str(e), data={})

    @staticmethod
    async def _get_departments(db: AsyncSession):
        """Get all departments with standard response format."""
        departments = await GetDetail._get_all(db, Department)
        data = [
            {
                "id": d[0].id,
                "name": d[0].name,
                "description": d[0].description,
                "head_name": d[1],
                "total_members": d[2],
                "total_projects": d[3]
            }
            for d in departments
        ]
        return success(message=f"Found {len(data)} departments", data=data)
    
    @staticmethod
    async def _get_department(department_id, db: AsyncSession):
        """Get department by ID with standard response format."""
        department = await GetDetail._get_department_by_id(db, department_id)
        if not department:
            return not_found(resource="Department", identifier=department_id)
        
        return success(
            message="",
            data={
                "id": department[0].id,
                "name": department[0].name,
                "description": department[0].description,
                "head_name": department[1],
                "total_members": department[2],
                "total_associated_projects": department[3]
            }
        )
    
    @staticmethod
    async def _update_department(department_id: int, data: UpdateDepartmentRequest, db: AsyncSession):
        """Update department with standard response format."""
        department_detail = await GetDetail._get_one(db, Department, Department.id == department_id)
        if not department_detail:
            return not_found(resource="Department", identifier=department_id)
                
        # Accept dict or pydantic model for update
        try:
            update_data = data.model_dump(exclude_unset=True) if hasattr(data, 'model_dump') else dict(data)
        except Exception:
            update_data = data or {}
        if not update_data:
            return error(message="At least one field is required for updating the department.", data={})
        
        try:
            repo = DepartmentRepository()
            result = await repo.update_instance(db, department_detail, update_data)
            return success(
                message="Department updated successfully",
                data={"id": result.id, "name": result.name}
            )
        except Exception as e:
            await db.rollback()
            log.error(f"Error updating department {department_id}: {str(e)}")
            return error(message=str(e), data={})
    
    @staticmethod
    async def _delete(department_id: int, db: AsyncSession):
        """Delete department with standard response format."""
        department_detail = await GetDetail._get_one(db, Department, Department.id == department_id)
        if not department_detail:
            # If department already deleted or missing, treat as success for idempotency
            return success(
                message=f"Department with ID {department_id} not found (treated as already deleted)",
                data={}
            )
        
        try:
            repo = DepartmentRepository()
            await repo.delete_instance(db, department_detail)
            return success(message=f"Department '{department_detail.name}' deleted successfully", data={})
        except HTTPException as e:
            await db.rollback()
            return error(message=str(e.detail), data={})
        except Exception as e:
            await db.rollback()
            log.error(f"Error deleting department {department_id}: {str(e)}")
            return error(message=f"Failed to delete department: {str(e)}", data={})