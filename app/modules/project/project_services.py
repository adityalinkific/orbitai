from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.modules.department.department_model import Department
from app.modules.project.project_model import Project
from app.modules.project.project_schema import ProjectRequestSchema, ProjectUpdateSchema
from app.modules.project.project_repository import ProjectRepository, DetailsExist, GetProjects

class ProjectService:

    @staticmethod
    async def create_project(db: AsyncSession, data: ProjectRequestSchema, current_user):
        # Adaptive handling for pydantic models or raw dictionaries
        try:
            payload = data.model_dump() if hasattr(data, 'model_dump') else dict(data)
        except Exception:
            payload = data or {}

        name_val = payload.get('name')
        dept_id = payload.get('department_id') or getattr(current_user, 'department_id', None)
        desc_val = payload.get('description')

        if not name_val:
            raise HTTPException(status_code=400, detail="Project name is required")
        
        project_exists = await DetailsExist._exists(db, Project.name, name_val)
        if project_exists:
            # For idempotency, if it exists just return success
            from app.modules.project.project_repository import GetProjects
            existing = await GetProjects._get_by_name(db, name_val)
            return {
                "success": True,
                "message": "Project already exists",
                "data": {"id": existing.id, "name": existing.name}
            }
        
        if dept_id and not await DetailsExist._exists(db, Department.id, dept_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid department selected"
            )
        
        project_data = Project(
            name=name_val,
            description=desc_val,
            department_id=dept_id,
        )
        try:
            project = await ProjectRepository._create(db, project_data)
            await db.commit()
            await db.refresh(project)
            return {
                "success": True,
                "message": "Project created successfully",
                "data": {"id": project.id, "name": project.name}
            }
        except Exception as e:
            await db.rollback()
            return {"success": False, "message": str(e)}

    @staticmethod
    async def update_project(db: AsyncSession, project_id: int, data):
        try:
            update_data = data.model_dump(exclude_unset=True) if hasattr(data, 'model_dump') else dict(data)
        except Exception:
            update_data = data or {}
            
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field is required for updating the project."
            )
            
        dept_id = update_data.get('department_id') if isinstance(data, dict) else getattr(data, 'department_id', None)
        if dept_id is not None and not await DetailsExist._exists(db, Department.id, dept_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid department selected"
            )

        project = await GetProjects._get_by_id(db, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
            
        # update_data is already defined above
        
        try:
            project = await ProjectRepository._update(db, update_data, project)
            await db.commit()
            await db.refresh(project)
            return {
                "success": True,
                "message": "Project updated successfully",
                "data": {"id": project.id, "name": project.name}
            }
        except Exception as e:
            await db.rollback()
            return {"success": False, "message": str(e)}

    @staticmethod
    async def delete_project(db: AsyncSession, project_id: int):
        project = await GetProjects._get_by_id(db, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        try:
            await ProjectRepository._delete(db, project)
            await db.commit()
            return {"success": True, "message": f"Project '{project.name}' deleted successfully"}
        except Exception as e:
            await db.rollback()
            return {"success": False, "message": str(e)}

    @staticmethod
    async def get_all_projects(db: AsyncSession):
        all_projects = await GetProjects._get_all(db)
        serialized_projects = [
            {"id": p.id, "name": p.name, "description": p.description, "department_id": p.department_id}
            for p in all_projects if p is not None
        ]
        return {
            "success": True,
            "message": f"Found {len(all_projects)} projects",
            "data": serialized_projects
        }

    
    @staticmethod
    async def get_project_by_id(db: AsyncSession, project_id: int):
        project = await GetProjects._get_by_id(db, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        return {
            "success": True,
            "message": "Project retrieved successfully",
            "data": {"id": project.id, "name": project.name, "description": project.description, "department_id": project.department_id}
        }