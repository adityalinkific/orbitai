"""
Orbit Entity Resolver (Enterprise Edition)
Centralized logic for resolving natural language names/IDs to database objects.
Supports noise word removal, fuzzy matching, and context-aware fallback.
"""

import re
from typing import Any, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.project.project_model import Project
from app.modules.auth.auth_model import User
from app.modules.task.task_model import Task
from app.modules.department.department_model import Department
from app.modules.orbit_assistant.engine.context_manager import context_manager

# Noise words to strip from entity names
NOISE_WORDS = [
    r"\bproject\b", r"\btask\b", r"\bdepartment\b", r"\buser\b",
    r"\bid\b", r"\bnamed\b", r"\bcalled\b", r"\bthe\b", r"\ba\b", r"\ban\b"
    r"\bnamed\b", r"\bcalled\b", r"\bthe\b", r"\ba\b", r"\ban\b"
]

class EntityResolver:
    """
    Standardizes how we find entities with deep natural language support.
    """

    @staticmethod
    def _clean_name(name: str) -> str:
        if not name: return ""
        clean = name.lower()
        # Remove punctuation that may wrap names or IDs
        clean = re.sub(r"[\"'`#,:;]", "", clean)
        for word in NOISE_WORDS:
            clean = re.sub(word, "", clean)
        clean = re.sub(r"\s+", " ", clean)
        for word in NOISE_WORDS:
            clean = re.sub(word, "", clean)
        return clean.strip()

    @staticmethod
    async def resolve_project(db: AsyncSession, identifier: Any, session_id: str = None) -> Optional[Project]:
        clean_name = EntityResolver._clean_name(str(identifier))
        
        # 1. Direct ID Resolve
        if clean_name.isdigit():
            proj = await db.get(Project, int(clean_name))
            if proj: return proj

        # 2. Context Fallback (for "it", "this project", or missing name)
        if not clean_name or clean_name in ["it", "this", "project", "same"]:
            if session_id:
                ctx = context_manager._sessions.get(session_id, {})
                last_id = ctx.get("last_project_id") or ctx.get("active_entities", {}).get("project")
                if last_id:
                    return await db.get(Project, int(last_id))

        if not clean_name: return None

        # 3. Exact Match
        stmt = select(Project).where(Project.name.ilike(clean_name))
        result = await db.execute(stmt)
        proj = result.scalars().first()
        if proj: return proj

        # 4. Partial Match
        stmt = select(Project).where(Project.name.ilike(f"%{clean_name}%"))
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def resolve_user(db: AsyncSession, identifier: Any, session_id: str = None) -> Optional[User]:
        clean_name = EntityResolver._clean_name(str(identifier))
        
        if clean_name.isdigit():
            user = await db.get(User, int(clean_name))
            if user: return user

        if not clean_name or clean_name in ["it", "this", "user", "them", "him", "her"]:
            if session_id:
                ctx = context_manager._sessions.get(session_id, {})
                last_id = ctx.get("last_user_id") or ctx.get("active_entities", {}).get("user")
                if last_id:
                    return await db.get(User, int(last_id))

        if not clean_name: return None

        if "@" in clean_name:
            stmt = select(User).where(User.email.ilike(clean_name))
            result = await db.execute(stmt)
            user = result.scalars().first()
            if user: return user

        stmt = select(User).where(User.name.ilike(clean_name))
        result = await db.execute(stmt)
        user = result.scalars().first()
        if user: return user

        stmt = select(User).where(User.name.ilike(f"%{clean_name}%"))
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def resolve_task(db: AsyncSession, identifier: Any, session_id: str = None) -> Optional[Task]:
        clean_name = EntityResolver._clean_name(str(identifier))
        
        if clean_name.isdigit():
            task = await db.get(Task, int(clean_name))
            if task: return task

        # Support explicit task_id lookup when the identifier is a UUID or task token.
        if clean_name:
            stmt = select(Task).where(Task.task_id == clean_name)
            result = await db.execute(stmt)
            task = result.scalars().first()
            if task: return task

        if not clean_name or clean_name in ["it", "this", "task", "job"]:
            if session_id:
                ctx = context_manager._sessions.get(session_id, {})
                last_id = ctx.get("last_task_id") or ctx.get("active_entities", {}).get("task")
                if last_id:
                    return await db.get(Task, int(last_id))

        if not clean_name: return None

        stmt = select(Task).where(Task.title.ilike(clean_name))
        result = await db.execute(stmt)
        task = result.scalars().first()
        if task: return task

        stmt = select(Task).where(Task.title.ilike(f"%{clean_name}%"))
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def resolve_department(db: AsyncSession, identifier: Any, session_id: str = None) -> Optional[Department]:
        clean_name = EntityResolver._clean_name(str(identifier))
        
        if clean_name.isdigit():
            dept = await db.get(Department, int(clean_name))
            if dept: return dept

        if not clean_name: return None

        stmt = select(Department).where(Department.name.ilike(clean_name))
        result = await db.execute(stmt)
        dept = result.scalars().first()
        if dept: return dept

        stmt = select(Department).where(Department.name.ilike(f"%{clean_name}%"))
        result = await db.execute(stmt)
        return result.scalars().first()
