from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey, text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
    

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    emp_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False, index= True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="RESTRICT"), index= True, nullable=False)
    reporting_manager_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index= True, nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="RESTRICT"), index= True, nullable= False)
    is_active = Column(Boolean, server_default=text("true"), nullable=False)
    logged_in = Column(Boolean, server_default=text("false"), nullable=False)
    joined_date = Column(DateTime(timezone= True), server_default= func.now(), nullable= False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    
    role = relationship("Role", back_populates="users", lazy= "selectin")
    department = relationship("Department", back_populates="users", lazy="selectin")
    reporting_manager = relationship("User", remote_side=[id], lazy="selectin")
    
    department = relationship("Department", back_populates="users", foreign_keys=[department_id])
    
class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    role = Column(String(50), unique=True, nullable=False, index= True)
    description = Column(Text, nullable= True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    users = relationship("User", back_populates="role")