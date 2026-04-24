from pydantic import BaseModel, EmailStr
from datetime import date, datetime

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role_id: int
    reporting_manager_id: int | None = None
    department_id: int | None = None
    is_active: bool
    joined_date: date
    
class RegisterResponse(BaseModel):
    id: int
    emp_id: str
    name: str
    email: str
    role_id: int
    department_id: int
    reporting_manager_id: int | None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    
class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict | None = None
    
    
class RoleResponse(BaseModel):
    id: int
    role: str
    description: str

    class Config:
        from_attributes = True
    
class DepartmentResponse(BaseModel):
    id: int
    department: str
    description: str

    class Config:
        from_attributes = True
        
        
class UserResponse(BaseModel):
    id: int
    emp_id: str
    name: str
    email: EmailStr
    role_id: int
    role: RoleResponse
    reporting_manager_id: int | None
    department_id: int
    department: DepartmentResponse
    is_active: bool
    logged_in: bool
    joined_date: datetime
    created_at: datetime
    updated_at: datetime
    
    
class UserWithRoleResponse(UserResponse):
    role: RoleResponse

class UserWithDepartmentResponse(UserResponse):
    department: DepartmentResponse