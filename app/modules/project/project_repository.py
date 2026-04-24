from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists
from app.modules.project.project_model import Project
from app.core.base_repository import BaseRepository


class ProjectRepository(BaseRepository):
    """Project repository with standard CRUD operations."""
    
    def __init__(self):
        super().__init__(Project)
    
    @staticmethod
    async def get_by_name(db: AsyncSession, name: str):
        """Get project by name."""
        stmt = select(Project).where(Project.name == name)
        result = await db.execute(stmt)
        return result.scalars().first()


# Legacy compatibility - keep for gradual migration
class DetailsExist:

    @staticmethod
    async def _exists(db: AsyncSession, field, value) -> bool:
        stmt = select(exists().where(field == value))
        result = await db.execute(stmt)
        return result.scalar()
    
class GetProjects:
    
    @staticmethod
    async def _get_by_id(db: AsyncSession, project_id: int):
        repo = ProjectRepository()
        return await repo.get_by_id(db, project_id)
    
    @staticmethod
    async def _get_all(db: AsyncSession):
        repo = ProjectRepository()
        return await repo.get_all(db, eager_load=None)

    @staticmethod
    async def _get_by_name(db: AsyncSession, name: str):
        return await ProjectRepository.get_by_name(db, name)