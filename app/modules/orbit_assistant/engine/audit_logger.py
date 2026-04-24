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
        department_id: Optional[int],
        intent: str,
        action_taken: str,
        entities_used: Optional[dict] = None,
        before_state: Optional[dict] = None,
        after_state: Optional[dict] = None,
        result: str = "success",
        error_message: Optional[str] = None,
    ):
        """
        Persist governance audit entry with full state capture.

        Args:
            db: Database session
            session_id: Chat session ID
            user_id: User ID
            role: User role
            department_id: User's department ID
            intent: Intent being executed
            action_taken: Description of action
            entities_used: Dictionary of entities used in execution
            before_state: Dictionary of state before execution
            after_state: Dictionary of state after execution
            result: Execution result (success/denied/error)
            error_message: Error message if failed
        """
        import json

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
                department_id=department_id,
                intent=intent,
                action_taken=action_taken,
                entities_used=json.dumps(entities_used) if entities_used else None,
                before_state=json.dumps(before_state) if before_state else None,
                after_state=json.dumps(after_state) if after_state else None,
                result=result_enum,
                error_message=error_message,
            )

            db.add(audit_entry)
            await db.flush()

            system_log.info(
                f"[AUDIT] user={user_id} role={role} dept={department_id} "
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

            import json
            return [
                {
                    "id": e.id,
                    "session_id": e.session_id,
                    "user_id": e.user_id,
                    "role": e.role,
                    "department_id": e.department_id,
                    "intent": e.intent,
                    "action_taken": e.action_taken,
                    "entities_used": json.loads(e.entities_used) if e.entities_used else None,
                    "before_state": json.loads(e.before_state) if e.before_state else None,
                    "after_state": json.loads(e.after_state) if e.after_state else None,
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