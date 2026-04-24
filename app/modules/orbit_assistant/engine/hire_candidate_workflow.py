"""
Orbit Candidate Hiring Workflow
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.auth.auth_model import User
from app.core.resolvers.entity_resolver import EntityResolver
from app.modules.orbit_assistant.engine.email_service import EmailService
from app.modules.orbit_assistant.engine.audit_logger import audit_logger
import uuid

async def run_hire_candidate(db: AsyncSession, name: str, email: str, department_name: str, role_id: int):
    # 1. Validate department
    dept = await EntityResolver.resolve_department(db, department_name)
    if not dept:
        return {"success": False, "message": f"Department '{department_name}' not found."}

    # 2. Create user record (Role = Candidate/Employee)
    user = User(
        emp_id=f"LF-{uuid.uuid4().hex[:6].upper()}",
        name=name,
        email=email,
        password="TEMPORARY_PASSWORD", # Should be changed
        role_id=role_id,
        department_id=dept.id,
        is_active=True
    )

    try:
        db.add(user)
        await db.flush() # Flush to get user.id

        # 3. Send Welcome Email
        subject = "Welcome to Orbit Governance System"
        body = f"Hello {name},\n\nYou have been hired into the {dept.name} department. Your account is being set up."
        await EmailService.send_email(email, subject, body)

        # 4. Log Hire Event
        await audit_logger.log_action(
            db=db,
            session_id=None, # Workflow doesn't have it easily available here yet
            user_id=user.id, # New user ID
            role="admin",    # Assuming admin for system actions
            intent="HIRE_CANDIDATE",
            action_taken=f"Hired {name} into {dept.name}",
            result="success"
        )

        await db.commit()
        return {"success": True, "message": f"{name} hired successfully into {dept.name}", "data": {"id": user.id}}
    except Exception as e:
        await db.rollback()
        return {"success": False, "message": str(e)}
