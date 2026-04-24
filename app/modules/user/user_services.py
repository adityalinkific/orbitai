from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.user.user_repository import UserRepository, GetDetail
from app.modules.user.user_schema import ChangePassword, UpdateUserDetailsRequest
from app.core.security import PasswordService
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
        """List all users with proper response format."""
        users = await UserServices._all_users(db)
        return {
            "status": "success",
            "message": f"Found {len(users)} users",
            "data": users
        }

    @staticmethod
    async def get_users(db: AsyncSession):
        """Alias for list_users to match config.yaml."""
        return await UserServices.list_users(db)

    @staticmethod
    async def update_user_email(db: AsyncSession, username: str, email: str):
        from app.core.resolvers.entity_resolver import EntityResolver
        user = await EntityResolver.resolve_user(db, username)

        if not user:
            return {"status": "error", "message": "User not found", "data": {}}

        try:
            user.email = email
            await db.commit()
            return {"status": "success", "message": f"Updated email for {user.name}", "data": {"id": user.id, "email": user.email}}
        except Exception as e:
            await db.rollback()
            return {"status": "error", "message": str(e), "data": {}}
    
    @staticmethod
    async def _change_password(data: ChangePassword, db: AsyncSession, current_user: User):
        if not PasswordService._verify(data.current_password, current_user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid current password"
            )
            
        hashed_password = PasswordService._hash(data.new_password)
        try:
            await UserRepository._update({"password": hashed_password}, current_user)
            await db.commit()
            return {"status": "success", "message": "Password changed successfully", "data": {"id": current_user.id}}
        except Exception:
            await db.rollback()
            raise
        
    @staticmethod
    async def _update_user(user_id: int, data: UpdateUserDetailsRequest, db: AsyncSession):
        user_detail = await GetDetails._get_details(db, User, user_id, "user")
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field is required for updating the task."
            )
        
        if data.department_id: 
            await RecordChecking._check(db, Department.id, data.department_id, "department")
        if data.role_id:
            await RecordChecking._check(db, Role.id, data.role_id, 'role')
        if data.reporting_manager_id:
            await RecordChecking._check(db, User.id, data.reporting_manager_id, 'reporting manager')
        
        if data.password:
            update_data.password = PasswordService._hash(data.password)
            
        try:
            result = await UserRepository._update(update_data, user_detail)
            await db.commit()
            await db.refresh(result)
            return {
                "status": "success",
                "message": "User updated successfully",
                "data": {"id": result.id, "name": result.name, "email": result.email}
            }
        except Exception as e:
            await db.rollback()
            return {"status": "error", "message": str(e), "data": {}}