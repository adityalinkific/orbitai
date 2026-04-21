"""
ORBIT Assistant History API
Provides user and session history retrieval.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.dependency import get_db
from app.modules.orbit_assistant.orbit_assistant_model import ChatMessage, ChatSession

router = APIRouter(prefix="/history", tags=["History"])

@router.get("/user-history")
async def get_user_history(user_id: int, db: AsyncSession = Depends(get_db)):
    """Returns chat history for a specific user."""
    # Get all sessions for the user
    stmt = select(ChatSession).where(ChatSession.user_id == user_id)
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    
    session_ids = [s.session_id for s in sessions]
    
    if not session_ids:
        return {"user_id": user_id, "sessions": [], "total": 0}
    
    # Get all messages for these sessions
    stmt = select(ChatMessage).where(
        ChatMessage.session_id.in_(session_ids)
    ).order_by(ChatMessage.created_at.desc())
    
    result = await db.execute(stmt)
    messages = result.scalars().all()
    
    return {
        "user_id": user_id,
        "total_sessions": len(sessions),
        "total_messages": len(messages),
        "messages": [
            {
                "session_id": m.session_id,
                "sender": m.sender.value,
                "message": m.message,
                "intent": m.intent,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in messages
        ]
    }

@router.get("/session/{session_id}")
async def get_session_history(session_id: str, db: AsyncSession = Depends(get_db)):
    """Returns chat messages for a specific session."""
    stmt = select(ChatMessage).where(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.asc())
    
    result = await db.execute(stmt)
    messages = result.scalars().all()
    
    return {
        "session_id": session_id,
        "total_messages": len(messages),
        "messages": [
            {
                "sender": m.sender.value,
                "message": m.message,
                "intent": m.intent,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in messages
        ]
    }
