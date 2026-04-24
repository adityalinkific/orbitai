from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.modules.role.role_repository import RoleRepository, GetDetail, RecordExists
from app.modules.auth.auth_model import Role
from app.modules.role.role_schema import CreateRoleRequest, RoleUpdateSchema
from app.core.response import success, error, not_found, conflict


class RoleService:

    @staticmethod
    async def _create_role(data: CreateRoleRequest, db: AsyncSession, current_user):
        """Create a new role with standard response format."""
        if await RecordExists._check(db, Role.role == data.role):
            return conflict(message="Role already exists", data={})

        new_role = Role(
            role=data.role,
            description=data.description
        )
        try:
            repo = RoleRepository()
            new_role = await repo.create(db, new_role)
            return success(
                message="Role created successfully",
                data={"id": new_role.id, "role": new_role.role}
            )
        except Exception as e:
            await db.rollback()
            return error(message=str(e), data={})
            
    @staticmethod
    async def _get_roles(db: AsyncSession):
        """Get all roles with standard response format."""
        roles = await GetDetail._get_all(db, Role)
        data = []
        for r in roles:
            if hasattr(r, 'id'):
                data.append({
                    "id": r.id,
                    "role": r.role,
                    "description": r.description,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None
                })
            else:
                data.append({"id": None, "role": str(r)})
        return success(message=f"Found {len(roles)} roles", data=data)
    
    @staticmethod
    async def _get_role(role_id: int, db: AsyncSession):
        """Get role by ID with standard response format."""
        role_detail = await GetDetail._get_one(db, Role, Role.id == role_id)
        if not role_detail:
            return not_found(resource="Role", identifier=role_id)
        
        return success(
            message="Role retrieved successfully",
            data={
                "id": role_detail.id,
                "role": role_detail.role,
                "description": role_detail.description,
                "created_at": role_detail.created_at.isoformat() if role_detail.created_at else None,
                "updated_at": role_detail.updated_at.isoformat() if role_detail.updated_at else None
            }
        )
    
    @staticmethod
    async def _update(role_id: int, data: RoleUpdateSchema, db: AsyncSession):
        """Update role with standard response format."""
        role_detail = await GetDetail._get_one(db, Role, Role.id == role_id)
        
        if not role_detail:
            return not_found(resource="Role", identifier=role_id)
        
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return error(message="At least one field is required for updating the role.", data={})
        
        try:
            repo = RoleRepository()
            result = await repo.update_instance(db, role_detail, update_data)
            return success(
                message="Role updated successfully",
                data={"id": result.id, "role": result.role}
            )
        except Exception as e:
            await db.rollback()
            return error(message=str(e), data={})
    
    @staticmethod
    async def _delete(role_id: int, db: AsyncSession):
        """Delete role with standard response format."""
        from app.modules.auth.auth_model import User
        role_detail = await GetDetail._get_one(db, Role, Role.id == role_id)
        if not role_detail:
            return not_found(resource="Role", identifier=role_id)

        # Check if any users are assigned to this role
        users_with_role = await GetDetail._get_all(db, User, User.role_id == role_id)
        if users_with_role:
            return error(
                message=f"Cannot delete role '{role_detail.role}' because it is assigned to {len(users_with_role)} user(s). Please reassign or delete the users first.",
                data={}
            )

        try:
            repo = RoleRepository()
            await repo.delete_instance(db, role_detail)
            return success(message=f"Role '{role_detail.role}' deleted successfully", data={})
        except Exception as e:
            await db.rollback()
            return error(message=f"Cannot delete role: {str(e)}", data={})
