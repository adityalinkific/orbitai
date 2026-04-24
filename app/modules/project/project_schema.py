from pydantic import BaseModel, Field
from datetime import date, datetime


class ProjectRequestSchema(BaseModel):
    name: str = Field(..., min_length=3)
    description: str | None = Field(None, max_length=255)
    department_id: int
    manager_id: int | None = None
    created_by: int | None = None
    
class ProjectUpdateSchema(BaseModel):
    name: str | None = Field(None, min_length=3)
    description: str | None = Field(None, max_length=255)
    department_id: int | None = None
    manager_id: int | None = None
    created_by: int | None = None
    

class ProjectResponseSchema(BaseModel):
    id: int
    name: str
    description: str | None
    department_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True