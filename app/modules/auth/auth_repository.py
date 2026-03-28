from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists
from sqlalchemy.orm import selectinload
from app.modules.auth.auth_model import User


class AuthRepository:
    @staticmethod
    async def _create_user(db: AsyncSession, user: User):
        db.add(user)
        return user
    
    @staticmethod
    async def _update(update_data: dict, instance: any):
        for field, value in update_data.items():
            setattr(instance, field, value)
        return instance
    
class GetRecord:
    @staticmethod
    async def _get_one(db: AsyncSession, model, *conditions):
        stmt = select(model).where(*conditions)
        result = await db.execute(stmt)
        return result.scalars().first()
    
    @staticmethod
    async def _get_all(db: AsyncSession):
        stmt = (
            select(User)
            .options(
                selectinload(User.role),
                selectinload(User.department)
            )
            .order_by(User.id.desc())
            # .where(User.email == email)
        )
        result = await db.execute(stmt)
        return result.scalars().first()
    
    
class RecordExists():
    @staticmethod
    async def _check(db: AsyncSession, *conditions) -> bool:
        stmt = select(exists().where(*conditions))
        result = await db.execute(stmt)
        return result.scalar()
    
class DeleteUser():
    @staticmethod
    async def _delete_user(db: AsyncSession, user):
        return await db.delete(user)

    

# class DetailsExist():
#     @staticmethod
#     async def exists(db: AsyncSession, field, value) -> bool:
#         stmt = select(exists().where(field == value))
#         result = await db.execute(stmt)
#         return result.scalar()

# class GetDetails():
#     @staticmethod
#     async def get_by_id(db: AsyncSession, model, field, value):
#         stmt = select(model).where(field == value)
#         result = await db.execute(stmt)
#         return result.scalars().first()