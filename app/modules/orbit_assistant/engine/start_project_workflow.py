"""
Orbit Project Activation Workflow
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.resolvers.entity_resolver import EntityResolver

async def start_project(db: AsyncSession, project_name: str):
    project = await EntityResolver.resolve_project(db, project_name)

    if not project:
        return {"success": False, "message": "Project not found"}

    try:
        # Assuming status column exists or description is updated for now
        # project.status = "active" 
        project.description = f"{project.description or ''} [STATUS: ACTIVE]"
        await db.commit()
        return {"success": True, "message": f"Project '{project.name}' started successfully"}
    except Exception as e:
        await db.rollback()
        return {"success": False, "message": str(e)}
