from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.meeting.meeting_model import Meeting
from app.modules.meeting.meeting_schema import MeetingCreateRequest, MeetingUpdateRequest
from app.modules.meeting.meeting_repository import MeetingRepository, GetMeetingRecord, DeleteMeeting
from app.modules.project.project_model import Project
from app.modules.auth.auth_repository import GetRecord

class MeetingService:
    @staticmethod
    async def create_meeting(data: MeetingCreateRequest, db: AsyncSession, current_user):
        # Verify project exists if project_id is provided
        if data.project_id:
            project = await GetRecord._get_one(db, Project, Project.id == data.project_id)
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail='Invalid project selected'
                )

        meeting = Meeting(
            title=data.title,
            description=data.description,
            start_time=data.start_time,
            end_time=data.end_time,
            project_id=data.project_id,
            status=data.status,
            organizer_id=current_user.id
        )

        try:
            await MeetingRepository._create_meeting(db, meeting)
            await db.commit()
            await db.refresh(meeting)
            return meeting
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def get_all_meetings(db: AsyncSession):
        return await GetMeetingRecord._get_all(db)

    @staticmethod
    async def get_meeting_by_id(db: AsyncSession, id: int):
        meeting = await GetMeetingRecord._get_one(db, Meeting, Meeting.id == id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found"
            )
        return meeting

    @staticmethod
    async def update_meeting(db: AsyncSession, id: int, data: MeetingUpdateRequest, current_user):
        meeting = await GetMeetingRecord._get_one(db, Meeting, Meeting.id == id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found"
            )

        # Basic permission check: only organizer or super_admin can update
        if meeting.organizer_id != current_user.id and current_user.role.role.lower() != 'super_admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this meeting"
            )

        # Validate project if being updated
        if data.project_id is not None and data.project_id != meeting.project_id:
            project = await GetRecord._get_one(db, Project, Project.id == data.project_id)
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail='Invalid project selected'
                )

        # Update fields dynamically
        update_data = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
        if update_data:
            try:
                await MeetingRepository._update(update_data, meeting)
                await db.commit()
                await db.refresh(meeting)
            except Exception:
                await db.rollback()
                raise
        return meeting

    @staticmethod
    async def delete_meeting(db: AsyncSession, id: int, current_user):
        meeting = await GetMeetingRecord._get_one(db, Meeting, Meeting.id == id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found"
            )

        # Basic permission check
        if meeting.organizer_id != current_user.id and current_user.role.role.lower() != 'super_admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this meeting"
            )

        try:
            await DeleteMeeting._delete_meeting(db, meeting)
            await db.commit()
            return
        except Exception:
            await db.rollback()
            raise
