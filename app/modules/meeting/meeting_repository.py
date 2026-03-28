from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.meeting.meeting_model import Meeting

class MeetingRepository:
    @staticmethod
    async def _create_meeting(db: AsyncSession, meeting: Meeting):
        db.add(meeting)
        return meeting

    @staticmethod
    async def _update(update_data: dict, instance: any):
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
