from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists
from app.modules.project.project_model import Project
from app.modules.project.project_schema import ProjectUpdateSchema


class ProjectRepository:
    
    @staticmethod
    async def _create(db: AsyncSession, project: Project):
        db.add(project)
        return project
    
    
    @staticmethod
    async def _update(db: AsyncSession, update_data: dict, project: Project):
        for field, value in update_data.items():
            setattr(project, field, value)
        
        return project
    
    @staticmethod
    async def _delete(db: AsyncSession, project: Project):
        await db.delete(project)
        return 
    
    
class DetailsExist():

    @staticmethod
    async def _exists(db: AsyncSession, field, value) -> bool:
        stmt = select(exists().where(field == value))
        result = await db.execute(stmt)
        return result.scalar()
    
    
class GetProjects:
    
    @staticmethod
    async def _get_by_id(db: AsyncSession, project_id: int):
        stmt = select(Project).where(Project.id == project_id)
        result = await db.execute(stmt)
        return result.scalars().first()
    
    @staticmethod
    async def _get_all(db: AsyncSession):
        stmt = select(Project).order_by(Project.created_at.desc())
        result = await db.execute(stmt)
        all_projects = result.scalars().all()
        return all_projects

    @staticmethod
    async def _get_by_name(db: AsyncSession, name: str):
        stmt = select(Project).where(Project.name == name)
        result = await db.execute(stmt)
        return result.scalars().first()