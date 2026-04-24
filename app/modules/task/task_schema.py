from pydantic import BaseModel, Field
from datetime import date, datetime
from enum import Enum


class TaskTypeEnum(str, Enum):
    daily = "daily"
    weekly = "weekly"


class TaskStatusEnum(str, Enum):
    assigned = "assigned"
    in_progress = "in_progress"
    submitted = "submitted"
    reviewed = "reviewed"
    
class PriorityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class TaskRequestSchema(BaseModel):
    title: str = Field(..., min_length=3)
    description: str | None = Field(None, max_length=255)
    project_id: int | None = None
    department_id: int | None = None
    task_type: TaskTypeEnum = TaskTypeEnum.daily
    priority: PriorityEnum = PriorityEnum.high
    due_date: date = Field(default_factory=lambda: datetime.now().date())
    manager_id: int | None = None

class TaskUpdateSchema(BaseModel):
    title: str | None = Field(None, min_length=3)
    description: str | None = Field(None, max_length=255)
    project_id: int | None = None
    department_id: int | None = None
    task_type: TaskTypeEnum | None = None
    priority: PriorityEnum | None = None
    due_date: date | None = None
    manager_id: int | None = None


class TaskResponseSchema(BaseModel):
    id: int
    task_id: str
    title: str
    description: str | None
    project_id: int
    department_id: int
    task_type: TaskTypeEnum
    priority: PriorityEnum
    due_date: date
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Task Assignment Schemas

class TaskAssignRequestSchema(BaseModel):
    task_id: int
    user_id: int
    due_date: date = Field(default_factory=lambda: datetime.now().date())
    
class AssignTaskResponseSchema(BaseModel):
    id: int
    task_id: int
    user_id: int

class TaskAssignUpdateSchema(BaseModel):
    task_id: int | None = None
    user_id: int | None = None
    due_date: date | None = None
    
class TaskAssignResponseSchema(BaseModel):
    id: int
    task_id: int
    user_id: int
    assigned_at: datetime
    assigned_by: int | None
    due_date: date
    status: TaskStatusEnum
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskStatusUpdateSchema(BaseModel):
    status: TaskStatusEnum

class TaskSubmitSchema(BaseModel):
    assign_task_id: int
    submission_text: str | None = None
    
class UploadTaskDocumentSchema(BaseModel):
    assign_task_id: int
    document_url: str | None = None


class ReportSubmitSchema(BaseModel):
    task_id: int
    content: str
    link_url: str | None = None


class ReportResponseSchema(BaseModel):
    task_id: str
    user_id: str
    content: str
    submitted_at: datetime


class ReportReviewSchema(BaseModel):
    reviewer_comment: str



VALID_TRANSITIONS = {
    TaskStatusEnum.assigned: [TaskStatusEnum.in_progress],
    TaskStatusEnum.in_progress: [TaskStatusEnum.submitted],
    TaskStatusEnum.submitted: [],
    TaskStatusEnum.reviewed: []
}