from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.auth.auth_model import Role
from app.modules.role.role_schema import CreateRoleRequest
from app.modules.role.role_services import RoleService
from app.core.schema import Response

class RoleController:

    @staticmethod
    async def create_role(data: CreateRoleRequest, db: AsyncSession, current_user):

        role = await RoleService._create_role(data, db, current_user)
        data = {
            "id": role.id,
            "role": role.role,
            "description": role.description,
            "created_at": role.created_at,
            "updated_at": role.updated_at
        }
        return await Response._success_response("Role created successfully", data)

    @staticmethod
    async def get_roles(db: AsyncSession):
        response = await RoleService._get_roles(db)
        # Extract the data list from the response
        roles = response.get("data", [])
        data = []
        for role in roles:
            if hasattr(role, 'id'):
                # It's a Role object
                data.append({
                    "id": role.id,
                    "role": role.role,
                    "description": role.description,
                    "created_at": role.created_at,
                    "updated_at": role.updated_at
                })
            else:
                # It's a dict (fallback)
                data.append({
                    "id": role.get("id"),
                    "role": role.get("role"),
                    "description": None,
                    "created_at": None,
                    "updated_at": None
                })
        return await Response._success_response("Roles fetched successfully", data)



    @staticmethod
    async def _get_perticular_role(role_id, db):
        role = await RoleService._get_role(role_id, db)
        data =  {
            "id": role["data"]["id"],
            "role": role["data"]["role"],
            "description": role["data"]["description"],
            "created_at": role["data"]["created_at"],
            "updated_at": role["data"]["updated_at"]
        }
        return await Response._success_response("Roles fetched successfully", data)
        
    
    @staticmethod
    async def _update_role(role_id, data, db):
        await RoleService._update(role_id, data, db)
        return await Response._success_response("Role updated successfully")
        
    
    @staticmethod
    async def _delete_role(role_id, db):
        result = await RoleService._delete(role_id, db)
        return await Response._success_response(result["message"])