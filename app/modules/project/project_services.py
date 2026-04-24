from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.modules.department.department_model import Department
from app.modules.project.project_model import Project
from app.modules.project.project_schema import ProjectRequestSchema, ProjectUpdateSchema
from app.modules.project.project_repository import ProjectRepository, DetailsExist, GetProjects
from app.core.response import success, error, not_found, conflict

class ProjectService:

    @staticmethod
    async def create_project(db: AsyncSession, data: ProjectRequestSchema, current_user):
        """Create a new project with standard response format."""
        try:
            payload = data.model_dump() if hasattr(data, 'model_dump') else dict(data)
        except Exception:
            payload = data or {}

        name_val = payload.get('name')
        dept_id = payload.get('department_id') or getattr(current_user, 'department_id', None)
        desc_val = payload.get('description')

        if not name_val:
            return error(message="Project name is required", data={})
        
        project_exists = await DetailsExist._exists(db, Project.name, name_val)
        if project_exists:
            existing = await GetProjects._get_by_name(db, name_val)
            return success(
                message="Project already exists",
                data={"id": existing.id, "name": existing.name}
            )
        
        if dept_id and not await DetailsExist._exists(db, Department.id, dept_id):
            return error(message="Invalid department selected", data={})
        
        project_data = Project(
            name=name_val,
            description=desc_val,
            department_id=dept_id,
        )
        try:
            repo = ProjectRepository()
            project = await repo.create(db, project_data)
            return success(
                message="Project created successfully",
                data={"id": project.id, "name": project.name}
            )
        except Exception as e:
            await db.rollback()
            return error(message=str(e), data={})

    @staticmethod
    async def update_project(db: AsyncSession, project_id: int, data):
        """Update project with standard response format."""
        try:
            update_data = data.model_dump(exclude_unset=True) if hasattr(data, 'model_dump') else dict(data)
        except Exception:
            update_data = data or {}
            
        if not update_data:
            return error(message="At least one field is required for updating the project.", data={})
            
        dept_id = update_data.get('department_id') if isinstance(data, dict) else getattr(data, 'department_id', None)
        if dept_id is not None and not await DetailsExist._exists(db, Department.id, dept_id):
            return error(message="Invalid department selected", data={})

        project = await GetProjects._get_by_id(db, project_id)
        if not project:
            return not_found(resource="Project", identifier=project_id)
            
        try:
            repo = ProjectRepository()
            project = await repo.update_instance(db, project, update_data)
            return success(
                message="Project updated successfully",
                data={"id": project.id, "name": project.name}
            )
        except Exception as e:
            await db.rollback()
            return error(message=str(e), data={})

    @staticmethod
    async def delete_project(db: AsyncSession, project_id: int):
        """Delete project with standard response format."""
        project = await GetProjects._get_by_id(db, project_id)
        if not project:
            return not_found(resource="Project", identifier=project_id)

        try:
            repo = ProjectRepository()
            await repo.delete_instance(db, project)
            return success(message=f"Project '{project.name}' deleted successfully", data={})
        except Exception as e:
            await db.rollback()
            return error(message=str(e), data={})

    @staticmethod
    async def get_all_projects(db: AsyncSession):
        """Get all projects with standard response format."""
        all_projects = await GetProjects._get_all(db)
        serialized_projects = [
            {
                "id": p.id, 
                "name": p.name, 
                "description": p.description, 
                "department_id": p.department_id,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None
            }
            for p in all_projects if p is not None
        ]
        return success(message=f"Found {len(all_projects)} projects", data=serialized_projects)
    
    @staticmethod
    async def get_project_by_id(db: AsyncSession, project_id: int):
        """Get project by ID with standard response format."""
        project = await GetProjects._get_by_id(db, project_id)
        if not project:
            return not_found(resource="Project", identifier=project_id)

        return success(
            message="Project retrieved successfully",
            data={
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "department_id": project.department_id,
                "status": project.status.value if project.status else None
            }
        )

    @staticmethod
    async def start_project(db: AsyncSession, project_id: int):
        """Start a project by changing its status to active."""
        project = await GetProjects._get_by_id(db, project_id)
        if not project:
            return not_found(resource="Project", identifier=project_id)

        try:
            from app.modules.project.project_model import ProjectStatusEnum
            project.status = ProjectStatusEnum.active
            await db.commit()
            await db.refresh(project)
            return success(
                message=f"Project '{project.name}' started successfully",
                data={"id": project.id, "name": project.name, "status": project.status.value}
            )
        except Exception as e:
            await db.rollback()
            return error(message=str(e), data={})