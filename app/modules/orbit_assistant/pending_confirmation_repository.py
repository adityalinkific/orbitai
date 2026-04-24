from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.modules.orbit_assistant.pending_confirmation_model import PendingConfirmation
from app.core.base_repository import BaseRepository


class PendingConfirmationRepository(BaseRepository):
    """Repository for pending confirmation operations."""
    
    async def create_confirmation(
        self,
        db: AsyncSession,
        request_id: str,
        intent: str,
        entity: str,
        user_id: int,
        payload: Dict[str, Any],
        expires_at: datetime
    ) -> PendingConfirmation:
        """Create a new pending confirmation."""
        import json
        
        confirmation = PendingConfirmation(
            request_id=request_id,
            intent=intent,
            entity=entity,
            user_id=user_id,
            payload=json.dumps(payload) if payload else None,
            status="pending",
            expires_at=expires_at
        )
        
        return await self.create(db, confirmation)
    
    async def get_confirmation(
        self,
        db: AsyncSession,
        request_id: str
    ) -> Optional[PendingConfirmation]:
        """Get a confirmation by request_id."""
        result = await db.execute(
            select(PendingConfirmation).where(PendingConfirmation.request_id == request_id)
        )
        return result.scalar_one_or_none()
    
    async def confirm_confirmation(
        self,
        db: AsyncSession,
        request_id: str
    ) -> bool:
        """Mark a confirmation as confirmed."""
        confirmation = await self.get_confirmation(db, request_id)
        if not confirmation:
            return False
        
        if confirmation.status != "pending":
            return False
        
        if confirmation.expires_at < datetime.utcnow():
            confirmation.status = "expired"
            await db.commit()
            return False
        
        confirmation.status = "confirmed"
        await db.commit()
        return True
    
    async def cancel_confirmation(
        self,
        db: AsyncSession,
        request_id: str
    ) -> bool:
        """Cancel a confirmation."""
        confirmation = await self.get_confirmation(db, request_id)
        if not confirmation:
            return False
        
        confirmation.status = "cancelled"
        await db.commit()
        return True
    
    async def cleanup_expired_confirmations(
        self,
        db: AsyncSession
    ) -> int:
        """Delete expired confirmations older than 24 hours."""
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        result = await db.execute(
            delete(PendingConfirmation).where(
                and_(
                    PendingConfirmation.expires_at < cutoff,
                    PendingConfirmation.status.in_(["expired", "cancelled"])
                )
            )
        )
        await db.commit()
        return result.rowcount
    
    async def get_user_confirmations(
        self,
        db: AsyncSession,
        user_id: int,
        limit: int = 10
    ) -> list[PendingConfirmation]:
        """Get recent confirmations for a user."""
        result = await db.execute(
            select(PendingConfirmation)
            .where(PendingConfirmation.user_id == user_id)
            .order_by(PendingConfirmation.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
