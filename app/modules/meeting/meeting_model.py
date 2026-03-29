from sqlalchemy import Column, String, Integer, Text, Date, DateTime, ForeignKey, Enum
import enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class AttendeeStatusEnum(str, enum.Enum):
    invited = "invited"
    accepted = "accepted"
    declined = "declined"


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    meeting_date = Column(Date, nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    organizer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(50), default="Scheduled", nullable=False)
    meeting_link = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    organizer = relationship("User", lazy="selectin")
    project = relationship("Project", backref="meetings", lazy="selectin")
    attendees = relationship("MeetingAttendee", back_populates="meeting", lazy="selectin", cascade="all, delete-orphan")


class MeetingAttendee(Base):
    __tablename__ = "meeting_attendees"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Enum(AttendeeStatusEnum), default=AttendeeStatusEnum.invited, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    meeting = relationship("Meeting", back_populates="attendees")
    user = relationship("User", lazy="selectin")
