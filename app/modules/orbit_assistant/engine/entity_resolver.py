"""
Orbit Assistant — Entity Resolver
Converts human language entities → database IDs
"""

from sqlalchemy import select
from typing import Dict, Any
import re

from app.modules.project.project_model import Project
from app.modules.auth.auth_model import User
from app.modules.department.department_model import Department
from app.modules.task.task_model import Task


def _clean_name(name: str) -> str:
    if not name:
        return ""
    clean = name.lower()
    clean = re.sub(r"[\"'`#,:;]", "", clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


async def _resolve_project(db, name: str):
    clean_name = _clean_name(name)
    stmt = select(Project).where(Project.name.ilike(f"%{clean_name}%"))
async def _resolve_project(db, name: str):
    stmt = select(Project).where(Project.name.ilike(f"%{name}%"))
    res = await db.execute(stmt)
    return res.scalars().first()


async def _resolve_user(db, name: str):
    clean_name = _clean_name(name)
    stmt = select(User).where(User.name.ilike(f"%{clean_name}%"))
    stmt = select(User).where(User.name.ilike(f"%{name}%"))
    res = await db.execute(stmt)
    return res.scalars().first()


async def _resolve_department(db, name: str):
    clean_name = _clean_name(name)
    stmt = select(Department).where(Department.name.ilike(f"%{clean_name}%"))
    stmt = select(Department).where(Department.name.ilike(f"%{name}%"))
    res = await db.execute(stmt)
    return res.scalars().first()


async def _resolve_task(db, title: str):
    clean_title = _clean_name(title)
    if clean_title.isdigit():
        task = await db.get(Task, int(clean_title))
        if task:
            return task
    stmt = select(Task).where(Task.title.ilike(f"%{clean_title}%"))
    stmt = select(Task).where(Task.title.ilike(f"%{title}%"))
    res = await db.execute(stmt)
    return res.scalars().first()


async def resolve_entities(intent: str, entities: Dict[str, Any], session):
    """
    Inject DB IDs required by services.
    """

    db = session["db"]

    # PROJECT
    if "project_name" in entities and "project_id" not in entities:
        project = await _resolve_project(db, entities["project_name"])
        if project:
            entities["project_id"] = project.id

    # USER
    if "user_name" in entities and "user_id" not in entities:
        user = await _resolve_user(db, entities["user_name"])
        if user:
            entities["user_id"] = user.id
    elif "user" in entities and "user_id" not in entities:
        user = await _resolve_user(db, entities["user"])
        if user:
            entities["user_id"] = user.id

    # DEPARTMENT
    if "department_name" in entities and "department_id" not in entities:
        dept = await _resolve_department(db, entities["department_name"])
        if dept:
            entities["department_id"] = dept.id

    # TASK
    if "task_title" in entities and "task_id" not in entities:
        task = await _resolve_task(db, entities["task_title"])
        if task:
            entities["task_id"] = task.id
    elif "task" in entities and "task_id" not in entities:
        task = await _resolve_task(db, entities["task"])
        if task:
            entities["task_id"] = task.id
            entities["task_id"] = task.task_id

    return entities