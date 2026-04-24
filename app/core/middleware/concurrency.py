import asyncio
from typing import Callable, Any, Optional
from fastapi import Request, HTTPException, status
from app.modules.orbit_assistant.engine.logger import get_logger

log = get_logger("concurrency")


class ConcurrencyLimiter:
    """Limit concurrent requests per user to prevent abuse."""
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.user_semaphores: dict[int, asyncio.Semaphore] = {}
        self.lock = asyncio.Lock()
    
    async def acquire(self, user_id: int):
        """Acquire a slot for the user."""
        async with self.lock:
            if user_id not in self.user_semaphores:
                self.user_semaphores[user_id] = asyncio.Semaphore(self.max_concurrent)
        
        semaphore = self.user_semaphores[user_id]
        acquired = await semaphore.acquire()
        
        if not acquired:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many concurrent requests. Please wait and try again."
            )
        
        return semaphore
    
    async def release(self, user_id: int, semaphore: asyncio.Semaphore):
        """Release a slot for the user."""
        semaphore.release()
        
        # Clean up if no more users
        async with self.lock:
            if semaphore._value == self.max_concurrent:
                self.user_semaphores.pop(user_id, None)


# Global concurrency limiter
concurrency_limiter = ConcurrencyLimiter(max_concurrent=5)


async def with_concurrency_limit(user_id: int, func: Callable, *args, **kwargs) -> Any:
    """Execute a function with concurrency limiting."""
    semaphore = await concurrency_limiter.acquire(user_id)
    try:
        return await func(*args, **kwargs)
    finally:
        await concurrency_limiter.release(user_id, semaphore)
