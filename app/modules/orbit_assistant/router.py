"""
ORBIT Assistant Unified Router
All Orbit Assistant capabilities in one place.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependency import get_db, get_current_user
from app.modules.orbit_assistant.assistant_service import assistant_service
from app.modules.orbit_assistant.schemas import ChatRequest
from app.modules.orbit_assistant.engine.executor import Executor

router = APIRouter(prefix="/api/v1/assistant", tags=["Orbit Assistant"])


# ──────────────────────────────────────────────────────────
# CHAT ENDPOINT
# ──────────────────────────────────────────────────────────
@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Process an Orbit Assistant command."""
    return await assistant_service.chat(
        request=request,
        db=db,
        current_user=current_user,
    )


# ──────────────────────────────────────────────────────────
# CAPABILITIES ENDPOINT
# ──────────────────────────────────────────────────────────
@router.get("/capabilities")
async def capabilities(current_user=Depends(get_current_user)):
    """Returns role-filtered capabilities for the authenticated user."""
    from app.modules.orbit_assistant.engine.capability_resolver import capability_resolver
    from app.modules.orbit_assistant.system_intents import SYSTEM_ONLY_INTENTS
    
    # Extract role from JWT token (priority) or database (fallback)
    user_role = None
    if hasattr(current_user, 'role_from_token') and current_user.role_from_token:
        user_role = current_user.role_from_token
    elif hasattr(current_user, 'role') and current_user.role:
        user_role = current_user.role.role
    else:
        user_role = "EMPLOYEE"  # Default fallback
    
    # Get role-filtered capabilities
    capabilities = capability_resolver.get_user_capabilities(user_role)
    
    return {
        "role": user_role.upper(),
        "capabilities": capabilities,
        "total": len(capabilities)
    }


# ──────────────────────────────────────────────────────────
# HISTORY ENDPOINTS
# ──────────────────────────────────────────────────────────
@router.get("/history/user")
async def user_history(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns chat history for current user."""
    from app.modules.orbit_assistant.orbit_assistant_model import ChatMessage, ChatSession
    from sqlalchemy import select
    
    stmt = select(ChatSession).where(ChatSession.user_id == current_user.id)
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    
    session_ids = [s.session_id for s in sessions]
    
    if not session_ids:
        return {"user_id": current_user.id, "total_sessions": 0, "total_messages": 0, "messages": []}
    
    stmt = select(ChatMessage).where(
        ChatMessage.session_id.in_(session_ids)
    ).order_by(ChatMessage.created_at.desc())
    
    result = await db.execute(stmt)
    messages = result.scalars().all()
    
    return {
        "user_id": current_user.id,
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
            for m in messages[:50]
        ]
    }


@router.get("/history/session/{session_id}")
async def session_history(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Returns chat messages for a specific session."""
    from app.modules.orbit_assistant.orbit_assistant_model import ChatMessage
    from sqlalchemy import select
    
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


# ──────────────────────────────────────────────────────────
# HEALTH ENDPOINT
# ──────────────────────────────────────────────────────────
@router.get("/health")
async def health():
    """Orbit Assistant health check."""
    return {
        "assistant": "ready",
        "email": "configured",
        "history": "active",
        "workflow": "ready",
        "status": "operational"
    }
