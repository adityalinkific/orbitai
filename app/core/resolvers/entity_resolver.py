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

        if not clean_name: return None

        # 2. Exact Match Only (removed fuzzy match for safety)
        stmt = select(Project).where(Project.name.ilike(clean_name))
        result = await db.execute(stmt)
        proj = result.scalars().first()
        if proj: return proj

        # No fallback - return None if not found
        return None

    @staticmethod
    async def resolve_user(db: AsyncSession, identifier: Any, session_id: str = None) -> Optional[User]:
        clean_name = EntityResolver._clean_name(str(identifier))
        
        # 1. Direct ID Resolve
        if clean_name.isdigit():
            user = await db.get(User, int(clean_name))
            if user: return user

        if not clean_name: return None

        # 2. Exact Match Only (removed fuzzy match for safety)
        stmt = select(User).where(User.name.ilike(clean_name))
        result = await db.execute(stmt)
        user = result.scalars().first()
        if user: return user

        # No fallback - return None if not found
        return None

    @staticmethod
    async def resolve_task(db: AsyncSession, identifier: Any, session_id: str = None) -> Optional[Task]:
        clean_name = EntityResolver._clean_name(str(identifier))
        
        # 1. Direct ID Resolve
        if clean_name.isdigit():
            task = await db.get(Task, int(clean_name))
            if task: return task

        if not clean_name: return None

        # 2. Exact Match Only (removed fuzzy match for safety)
        stmt = select(Task).where(Task.title.ilike(clean_name))
        result = await db.execute(stmt)
        task = result.scalars().first()
        if task: return task

        # No fallback - return None if not found
        return None

    @staticmethod
    async def resolve_department(db: AsyncSession, identifier: Any, session_id: str = None) -> Optional[Department]:
        clean_name = EntityResolver._clean_name(str(identifier))
        
        # 1. Direct ID Resolve
        if clean_name.isdigit():
            dept = await db.get(Department, int(clean_name))
            if dept: return dept

        if not clean_name: return None

        # 2. Exact Match Only (removed fuzzy match for safety)
        stmt = select(Department).where(Department.name.ilike(clean_name))
        result = await db.execute(stmt)
        dept = result.scalars().first()
        if dept: return dept

        # No fallback - return None if not found
        return None
