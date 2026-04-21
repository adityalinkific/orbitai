from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.schema import ApiResponse
from app.core.dependency import get_db, require_roles, get_current_user

from app.modules.user.user_controller import UserController
from app.modules.auth.auth_model import User
from app.modules.auth.auth_schema import UserResponse
from app.modules.user.user_schema import ChangePassword, UpdateUserDetailsRequest


user_router = APIRouter(prefix= '/user', tags= ['User'])

@user_router.get('/all-users', summary= "All Users Details")
async def all_users(db: AsyncSession = Depends(get_db), current_user= Depends(require_roles('super_admin', 'admin'))):
    return await UserController._all_user(db)


@user_router.patch('/change-password', response_model= ApiResponse[None], summary= "Change Your Password")
async def change_password(data: ChangePassword, db: AsyncSession = Depends(get_db), current_user= Depends(get_current_user)):
    return await UserController._change_password(data, db, current_user)

@user_router.put('/update-user/{user_id}', response_model= ApiResponse[UserResponse], summary= "Update User's Details")
async def update_user(user_id: int, data: UpdateUserDetailsRequest, db: AsyncSession = Depends(get_db), _= Depends(require_roles('super_admin', 'admin'))):
    return await UserController._update_user(user_id, data, db)