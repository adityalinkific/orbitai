"""
Audit Logger — Governance Business Audit Trail with DB Persistence.
Records every action (success, denied, error) to chat_audit_logs table.
"""

from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from .logger import get_logger

system_log = get_logger("audit_logger")


class AuditLogger:
    """
    Orbit Audit Logger Service
    Singleton used across assistant pipeline
    """

    # =====================================================
    # LOG ACTION
    # =====================================================
    async def log_action(
        self,
        db: AsyncSession,
        session_id: Optional[str],
        user_id: int,
        role: str,
        intent: str,
        action_taken: str,
        result: str,
        error_message: Optional[str] = None,
    ):
        """
        Persist governance audit entry.
        """

        from app.modules.orbit_assistant.orbit_assistant_model import (
            ChatAuditLog,
            AuditResult,
        )

        try:

            # Map string → enum
            result_enum = AuditResult.success
            if result.lower() == "denied":
                result_enum = AuditResult.denied
            elif result.lower() in ("error", "failure"):
                result_enum = AuditResult.error

            audit_entry = ChatAuditLog(
                session_id=session_id,
                user_id=user_id,
                role=role,
                intent=intent,
                action_taken=action_taken,
                result=result_enum,
                error_message=error_message,
            )

            db.add(audit_entry)
            await db.flush()

            system_log.info(
                f"[AUDIT] user={user_id} role={role} "
                f"intent={intent} result={result} session={session_id}"
            )

        except Exception as e:
            # NEVER break assistant flow
            system_log.error(
                f"[AUDIT_FAIL] Could not persist audit entry: {str(e)} "
                f"user={user_id} intent={intent}"
            )

    # =====================================================
    # FETCH AUDIT LOGS
    # =====================================================
    async def get_audit_log(
        self,
        db: AsyncSession,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:

        from sqlalchemy import select
        from app.modules.orbit_assistant.orbit_assistant_model import ChatAuditLog

        stmt = select(ChatAuditLog).order_by(
            ChatAuditLog.timestamp.desc()
        )

        if user_id:
            stmt = stmt.where(ChatAuditLog.user_id == user_id)

        if session_id:
            stmt = stmt.where(ChatAuditLog.session_id == session_id)

        stmt = stmt.limit(limit)

        try:
            result = await db.execute(stmt)
            entries = result.scalars().all()

            return [
                {
                    "id": e.id,
                    "session_id": e.session_id,
                    "user_id": e.user_id,
                    "role": e.role,
                    "intent": e.intent,
                    "action_taken": e.action_taken,
                    "result": e.result.value if e.result else None,
                    "error_message": e.error_message,
                    "timestamp": (
                        e.timestamp.isoformat() if e.timestamp else None
                    ),
                }
                for e in entries
            ]

        except Exception as e:
            system_log.error(f"Failed to query audit log: {str(e)}")
            return []


# =====================================================
# REQUIRED SINGLETON EXPORT
# =====================================================
audit_logger = AuditLogger()