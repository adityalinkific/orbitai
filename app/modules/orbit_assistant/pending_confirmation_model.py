from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.sql import func
from app.core.database.database import Base


class PendingConfirmation(Base):
    """Model for storing pending confirmation requests."""
    
    __tablename__ = "pending_confirmations"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(36), unique=True, nullable=False, index=True)
    intent = Column(String(100), nullable=False)
    entity = Column(String(255), nullable=False)
    user_id = Column(Integer, nullable=False, index=True)
    payload = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending, confirmed, expired, cancelled
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<PendingConfirmation(request_id={self.request_id}, intent={self.intent}, status={self.status})>"
