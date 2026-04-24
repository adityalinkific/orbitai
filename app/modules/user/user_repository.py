from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.modules.auth.auth_model import User
from app.core.base_repository import BaseRepository


class UserRepository(BaseRepository):
    """User repository with standard CRUD operations."""
    
    def __init__(self):
        super().__init__(User)
    
    @staticmethod
    async def get_all_with_relations(db: AsyncSession):
        """Get all users with role and department relations."""
        stmt = (select(User)
            .order_by(User.id.desc())
            .options(
                selectinload(User.role),
                selectinload(User.department)
            )
        )
        result = await db.execute(stmt)
        users = result.scalars().all()
        return users


# Legacy compatibility - keep for gradual migration
class GetDetail:
    @staticmethod
    async def _all_data(db):
        repo = UserRepository()
        return await repo.get_all_with_relations(db)
    
    @staticmethod
    async def _get_one(db: AsyncSession, model, *conditions):
        stmt = select(model).where(*conditions)
        result = await db.execute(stmt)
        return result.scalars().first()