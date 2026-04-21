"""
Permanent Assistant Logger
Logs all assistant events for production audit trail.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.orbit_assistant.orbit_assistant_model import AssistantLog
from app.modules.orbit_assistant.engine.logger import get_logger

log = get_logger("assistant_logger")


async def log_assistant_event(
    db: AsyncSession,
    user_id: int,
    session_id: str,
    message: str,
    intent: str,
    status: str,
    error: str = None,
):
    """
    Log an assistant event to the permanent audit trail.
    
    Args:
        db: Database session
        user_id: User ID who triggered the event
        session_id: Conversation session ID
        message: User's input message
        intent: Detected intent
        status: SUCCESS or FAILED
        error: Error message if failed
    """
    try:
        log_entry = AssistantLog(
            user_id=user_id,
            session_id=session_id,
            message=message,
            intent=intent,
            status=status,
            error=error
        )
        db.add(log_entry)
        await db.commit()
        log.info(f"Logged assistant event: user_id={user_id}, intent={intent}, status={status}")
    except Exception as e:
        log.error(f"Failed to log assistant event: {str(e)}", exc_info=True)
        # Don't raise - logging failures should not break the assistant
