from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import AsyncSessionLocal
from app.modules.auth.auth_model import User
from jose import JWTError, jwt
from app.core.security import TokenService
from app.core.schema import Response

security = HTTPBearer()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(request: Request, token: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)):
    try:
        
        payload = TokenService._decode_access_token(token.credentials)

        email: str | None = payload.get("sub")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail= await Response._error_response("Invalid token")
            )

        stmt = (select(User)
            .options(
                selectinload(User.role),
                selectinload(User.department)
            )
            .where(User.email == email)
        )
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if not user.logged_in:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail = await Response._error_response("You are logged out. Login again.")
            )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail= await Response._error_response("Unauthenticated")
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail= await Response._error_response("You are blocked. Please contact admin.")
            )

        request.state.user = user
        return user

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail= "Invalid or expired token",
        )


def require_roles(*allowed_roles: str):

    async def role_checker(current_user: User = Depends(get_current_user)):
        user_role = current_user.role.role

        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail= await Response._error_response("You do not have permission to perform this action.")
            )

        return current_user

    return role_checker

