from app.modules.meeting.meeting_services import MeetingService
from app.core.schema import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.meeting.meeting_schema import MeetingCreateRequest, MeetingUpdateRequest

class MeetingController:

    @staticmethod
    async def _create_meeting(data: MeetingCreateRequest, db: AsyncSession, current_user):
        meeting = await MeetingService.create_meeting(data, db, current_user)
        response_data = {
            "id": meeting.id,
            "title": meeting.title,
            "description": meeting.description,
            "start_time": meeting.start_time,
            "end_time": meeting.end_time,
            "status": meeting.status,
            "organizer_id": meeting.organizer_id,
            "project_id": meeting.project_id,
            "created_at": meeting.created_at,
            "updated_at": meeting.updated_at
        }
        return await Response._success_response("Meeting created successfully", response_data)

    @staticmethod
    async def _get_all_meetings(db: AsyncSession):
        meetings = await MeetingService.get_all_meetings(db)
        
        # Simple serialization
        response_data = []
        for meeting in meetings:
            response_data.append({
                "id": meeting.id,
                "title": meeting.title,
                "description": meeting.description,
                "start_time": meeting.start_time,
                "end_time": meeting.end_time,
                "status": meeting.status,
                "organizer_id": meeting.organizer_id,
                "project_id": meeting.project_id,
                "created_at": meeting.created_at,
                "updated_at": meeting.updated_at
            })
            
        return await Response._success_response("Meetings fetched successfully", response_data)

    @staticmethod
    async def _get_meeting_by_id(id: int, db: AsyncSession):
        meeting = await MeetingService.get_meeting_by_id(db, id)
        response_data = {
            "id": meeting.id,
            "title": meeting.title,
            "description": meeting.description,
            "start_time": meeting.start_time,
            "end_time": meeting.end_time,
            "status": meeting.status,
            "organizer_id": meeting.organizer_id,
            "project_id": meeting.project_id,
            "created_at": meeting.created_at,
            "updated_at": meeting.updated_at
        }
        return await Response._success_response("Meeting details fetched successfully", response_data)

    @staticmethod
    async def _update_meeting(id: int, data: MeetingUpdateRequest, db: AsyncSession, current_user):
        meeting = await MeetingService.update_meeting(db, id, data, current_user)
        response_data = {
            "id": meeting.id,
            "title": meeting.title,
            "description": meeting.description,
            "start_time": meeting.start_time,
            "end_time": meeting.end_time,
            "status": meeting.status,
            "organizer_id": meeting.organizer_id,
            "project_id": meeting.project_id,
            "created_at": meeting.created_at,
            "updated_at": meeting.updated_at
        }
        return await Response._success_response("Meeting updated successfully", response_data)

    @staticmethod
    async def _delete_meeting(id: int, db: AsyncSession, current_user):
        await MeetingService.delete_meeting(db, id, current_user)
        return await Response._success_response("Meeting deleted successfully")
