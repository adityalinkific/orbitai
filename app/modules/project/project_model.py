import enum

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Enum, text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class ProjectStatusEnum(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    archived = "archived"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(ProjectStatusEnum, name="projectstatusenum"),
        default=ProjectStatusEnum.active,
        server_default=text("'active'::projectstatusenum"),
        nullable=False,
    )
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="RESTRICT"), index=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    department = relationship("Department", back_populates="projects")
