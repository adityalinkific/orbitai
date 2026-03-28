from app.modules.auth.auth_model import User
from app.modules.auth.auth_services import AuthService
from app.core.schema import Response


class AuthController:

    @staticmethod
    async def _register(data, db, current_user):
        user = await AuthService.register_user(data, db, current_user)
        print(user)
        data = {
            "id": user.id,
            "emp_id": user.emp_id,
            "name": user.name,
            "email": user.email,
            "role_id": user.role_id,
            "department_id": user.department_id,
            "reporting_manager_id": user.reporting_manager_id
        }
        return await Response._success_response("User registered successfully", data)
        
        
    @staticmethod
    async def _login(data, db):
        token = await AuthService.login_user(data, db)
        data = {
            "access_token": token,
            "token_type": "Bearer"
        }
        return await Response._success_response("Login successful", data)
        
    
    @staticmethod
    async def _get_authenticated_user(current_user):
        user = await AuthService.get_user_details(current_user)
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
                "id": current_user.role.id,
                "role": current_user.role.role,
                "description": current_user.role.description,
            },
            "department": {
                "id": current_user.department.id,
                "department": current_user.department.name,
                "description": current_user.department.description,
            },
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
        
        return await Response._success_response("Authenticated user's details fetched successfully", data)


    @staticmethod
    async def _logout(db, current_user):
        await AuthService.logout_user(db, current_user)

        return await Response._success_response("Logout successfully")

    @staticmethod
    async def _delete_user_account(id: int, db):
        await AuthService.delete_user(id, db)

        return await Response._success_response("User account deleted successfully")