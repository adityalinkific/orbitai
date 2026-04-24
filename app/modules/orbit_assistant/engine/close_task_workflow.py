"""
Orbit Task Closure Workflow
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.task.task_model import Task, TaskAssignment, TaskStatusEnum
from app.modules.task.task_repository import TaskRepository

async def close_task(db: AsyncSession, task_name: str):
    """Close a task by updating its assignment status to 'reviewed'."""
    try:
        # ---- SAFE VALIDATION ----
        if not task_name:
            return {
                "status": "error",
                "success": False,
                "message": "Task name is required to close a task",
                "data": {}
            }

        # Direct query to find the task
        stmt = select(Task).where(Task.title == task_name)
        result = await db.execute(stmt)
        task = result.scalars().first()

        # ---- IDEMPOTENT CHECK: Task not found ----
        if not task:
            return {
                "status": "success",
                "success": True,
                "message": "Task already closed or does not exist",
                "data": {}
            }

        # Find the task assignment for this task
        stmt = select(TaskAssignment).where(TaskAssignment.task_id == task.id)
        result = await db.execute(stmt)
        assignment = result.scalars().first()

        # ---- IDEMPOTENT CHECK: No assignment ----
        if not assignment:
            return {
                "status": "success",
                "success": True,
                "message": f"Task '{task.title}' has no active assignment - considered closed",
                "data": {
                    "id": task.id,
                    "title": task.title,
                    "status": "no_assignment"
                }
            }

        # ---- IDEMPOTENT CHECK: Already closed ----
        if assignment.status == TaskStatusEnum.reviewed:
            return {
                "status": "success",
                "success": True,
                "message": "Task already closed",
                "data": {
                    "id": task.id,
                    "title": task.title,
                    "status": "reviewed"
                }
            }

        # Update assignment status to reviewed (closest to closed)
        await TaskRepository.update({"status": TaskStatusEnum.reviewed}, assignment)
        await db.commit()
        await db.refresh(assignment)
        
        return {
            "status": "success",
            "success": True, 
            "message": f"Task '{task.title}' closed successfully",
            "data": {
                "id": task.id,
                "title": task.title,
                "status": "reviewed"
            }
        }
    except Exception as e:
        await db.rollback()
        return {
            "status": "error",
            "success": False,
            "message": f"Failed to close task: {str(e)}",
            "data": {}
        }
