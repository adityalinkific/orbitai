import asyncio
from typing import Callable, Any, Optional
from app.modules.orbit_assistant.engine.logger import get_logger

log = get_logger("timeout")


async def with_timeout(
    func: Callable,
    timeout_seconds: float,
    *args,
    **kwargs
) -> Any:
    """
    Execute an async function with a timeout.
    
    Args:
        func: Async function to execute
        timeout_seconds: Timeout in seconds
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function
    
    Returns:
        Result of the function
    
    Raises:
        asyncio.TimeoutError: If function doesn't complete within timeout
    """
    try:
        return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        log.error(f"Function {func.__name__} timed out after {timeout_seconds}s")
        raise


class TimeoutContext:
    """Context manager for timeout operations."""
    
    def __init__(self, timeout_seconds: float):
        self.timeout_seconds = timeout_seconds
        self._task: Optional[asyncio.Task] = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        return False
    
    async def run(self, func: Callable, *args, **kwargs) -> Any:
        """Run a function with timeout."""
        self._task = asyncio.create_task(func(*args, **kwargs))
        try:
            return await with_timeout(lambda: self._task, self.timeout_seconds)
        finally:
            self._task = None
