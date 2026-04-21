from pydantic import BaseModel, field_validator
import re
from datetime import date

class ChangePassword(BaseModel):
    current_password: str
    new_password: str
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        errors = []
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", password):
            errors.append("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Password must contain at least one special character")
        if errors:
            # raise ValueError(" ".join(errors))
            raise ValueError(errors)
        return password
    
class UpdateUserDetailsRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    password: str | None = None
    role_id: int | None = None
    reporting_manager_id: int | None = None
    department_id: int | None = None
    is_active: bool | None = None
    joined_date: date | None = None