from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.meeting.meeting_model import Meeting, MeetingAttendee


class MeetingRepository:
    @staticmethod
    async def _create_meeting(db: AsyncSession, meeting: Meeting):
        db.add(meeting)
        return meeting

    @staticmethod
    async def _update(update_data: dict, instance):
        for field, value in update_data.items():
            setattr(instance, field, value)
        return instance


class GetMeetingRecord:
    @staticmethod
    async def _get_one(db: AsyncSession, model, *conditions):
        stmt = select(model).where(*conditions)
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def _get_all(db: AsyncSession):
        stmt = select(Meeting).order_by(Meeting.id.desc())
        result = await db.execute(stmt)
        return result.scalars().all()


class DeleteMeeting:
    @staticmethod
    async def _delete_meeting(db: AsyncSession, meeting: Meeting):
        return await db.delete(meeting)


class MeetingAttendeeRepository:
    @staticmethod
    async def _add_attendees(db: AsyncSession, meeting_id: int, user_ids: list[int]):
        """Bulk-insert attendees, skipping duplicates."""
        existing_stmt = select(MeetingAttendee.user_id).where(
            MeetingAttendee.meeting_id == meeting_id
        )
        result = await db.execute(existing_stmt)
        existing_user_ids = set(result.scalars().all())

        new_attendees = [
            MeetingAttendee(meeting_id=meeting_id, user_id=uid)
            for uid in user_ids
            if uid not in existing_user_ids
        ]
        if new_attendees:
            db.add_all(new_attendees)
        return new_attendees

    @staticmethod
    async def _remove_attendee(db: AsyncSession, meeting_id: int, user_id: int):
        stmt = select(MeetingAttendee).where(
            MeetingAttendee.meeting_id == meeting_id,
            MeetingAttendee.user_id == user_id,
        )
        result = await db.execute(stmt)
        attendee = result.scalars().first()
        if attendee:
            await db.delete(attendee)
        return attendee
