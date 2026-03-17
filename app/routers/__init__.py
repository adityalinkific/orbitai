from fastapi import APIRouter

from app.modules.auth.auth_routers import router
from app.modules.health.health_routers import router as health_router
from app.modules.role.role_routers import router as role_router
from app.modules.department.department_routers import router as department_router
from app.modules.project.project_routers import router as project_router
from app.modules.task.task_routers import router as task_router, report_router
from app.modules.user.user_routers import user_router
from app.modules.meeting.meeting_routers import router as meeting_router

api_router = APIRouter(prefix= "/api/v1")


api_router.include_router(router)
api_router.include_router(health_router)
api_router.include_router(role_router)
api_router.include_router(department_router)
api_router.include_router(project_router)
api_router.include_router(task_router)
api_router.include_router(report_router)
api_router.include_router(user_router)
api_router.include_router(meeting_router)