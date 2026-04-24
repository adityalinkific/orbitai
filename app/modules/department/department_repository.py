from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import exists, select, func
from app.modules.department.department_model import Department
from app.modules.auth.auth_model import User
from app.modules.project.project_model import Project
from app.core.base_repository import BaseRepository


class DepartmentRepository(BaseRepository):
    """Department repository with standard CRUD and custom aggregation queries."""
    
    def __init__(self):
        super().__init__(Department)
    
    @staticmethod
    async def get_all_with_stats(db: AsyncSession):
        """Get all departments with user and project counts."""
        user_count_subq = (
            select(
                User.department_id,
                func.count(User.id).label("total_members")
            )
            .group_by(User.department_id)
            .subquery()
        )

        project_count_subq = (
            select(
                Project.department_id,
                func.count(Project.id).label("total_projects")
            )
            .group_by(Project.department_id)
            .subquery()
        )
        
        stmt = (
            select(
                Department,
                User.name.label("head_name"),
                func.coalesce(user_count_subq.c.total_members, 0).label("total_members"),
                func.coalesce(project_count_subq.c.total_projects, 0).label("total_projects"),
            )
            .outerjoin(User, Department.department_head_id == User.id)
            .outerjoin(user_count_subq, Department.id == user_count_subq.c.department_id)
            .outerjoin(project_count_subq, Department.id == project_count_subq.c.department_id)
            .order_by(Department.id.desc())
        )
        result = await db.execute(stmt)
        return result.all()
    
    @staticmethod
    async def get_with_stats_by_id(db: AsyncSession, department_id: int):
        """Get department by ID with user and project counts."""
        user_count_subq = (
            select(
                User.department_id,
                func.count(User.id).label("total_members")
            )
            .group_by(User.department_id)
            .subquery()
        )

        project_count_subq = (
            select(
                Project.department_id,
                func.count(Project.id).label("total_projects")
            )
            .group_by(Project.department_id)
            .subquery()
        )

        stmt = (
            select(
                Department,
                User.name.label("head_name"),
                func.coalesce(user_count_subq.c.total_members, 0).label("total_members"),
                func.coalesce(project_count_subq.c.total_projects, 0).label("total_associated_projects"),
            )
            .outerjoin(User, Department.department_head_id == User.id)
            .outerjoin(user_count_subq, Department.id == user_count_subq.c.department_id)
            .outerjoin(project_count_subq, Department.id == project_count_subq.c.department_id)
            .where(Department.id == department_id)
        )

        result = await db.execute(stmt)
        return result.first()


# Legacy compatibility - keep for gradual migration
class RecordExists():

    @staticmethod
    async def _check(db: AsyncSession, *conditions) -> bool:
        stmt = select(exists().where(*conditions))
        result = await db.execute(stmt)
        return result.scalar()


class GetDetail:
    @staticmethod
    async def _get_all(db: AsyncSession, model, *conditions):
        repo = DepartmentRepository()
        return await repo.get_all_with_stats(db)
    
    @staticmethod
    async def _get_department_by_id(db: AsyncSession, department_id: int):
        return await DepartmentRepository.get_with_stats_by_id(db, department_id)
    
    @staticmethod
    async def _get_one(db: AsyncSession, model, *conditions):
        stmt = select(model).where(*conditions)
        result = await db.execute(stmt)
        return result.scalars().first()