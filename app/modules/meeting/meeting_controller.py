from app.modules.meeting.meeting_services import MeetingService, MeetingAttendeeService
from app.core.schema import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.meeting.meeting_schema import MeetingCreateRequest, MeetingUpdateRequest, AddAttendeesRequest


def _serialize_meeting(meeting) -> dict:
    return {
        "id": meeting.id,
        "title": meeting.title,
        "description": meeting.description,
        "meeting_date": meeting.meeting_date,
        "start_time": meeting.start_time,
        "end_time": meeting.end_time,
        "status": meeting.status,
        "meeting_link": meeting.meeting_link,
        "project_id": meeting.project_id,
        "organizer_id": meeting.organizer_id,
        "organizer": {
            "id": meeting.organizer.id,
            "name": meeting.organizer.name,
            "email": meeting.organizer.email,
        } if meeting.organizer else None,
        "attendees": [
            {
                "id": a.id,
                "user_id": a.user_id,
                "status": a.status,
                "user": {
                    "id": a.user.id,
                    "name": a.user.name,
                    "email": a.user.email,
                } if a.user else None,
            }
            for a in (meeting.attendees or [])
        ],
        "created_at": meeting.created_at,
        "updated_at": meeting.updated_at,
    }


class MeetingController:

    @staticmethod
    async def _create_meeting(data: MeetingCreateRequest, db: AsyncSession, current_user):
        meeting = await MeetingService.create_meeting(data, db, current_user)
        return await Response._success_response("Meeting created successfully", _serialize_meeting(meeting))

    @staticmethod
    async def _get_all_meetings(db: AsyncSession):
        meetings = await MeetingService.get_all_meetings(db)
        return await Response._success_response("Meetings fetched successfully", [_serialize_meeting(m) for m in meetings])

    @staticmethod
    async def _get_meeting_by_id(id: int, db: AsyncSession):
        meeting = await MeetingService.get_meeting_by_id(db, id)
        return await Response._success_response("Meeting details fetched successfully", _serialize_meeting(meeting))

    @staticmethod
    async def _update_meeting(id: int, data: MeetingUpdateRequest, db: AsyncSession, current_user):
        meeting = await MeetingService.update_meeting(db, id, data, current_user)
        return await Response._success_response("Meeting updated successfully", _serialize_meeting(meeting))

    @staticmethod
    async def _delete_meeting(id: int, db: AsyncSession, current_user):
        await MeetingService.delete_meeting(db, id, current_user)
        return await Response._success_response("Meeting deleted successfully")

    @staticmethod
    async def _add_attendees(id: int, data: AddAttendeesRequest, db: AsyncSession, current_user):
        meeting = await MeetingAttendeeService.add_attendees(db, id, data.user_ids, current_user)
        return await Response._success_response("Attendees added successfully", _serialize_meeting(meeting))

    @staticmethod
    async def _remove_attendee(meeting_id: int, user_id: int, db: AsyncSession, current_user):
        meeting = await MeetingAttendeeService.remove_attendee(db, meeting_id, user_id, current_user)
        return await Response._success_response("Attendee removed successfully", _serialize_meeting(meeting))
