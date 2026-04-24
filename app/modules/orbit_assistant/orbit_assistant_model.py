"""
Orbit Assistant — Database Models.
Stores chat sessions, message history, and governance audit logs.
"""

import uuid
import enum

from sqlalchemy import (
    Column, String, Integer, Text, DateTime,
    ForeignKey, Enum, Boolean,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class MessageSender(str, enum.Enum):
    user = "user"
    bot = "bot"


class MessageStatus(str, enum.Enum):
    success = "success"
    denied = "denied"
    clarification = "clarification"
    error = "error"


class AuditResult(str, enum.Enum):
    success = "success"
    denied = "denied"
    error = "error"


# ──────────────────────────────────────────────
# Table 1: chat_sessions
# ──────────────────────────────────────────────

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(
        String(36), unique=True, index=True, nullable=False,
        default=lambda: str(uuid.uuid4()),
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    role = Column(String(50), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    last_active_at = Column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )
    is_active = Column(Boolean, server_default="true", nullable=False)

    # Relationships
    messages = relationship(
        "ChatMessage", back_populates="session",
        cascade="all, delete-orphan", lazy="selectin",
    )
    audit_logs = relationship(
        "ChatAuditLog", back_populates="session",
        cascade="all, delete-orphan", lazy="selectin",
    )


# ──────────────────────────────────────────────
# Table 2: chat_messages
# ──────────────────────────────────────────────

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(
        String(36),
        ForeignKey("chat_sessions.session_id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    sender = Column(Enum(MessageSender), nullable=False)
    message = Column(Text, nullable=False)
    intent = Column(String(100), nullable=True)
    status = Column(Enum(MessageStatus), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # Relationships
    session = relationship("ChatSession", back_populates="messages")


# ──────────────────────────────────────────────
# Table 3: chat_audit_logs
# ──────────────────────────────────────────────

class ChatAuditLog(Base):
    __tablename__ = "chat_audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(
        String(36),
        ForeignKey("chat_sessions.session_id", ondelete="SET NULL"),
        index=True, nullable=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    role = Column(String(50), nullable=False)
    department_id = Column(Integer, nullable=True, index=True)
    intent = Column(String(100), nullable=False)
    action_taken = Column(Text, nullable=True)
    entities_used = Column(Text, nullable=True)  # JSON string of entities
    before_state = Column(Text, nullable=True)  # JSON string of before state
    after_state = Column(Text, nullable=True)  # JSON string of after state
    result = Column(Enum(AuditResult), nullable=False)
    error_message = Column(Text, nullable=True)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # Relationships
    session = relationship("ChatSession", back_populates="audit_logs", viewonly=True)


# ──────────────────────────────────────────────
# Table 4: conversation_states
# ──────────────────────────────────────────────

class ConversationState(Base):
    __tablename__ = "conversation_states"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    session_id = Column(
        String(36),
        ForeignKey("chat_sessions.session_id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    pending_intent = Column(String(100), nullable=True)
    pending_data = Column(Text, nullable=True)
    status = Column(String(50), server_default="active", nullable=False)
    expires_at = Column(
        DateTime(timezone=True), nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )


# ──────────────────────────────────────────────
# Table 5: assistant_logs (Permanent Audit Trail)
# ──────────────────────────────────────────────

class AssistantLog(Base):
    __tablename__ = "assistant_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    session_id = Column(
        String(36),
        ForeignKey("chat_sessions.session_id", ondelete="SET NULL"),
        index=True, nullable=True,
    )
    message = Column(Text, nullable=False)
    intent = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False)  # SUCCESS, FAILED
    error = Column(Text, nullable=True)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
