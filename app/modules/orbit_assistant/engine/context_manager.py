"""
Context Manager — Per-user session tracking with DB persistence.
Maintains department, recent actions, and active entity references
so users can say "same project" and it resolves correctly.
"""

import uuid
from typing import Any, Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.orbit_assistant.engine.logger import get_logger

log = get_logger("context_manager")
log.info("Context Manager initialized")

# ==========================================================

# Context Manager Service (Singleton)

# ==========================================================

class ContextManager:

    def __init__(self):
        # in-memory hot cache
        self._sessions: dict[str, dict[str, Any]] = {}

    def resolve_pronoun(self, session_id: str, query: str) -> str:
        """Replace 'it', 'that', 'this' with last referenced entity name."""
        session = self._sessions.get(session_id)
        if not session:
            return query

        import re
        pronouns = ["it", "that", "this"]
        last_task = session.get("last_task_name")
        last_project = session.get("last_project_name")

        for p in pronouns:
            if re.search(rf"\b{p}\b", query, re.IGNORECASE):
                if last_task:
                    query = re.sub(rf"\b{p}\b", last_task, query, flags=re.IGNORECASE)
                    log.info(f"Resolved pronoun '{p}' to task '{last_task}'")
                    break
                elif last_project:
                    query = re.sub(rf"\b{p}\b", last_project, query, flags=re.IGNORECASE)
                    log.info(f"Resolved pronoun '{p}' to project '{last_project}'")
                    break
        return query

    # ------------------------------------------------------
    # Session Management
    # ------------------------------------------------------
    async def get_or_create_session(
        self,
        session_id: Optional[str],
        user_id: int,
        role: str,
        db: AsyncSession,
    ) -> dict[str, Any]:

        from app.modules.orbit_assistant.orbit_assistant_model import ChatSession

        # ---------- Resume Existing Session ----------
        if session_id:

            if session_id in self._sessions:
                log.info(f"Session resumed (memory): {session_id}")
                return self._sessions[session_id]

            stmt = select(ChatSession).where(
                ChatSession.session_id == session_id,
                ChatSession.user_id == user_id,
                ChatSession.is_active.is_(True),
            )

            result = await db.execute(stmt)
            session_row = result.scalars().first()

            if session_row:
                session_row.last_active_at = datetime.now(timezone.utc)
                await db.flush()

                ctx = self._build_context(
                    session_id=session_id,
                    user_id=user_id,
                    role=role,
                )

                self._sessions[session_id] = ctx
                log.info(f"Session resumed (DB): {session_id}")
                return ctx

        # ---------- Create New Session ----------
        new_session_id = str(uuid.uuid4())

        session_row = ChatSession(
            session_id=new_session_id,
            user_id=user_id,
            role=role,
        )

        db.add(session_row)
        await db.flush()

        ctx = self._build_context(
            session_id=new_session_id,
            user_id=user_id,
            role=role,
        )

        self._sessions[new_session_id] = ctx

        log.info(f"New session created: {new_session_id}")
        return ctx

    # ------------------------------------------------------
    # Context Builder
    # ------------------------------------------------------
    def _build_context(self, session_id: str, user_id: int, role: str):
        return {
            "session_id": session_id,
            "user_id": user_id,
            "role": role,
            "department": None,
            "recent_actions": [],
            "active_entities": {},
            "last_project_id": None,
            "last_project_name": None,
            "last_task_id": None,
            "last_task_name": None,
            "last_user_id": None,
            "last_user_name": None,
            "awaiting_confirmation": False,
        }

    # ------------------------------------------------------
    # Message Persistence
    # ------------------------------------------------------
    async def save_message(
        self,
        session_id: str,
        sender: str,
        message: str,
        db: AsyncSession,
        intent: Optional[str] = None,
        status: Optional[str] = None,
    ):

        from app.modules.orbit_assistant.orbit_assistant_model import (
            ChatMessage,
            MessageSender,
            MessageStatus,
        )

        try:
            sender_enum = MessageSender(sender)
        except Exception:
            sender_enum = MessageSender.user

        status_enum = None
        if status:
            try:
                status_enum = MessageStatus(status)
            except Exception:
                pass

        msg = ChatMessage(
            session_id=session_id,
            sender=sender_enum,
            message=message,
            intent=intent,
            status=status_enum,
        )

        db.add(msg)
        await db.flush()

        log.info(f"Message saved | session={session_id}")

    # ------------------------------------------------------
    # Message History
    # ------------------------------------------------------
    async def get_message_history(
        self,
        session_id: str,
        user_id: int,
        db: AsyncSession,
    ) -> list[dict]:

        from app.modules.orbit_assistant.orbit_assistant_model import (
            ChatMessage,
            ChatSession,
        )

        stmt = select(ChatSession).where(
            ChatSession.session_id == session_id,
            ChatSession.user_id == user_id,
        )

        result = await db.execute(stmt)
        if not result.scalars().first():
            return []

        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )

        result = await db.execute(stmt)
        messages = result.scalars().all()

        return [
            {
                "sender": m.sender.value,
                "message": m.message,
                "intent": m.intent,
                "status": m.status.value if m.status else None,
                "created_at": m.created_at,
            }
            for m in messages
        ]

    # ------------------------------------------------------
    # Session End
    # ------------------------------------------------------
    async def end_session(
        self,
        session_id: str,
        user_id: int,
        db: AsyncSession,
    ) -> bool:

        from app.modules.orbit_assistant.orbit_assistant_model import ChatSession

        stmt = select(ChatSession).where(
            ChatSession.session_id == session_id,
            ChatSession.user_id == user_id,
        )

        result = await db.execute(stmt)
        session_row = result.scalars().first()

        if not session_row:
            return False

        session_row.is_active = False
        await db.flush()

        self._sessions.pop(session_id, None)

        log.info(f"Session ended: {session_id}")
        return True

    # ------------------------------------------------------
    # Context Tracking
    # ------------------------------------------------------
    def update_context(
        self,
        session_id: str,
        intent: str,
        entities: dict[str, Any],
        result: Optional[dict[str, Any]] = None,
        max_history: int = 10,
    ):

        session = self._sessions.get(session_id)
        if not session:
            return

        action = {"intent": intent, "entities": entities}

        if result and isinstance(result, dict):
            data = result.get("data")
            if isinstance(data, dict) and data.get("id"):
                action["result_id"] = data["id"]

        session["recent_actions"].append(action)
        session["recent_actions"] = session["recent_actions"][-max_history:]

        self._track_entity_refs(session, intent, entities, result)

    # ------------------------------------------------------
    def resolve_references(
        self,
        session_id: str,
        entities: dict[str, Any],
    ) -> dict[str, Any]:

        session = self._sessions.get(session_id)
        if not session:
            return entities

        resolved = dict(entities)

        for entity_type, ref_id in session["active_entities"].items():
            key = f"{entity_type}_id"
            resolved.setdefault(key, ref_id)

        if session.get("department"):
            resolved.setdefault("department_id", session["department"])

        return resolved

    # ------------------------------------------------------
    def set_department(self, session_id: str, department: str):
        session = self._sessions.get(session_id)
        if session:
            session["department"] = department

    # ------------------------------------------------------
    def clear_entity_after_deletion(self, session_id: str, entity_type: str):
        session = self._sessions.get(session_id)
        if session:
            session["active_entities"].pop(entity_type, None)

    # ------------------------------------------------------
    def _track_entity_refs(self, session, intent, entities, result):

        if "_" not in intent:
            return

        _, entity_type = intent.split("_", 1)
        entity_type = entity_type.lower()

        entity_id = (
            entities.get("id")
            or entities.get(f"{entity_type}_id")
        )

        if not entity_id and result:
            data = result.get("data", {})
            if isinstance(data, dict):
                entity_id = data.get("id")

        if entity_id:
            session["active_entities"][entity_type] = entity_id
            
            # Populate primary memory fields
            entity_name = None
            if result:
                data = result.get("data", {})
                if isinstance(data, dict):
                    entity_name = data.get("name") or data.get("title")

            if entity_type == "project":
                session["last_project_id"] = entity_id
                if entity_name: session["last_project_name"] = entity_name
            elif entity_type == "task":
                session["last_task_id"] = entity_id
                if entity_name: session["last_task_name"] = entity_name
            elif entity_type == "user":
                session["last_user_id"] = entity_id
                if entity_name: session["last_user_name"] = entity_name

# ==========================================================

# REQUIRED SINGLETON EXPORT

# ==========================================================

context_manager = ContextManager()
