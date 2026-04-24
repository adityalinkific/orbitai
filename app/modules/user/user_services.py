from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.user.user_repository import UserRepository, GetDetail
from app.modules.user.user_schema import ChangePassword, UpdateUserDetailsRequest
from app.core.security import PasswordService
from app.core.response import success, error, not_found
from app.modules.auth.auth_model import User, Role
from app.modules.auth.auth_services import RecordChecking, GetDetails
from app.modules.department.department_model import Department

class UserServices:
    
    @staticmethod
    async def _all_users(db: AsyncSession):
        users = await GetDetail._all_data(db)
        return [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "role": u.role.role if u.role else "N/A"
            }
            for u in users
        ]

    @staticmethod
    async def list_users(db: AsyncSession):
        """List all users with standard response format."""
        users = await UserServices._all_users(db)
        return success(message=f"Found {len(users)} users", data=users)

    @staticmethod
    async def get_users(db: AsyncSession):
        """Alias for list_users to match config.yaml."""
        return await UserServices.list_users(db)

    @staticmethod
    async def update_user_email(db: AsyncSession, username: str, email: str):
        """Update user email with standard response format."""
        from app.core.resolvers.entity_resolver import EntityResolver
        user = await EntityResolver.resolve_user(db, username)

        if not user:
            return not_found(resource="User", identifier=username)

        try:
            user.email = email
            await db.commit()
            return success(
                message=f"Updated email for {user.name}",
                data={"id": user.id, "email": user.email}
            )
        except Exception as e:
            await db.rollback()
            return error(message=str(e), data={})
    
    @staticmethod
    async def _change_password(data: ChangePassword, db: AsyncSession, current_user: User):
        """Change password with standard response format."""
        if not PasswordService._verify(data.current_password, current_user.password):
            return error(message="Invalid current password", data={})
            
        hashed_password = PasswordService._hash(data.new_password)
        try:
            repo = UserRepository()
            await repo.update_instance(db, current_user, {"password": hashed_password})
            await db.commit()
            return success(message="Password changed successfully", data={"id": current_user.id})
        except Exception as e:
            await db.rollback()
            return error(message=str(e), data={})
        
    @staticmethod
    async def _update_user(user_id: int, data: UpdateUserDetailsRequest, db: AsyncSession):
        """Update user with standard response format."""
        user_detail = await GetDetails._get_details(db, User, user_id, "user")
        if not user_detail:
            return not_found(resource="User", identifier=user_id)
        
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return error(message="At least one field is required for updating the user.", data={})
        
        if data.department_id: 
            await RecordChecking._check(db, Department.id, data.department_id, "department")
        if data.role_id:
            await RecordChecking._check(db, Role.id, data.role_id, 'role')
        if data.reporting_manager_id:
            await RecordChecking._check(db, User.id, data.reporting_manager_id, 'reporting manager')
        
        if data.password:
            update_data.password = PasswordService._hash(data.password)
            
        try:
            repo = UserRepository()
            result = await repo.update_instance(db, user_detail, update_data)
            await db.commit()
            await db.refresh(result)
            return success(
                message="User updated successfully",
                data={"id": result.id, "name": result.name, "email": result.email}
            )
        except Exception as e:
            await db.rollback()
            return error(message=str(e), data={})