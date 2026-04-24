from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import exists, select
from app.modules.auth.auth_model import Role
from app.core.base_repository import BaseRepository


class RoleRepository(BaseRepository):
    """Role repository with standard CRUD operations."""
    
    def __init__(self):
        super().__init__(Role)


# Legacy compatibility - keep for gradual migration
class RecordExists:

    @staticmethod
    async def _check(db: AsyncSession, *conditions) -> bool:
        stmt = select(exists().where(*conditions))
        result = await db.execute(stmt)
        return result.scalar()


class GetDetail:
    @staticmethod
    async def _get_all(db: AsyncSession, model, *conditions):
        stmt = select(model).order_by(model.id.desc())
        if conditions:
            stmt = stmt.where(*conditions)
        result = await db.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def _get_one(db: AsyncSession, model, *conditions):
        stmt = select(model).where(*conditions)
        result = await db.execute(stmt)
        return result.scalars().first()