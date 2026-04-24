from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class ProjectStatusEnum(str, enum.Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    archived = "archived"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable= True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="RESTRICT"), index= True, nullable= False)
    status = Column(Enum(ProjectStatusEnum), default=ProjectStatusEnum.draft, nullable=False)
    manager_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index= True, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    department = relationship("Department", back_populates="projects")
    manager = relationship("User", foreign_keys=[manager_id])
    creator = relationship("User", foreign_keys=[created_by])
