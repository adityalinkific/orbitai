from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.meeting.meeting_model import Meeting, MeetingAttendee
from app.modules.meeting.meeting_schema import MeetingCreateRequest, MeetingUpdateRequest
from app.modules.meeting.meeting_repository import MeetingRepository, GetMeetingRecord, DeleteMeeting, MeetingAttendeeRepository
from app.modules.project.project_model import Project
from app.modules.auth.auth_model import User
from app.modules.auth.auth_repository import GetRecord
from app.core.email_service import EmailService
import secrets
import string


class MeetingService:

    @staticmethod
    def _generate_link() -> str:
        chars = string.ascii_lowercase + string.digits
        token = ''.join(secrets.choice(chars) for _ in range(10))
        return f"https://meet.orbit.com/{token}"

    @staticmethod
    async def create_meeting(data: MeetingCreateRequest, db: AsyncSession, current_user):
        # Verify project exists if project_id is provided
        if data.project_id is not None:
            project = await GetRecord._get_one(db, Project, Project.id == data.project_id)
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Invalid project selected'
                )

        # Resolve organizer: admin may select a different organizer
        organizer_id = current_user.id
        if data.organizer_id and data.organizer_id != current_user.id:
            organizer = await GetRecord._get_one(db, User, User.id == data.organizer_id)
            if not organizer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Organizer user with id {data.organizer_id} not found"
                )
            organizer_id = data.organizer_id

        # Validate attendee user IDs
        if data.attendee_user_ids:
            for uid in data.attendee_user_ids:
                user = await GetRecord._get_one(db, User, User.id == uid)
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Attendee user with id {uid} not found"
                    )

        # Generate meeting link if requested
        meeting_link = MeetingService._generate_link() if data.generate_meeting_link else data.meeting_link

        meeting = Meeting(
            title=data.title,
            description=data.description,
            meeting_date=data.meeting_date,
            start_time=data.start_time,
            end_time=data.end_time,
            project_id=data.project_id,
            status=data.status,
            meeting_link=meeting_link,
            organizer_id=organizer_id
        )

        try:
            await MeetingRepository._create_meeting(db, meeting)
            await db.commit()
            await db.refresh(meeting)

            # Persist attendees
            if data.attendee_user_ids:
                await MeetingAttendeeRepository._add_attendees(db, meeting.id, data.attendee_user_ids)
                await db.commit()
                await db.refresh(meeting)

        except Exception:
            await db.rollback()
            raise

        # Send email invites AFTER successful DB commit
        if data.attendee_emails:
            organizer_name = getattr(current_user, 'name', 'The Organizer')
            subject = f"Meeting Invite: {data.title}"
            body = (
                f"Hi,\n\n"
                f"You have been invited to a meeting by {organizer_name}.\n\n"
                f"📅  Title:       {data.title}\n"
                f"📆  Date:        {data.meeting_date}\n"
                f"🕒  Start Time:  {data.start_time.strftime('%A, %d %B %Y at %H:%M UTC')}\n"
            )
            if data.end_time:
                body += f"🕔  End Time:    {data.end_time.strftime('%A, %d %B %Y at %H:%M UTC')}\n"
            if data.description:
                body += f"\n📝  Details:\n{data.description}\n"
            body += "\nPlease update your calendar accordingly.\n\nRegards,\nOrbit Governance System"

            await EmailService.send_email(
                to=[str(email) for email in data.attendee_emails],
                subject=subject,
                body=body,
            )

        return meeting

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

        if meeting.organizer_id != current_user.id and current_user.role.role.lower() != 'super_admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this meeting"
            )

        if data.project_id is not None and data.project_id != meeting.project_id:
            project = await GetRecord._get_one(db, Project, Project.id == data.project_id)
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Invalid project selected'
                )

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


class MeetingAttendeeService:

    @staticmethod
    async def add_attendees(db: AsyncSession, meeting_id: int, user_ids: list[int], current_user):
        meeting = await GetMeetingRecord._get_one(db, Meeting, Meeting.id == meeting_id)
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

        if meeting.organizer_id != current_user.id and current_user.role.role.lower() != 'super_admin':
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

        for uid in user_ids:
            user = await GetRecord._get_one(db, User, User.id == uid)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with id {uid} not found"
                )

        try:
            await MeetingAttendeeRepository._add_attendees(db, meeting_id, user_ids)
            await db.commit()
            await db.refresh(meeting)
        except Exception:
            await db.rollback()
            raise

        return meeting

    @staticmethod
    async def remove_attendee(db: AsyncSession, meeting_id: int, user_id: int, current_user):
        meeting = await GetMeetingRecord._get_one(db, Meeting, Meeting.id == meeting_id)
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

        if meeting.organizer_id != current_user.id and current_user.role.role.lower() != 'super_admin':
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

        try:
            attendee = await MeetingAttendeeRepository._remove_attendee(db, meeting_id, user_id)
            if not attendee:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendee not found in this meeting")
            await db.commit()
            await db.refresh(meeting)
        except HTTPException:
            raise
        except Exception:
            await db.rollback()
            raise

        return meeting
