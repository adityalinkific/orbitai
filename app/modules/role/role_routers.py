from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.schema import ApiResponse
from app.core.dependency import get_db, require_roles
from app.modules.role.role_controller import RoleController
from app.modules.role.role_schema import CreateRoleRequest, RoleResponse, RoleUpdateSchema

router = APIRouter(prefix= '/roles', tags= ['Roles'])

@router.post('/', response_model=ApiResponse[RoleResponse], summary= "Create a Role")
async def create_role(data: CreateRoleRequest, db: AsyncSession = Depends(get_db), current_user= Depends(require_roles("super_admin"))):
    return await RoleController.create_role(data, db, current_user)


@router.get('/role', summary= "Get All Roles")
async def get_role(db: AsyncSession = Depends(get_db)):
    return await RoleController.get_roles(db)


@router.get('/role-detail/{role_id}', response_model=ApiResponse[RoleResponse], summary= "Get Particular Role")
async def get_one_role(role_id: int, db: AsyncSession = Depends(get_db)):
    return await RoleController._get_perticular_role(role_id, db)


@router.put('/update-role/{role_id}', response_model= ApiResponse[None], summary= "Update Role")
async def update_role(role_id: int, data: RoleUpdateSchema, db: AsyncSession = Depends(get_db), _= Depends(require_roles('super_admin', 'admin'))):
    return await RoleController._update_role(role_id, data, db)


@router.delete('/delete-role/{role_id}', response_model= ApiResponse[None], summary= 'Delete Role')
async def delet_role(role_id: int, db: AsyncSession = Depends(get_db), _= Depends(require_roles('super_admin', 'admin'))):
    return await RoleController._delete_role(role_id, db)