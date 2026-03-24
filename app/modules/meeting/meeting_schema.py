from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional, List

class MeetingBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    project_id: Optional[int] = None
    status: str = "Scheduled"

class MeetingCreateRequest(MeetingBase):
    # organizer_id will be derived from the logged-in current_user
    attendee_emails: Optional[List[EmailStr]] = []

class MeetingUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    project_id: Optional[int] = None
    status: Optional[str] = None

class MeetingResponse(MeetingBase):
    id: int
    organizer_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
