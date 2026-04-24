from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.dependency import get_db
from app.modules.health.health_controller import Health

router = APIRouter(prefix= '/system', tags= ['System'])

@router.get("/health")
async def system_health(db: AsyncSession = Depends(get_db)):
    """System health check endpoint."""
    # Check database connection
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"
    
    return {
        "assistant": "healthy",
        "database": db_status,
        "email": "ready",
        "nlu": "active",
        "routes": "loaded",
        "status": "operational"
    }

@router.get("/health-check")
async def users(db: AsyncSession = Depends(get_db)):
    return await Health.health_check(db)