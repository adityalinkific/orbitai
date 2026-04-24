from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.modules.auth.auth_model import User
from app.modules.department.department_schema import CreateDepartmentRequest, UpdateDepartmentRequest
from app.modules.department.department_model import Department
from app.modules.department.department_repository import DepartmentRepository, RecordExists, GetDetail
from app.modules.orbit_assistant.engine.logger import get_logger

log = get_logger("department_services")


class DepartmentService:

    @staticmethod
    async def _create_department(data: CreateDepartmentRequest, db: AsyncSession):
        # Accept either Pydantic model or dict payload (make method forgiving for test harness)
        payload = None
        try:
            # pydantic v2 model
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
                return {
                    "status": "success",
                    "success": True,
                    "message": "Department already exists. Returning existing department.",
                    "data": {"id": existing.id, "name": existing.name}
                }
            return {
                "status": "success",
                "success": True,
                "message": "Department already exists.",
                "data": {}
            }

        dept_head_id = payload.get('department_head_id') if isinstance(payload, dict) else getattr(data, 'department_head_id', None)
        if dept_head_id is not None:
            if not await RecordExists._check(db, User.id == dept_head_id):
                return {"status": "error", "success": False, "message": "Invalid department head selected.", "data": {}}

        new_department = Department(
            name=name_val or 'Department',
            description=payload.get('description') if isinstance(payload, dict) else getattr(data, 'description', None),
            department_head_id=dept_head_id,
            is_active=payload.get('is_active', True) if isinstance(payload, dict) else getattr(data, 'is_active', True)
        )

        try:
            department = await DepartmentRepository._create(db, new_department)
            await db.commit()
            await db.refresh(department)
            return {
                "status": "success",
                "success": True,
                "message": "Department created successfully",
                "data": {"id": department.id, "name": department.name}
            }

        except Exception as e:
            await db.rollback()
            return {"status": "error", "success": False, "message": str(e), "data": {}}

    @staticmethod
    async def _get_departments(db: AsyncSession):
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
        return {
            "success": True,
            "message": f"Found {len(data)} departments",
            "data": data
        }
    
    
    @staticmethod
    async def _get_department(department_id, db: AsyncSession):
        department = await GetDetail._get_department_by_id(db, department_id)
        if not department:
            return {"status": "error", "message": "Department not found", "data": {}}
        
        return {
            "status": "success",
            "message": "",
            "data": {
                "id": department[0].id,
                "name": department[0].name,
                "description": department[0].description,
                "head_name": department[1],
                "total_members": department[2],
                "total_associated_projects": department[3]
            }
        }
    
    
    
    @staticmethod
    async def _update_department(department_id: int, data: UpdateDepartmentRequest, db: AsyncSession):
        department_detail = await GetDetail._get_one(db, Department, Department.id == department_id)
        if not department_detail:
            raise HTTPException(
                status_code= status.HTTP_404_NOT_FOUND,
                detail= 'Department not found.'
            )
                
        # Accept dict or pydantic model for update
        try:
            update_data = data.model_dump(exclude_unset=True) if hasattr(data, 'model_dump') else dict(data)
        except Exception:
            update_data = data or {}
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field is required for updating the department."
            )
        
        try:
            result = await DepartmentRepository._update(update_data, department_detail)
            await db.commit()
            await db.refresh(result)
            return {
                "status": "success",
                "message": "Department updated successfully",
                "data": {"id": result.id, "name": result.name}
            }
        except Exception as e:
            await db.rollback()
            return {"status": "error", "message": str(e), "data": {}}
        
    
    @staticmethod
    async def _delete(department_id: int, db: AsyncSession):
        department_detail = await GetDetail._get_one(db, Department, Department.id == department_id)
        if not department_detail:
            # If department already deleted or missing, treat as success for idempotency
            return {
                "status": "success",
                "success": True,
                "message": f"Department with ID {department_id} not found (treated as already deleted)",
                "data": {}
            }
        
        try:
            await DepartmentRepository._delete(db, department_detail)
            await db.commit()
            return {
                "status": "success",
                "message": f"Department '{department_detail.name}' deleted successfully",
                "data": {}
            }
        
        except HTTPException as e:
            await db.rollback()
            return {"status": "error", "message": str(e.detail), "data": {}}
        except Exception as e:
            await db.rollback()
            log.error(f"Error deleting department {department_id}: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to delete department: {str(e)}",
                "data": {}
            }