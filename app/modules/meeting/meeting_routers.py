from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.schema import ApiResponse
from app.core.dependency import get_db, get_current_user, require_roles
from app.modules.meeting.meeting_controller import MeetingController
from app.modules.meeting.meeting_schema import MeetingCreateRequest, MeetingUpdateRequest
from typing import List, Any

router = APIRouter(prefix='/meetings', tags=['Meetings'])

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
