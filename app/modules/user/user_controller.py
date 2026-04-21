from app.modules.user.user_services import UserServices
from app.core.schema import Response

class UserController:
    
    @staticmethod
    async def _all_user(db):
        users = await UserServices._all_users(db)
        # The service already processes the data, just return it
        return await Response._success_response("User's data fetched successfully!", users)
        
    
    async def _change_password(data, db, current_user):
        await UserServices._change_password(data, db, current_user)
        return await Response._success_response('Password changed successfully!')
        
    async def _update_user(user_id, data, db):
        user = await UserServices._update_user(user_id, data, db)
        data = {
            "id": user.id,
            "emp_id": user.emp_id,
            "name": user.name,
            "email": user.email,
            "role_id": user.role_id,
            "reporting_manager_id": user.reporting_manager_id,
            "department_id": user.department_id,
            "is_active": user.is_active,
            "logged_in": user.logged_in,
            "joined_date": user.joined_date,
            "role": {
                "id": user.role.id,
                "role": user.role.role,
                "description": user.role.description,
            },
            "department": {
                "id": user.department.id,
                "department": user.department.name,
                "description": user.department.description,
            },
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
        return await Response._success_response("User's details updated successfully!", data)
        