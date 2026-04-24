from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.auth.auth_repository import AuthRepository, RecordExists, GetRecord, DeleteUser
from app.modules.auth.auth_model import User, Role
from app.modules.department.department_model import Department
from app.core.security import PasswordService, TokenService
from app.core.response import success, error, conflict
from app.modules.auth.auth_schema import RegisterRequest, LoginRequest
import uuid


class AuthService:

    @staticmethod
    async def register_user(data: RegisterRequest, db: AsyncSession, current_user):
        """Register a new user with standard response format."""
        try:
            # If user already exists, return existing user info (idempotent create)
            if await RecordExists._check(db, User.email == data.email):
                existing_user = await GetRecord._get_one(db, User, User.email == data.email)
                if existing_user:
                    return success(
                        message="User already exists. Returning existing user.",
                        data={
                            "id": existing_user.id, 
                            "name": existing_user.name, 
                            "emp_id": existing_user.emp_id,
                            "email": existing_user.email,
                            "role_id": existing_user.role_id,
                            "department_id": existing_user.department_id,
                            "reporting_manager_id": existing_user.reporting_manager_id
                        }
                    )

            role = await GetRecord._get_one(db, Role, Role.id == data.role_id)

            if not role:
                return error(message="Invalid role selected", data={})
                
            if role.role.lower() == 'super_admin':
                return error(message="Cannot assign Super Admin role", data={})
                
            if data.reporting_manager_id:
                reporting_manager = await GetRecord._get_one(db, User, User.id == data.reporting_manager_id)
                if not reporting_manager:
                    return error(message="Invalid reporting manager selected", data={})
                if reporting_manager.is_active is False:
                    return error(message="Reporting manager is blocked", data={})

            hashed_password = PasswordService._hash(data.password)

            user = User(
                emp_id=f"LF-{uuid.uuid4().hex[:8].upper()}",
                name=data.name,
                email=data.email,
                password=hashed_password,
                role_id=data.role_id,
                reporting_manager_id=data.reporting_manager_id,
                department_id=data.department_id,
                is_active=data.is_active,
                joined_date=data.joined_date,
            )

            repo = AuthRepository()
            await repo.create(db, user)
            await db.commit()
            await db.refresh(user)
            return success(
                message="User registered successfully",
                data={
                    "id": user.id, 
                    "name": user.name, 
                    "emp_id": user.emp_id,
                    "email": user.email,
                    "role_id": user.role_id,
                    "department_id": user.department_id,
                    "reporting_manager_id": user.reporting_manager_id
                }
            )

        except Exception as e:
            try:
                await db.rollback()
            except Exception:
                pass
            err_msg = str(e).lower()
            # Treat duplicate/unique constraint violations as idempotent success
            if "unique" in err_msg or "duplicate" in err_msg or "integrity" in err_msg or "already exists" in err_msg:
                return success(message="User already registered (idempotent).", data={})
            return error(message=f"Failed to register user: {str(e)}", data={})

    @staticmethod
    async def login_user(data: LoginRequest, db: AsyncSession):
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        stmt = select(User).options(selectinload(User.role)).where(User.email == data.email)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email"
            )

        # 1. MATERIALIZE DATA IMMEDIATELY (Prevent Lazy Load)
        role_name = user.role.role if user.role else "employee"
        user_id = user.id
        user_email = user.email
        user_name = user.name
        hashed_password = user.password
        is_active = user.is_active

        if not PasswordService._verify(data.password, hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password"
            )

        if not is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are blocked. Please contact admin."
            )

        try:
            token = TokenService._create_access_token({
                "sub": user_email,
                "id": user_id,
                "role": role_name,
            })

            user.logged_in = True
            await db.commit()

            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {"email": user_email, "name": user_name}
            }
        
        except Exception:
            await db.rollback()
            raise


    @staticmethod
    async def get_user_details(current_user):
        return current_user
    

    @staticmethod
    async def logout_user(db: AsyncSession, current_user: User):
        try:
            await AuthRepository._update({"logged_in" : False}, current_user)
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def delete_user(id: int, db: AsyncSession):
        user = await GetRecord._get_one(db, User, User.id == id)        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        try:
            await DeleteUser._delete_user(db, user)
            await db.commit()
            return
        
        except Exception:
            await db.rollback()
            raise
        

class RecordChecking:
    @staticmethod
    async def _check(db: AsyncSession, field, id: int, message: str):
        if not await RecordExists._check(db, field == id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail= f"Invalid {message} selected."
            )

class GetDetails:
    @staticmethod
    async def _get_details(db: AsyncSession, model, id: int, message: str):
        result = await GetRecord._get_one(db, model, model.id == id)
        if not result:
            raise HTTPException(
                status_code= status.HTTP_404_NOT_FOUND,
                detail= f"{message.upper()} not found."
            )
        return result