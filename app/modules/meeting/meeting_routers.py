from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.schema import ApiResponse
from app.core.dependency import get_db, get_current_user
from app.modules.meeting.meeting_controller import MeetingController
from app.modules.meeting.meeting_schema import MeetingCreateRequest, MeetingUpdateRequest, AddAttendeesRequest
from typing import Any

router = APIRouter(prefix='/meetings', tags=['Meetings'])
attendee_router = APIRouter(prefix='/meetings', tags=['Meeting Attendees'])

@router.post('/', response_model=ApiResponse[Any], summary="Create a new Meeting")
async def create_meeting(data: MeetingCreateRequest, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    return await MeetingController._create_meeting(data, db, current_user)

@router.get('/', response_model=ApiResponse[Any], summary="Get all Meetings")
async def get_all_meetings(db: AsyncSession = Depends(get_db), _ = Depends(get_current_user)):
    return await MeetingController._get_all_meetings(db)

@router.get('/{id}', response_model=ApiResponse[Any], summary="Get Meeting by ID")
async def get_meeting_by_id(id: int, db: AsyncSession = Depends(get_db), _ = Depends(get_current_user)):
    return await MeetingController._get_meeting_by_id(id, db)

@router.put('/{id}', response_model=ApiResponse[Any], summary="Update Meeting details")
async def update_meeting(id: int, data: MeetingUpdateRequest, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    return await MeetingController._update_meeting(id, data, db, current_user)

@router.delete('/{id}', response_model=ApiResponse[Any], summary="Delete a Meeting")
async def delete_meeting(id: int, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    return await MeetingController._delete_meeting(id, db, current_user)

@attendee_router.post('/{id}/attendees', response_model=ApiResponse[Any], summary="Add Attendees to a Meeting")
async def add_attendees(id: int, data: AddAttendeesRequest, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    return await MeetingController._add_attendees(id, data, db, current_user)

@attendee_router.delete('/{id}/attendees/{user_id}', response_model=ApiResponse[Any], summary="Remove an Attendee from a Meeting")
async def remove_attendee(id: int, user_id: int, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    return await MeetingController._remove_attendee(id, user_id, db, current_user)

