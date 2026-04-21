"""
Orbit Assistant — Entity Resolver
Converts human language entities → database IDs
"""

from sqlalchemy import select
from typing import Dict, Any

from app.modules.project.project_model import Project
from app.modules.auth.auth_model import User
from app.modules.department.department_model import Department
from app.modules.task.task_model import Task


async def _resolve_project(db, name: str):
    stmt = select(Project).where(Project.name.ilike(f"%{name}%"))
    res = await db.execute(stmt)
    return res.scalars().first()


async def _resolve_user(db, name: str):
    stmt = select(User).where(User.name.ilike(f"%{name}%"))
    res = await db.execute(stmt)
    return res.scalars().first()


async def _resolve_department(db, name: str):
    stmt = select(Department).where(Department.name.ilike(f"%{name}%"))
    res = await db.execute(stmt)
    return res.scalars().first()


async def _resolve_task(db, title: str):
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

    # DEPARTMENT
    if "department_name" in entities and "department_id" not in entities:
        dept = await _resolve_department(db, entities["department_name"])
        if dept:
            entities["department_id"] = dept.id

    # TASK
    if "task_title" in entities and "task_id" not in entities:
        task = await _resolve_task(db, entities["task_title"])
        if task:
            entities["task_id"] = task.task_id

    return entities