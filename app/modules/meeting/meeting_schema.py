from pydantic import BaseModel, Field, EmailStr
from datetime import date, datetime
from typing import Optional, List


class MeetingBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    meeting_date: date
    start_time: datetime
    end_time: Optional[datetime] = None
    project_id: Optional[int] = None
    status: str = "Scheduled"
    meeting_link: Optional[str] = None


class MeetingCreateRequest(MeetingBase):
    organizer_id: Optional[int] = None  # Admin can select a different organizer; defaults to current_user
    attendee_user_ids: Optional[List[int]] = []
    attendee_emails: Optional[List[EmailStr]] = []  # for sending invite emails
    generate_meeting_link: bool = False  # if True, backend auto-generates a meet link


class MeetingUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    meeting_date: Optional[date] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    project_id: Optional[int] = None
    status: Optional[str] = None
    meeting_link: Optional[str] = None


class AddAttendeesRequest(BaseModel):
    user_ids: List[int]


class AttendeeUserResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True


class MeetingAttendeeResponse(BaseModel):
    id: int
    user_id: int
    status: str
    user: AttendeeUserResponse

    class Config:
        from_attributes = True


class OrganizerResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True


class MeetingResponse(MeetingBase):
    id: int
    organizer_id: int
    organizer: OrganizerResponse
    attendees: List[MeetingAttendeeResponse] = []
    meeting_link: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
