from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependency import get_db, get_current_user
from app.modules.orbit_assistant.assistant_service import assistant_service
from app.modules.orbit_assistant.schemas import ChatRequest

router = APIRouter(prefix="/assistant", tags=["Orbit Assistant"])


@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Process an Orbit Assistant command.
    Delegates all logic to assistant_service (Phase 5 Cleanup).
    """
    return await assistant_service.chat(
        request=request,
        db=db,
        current_user=current_user,
    )