from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Callable, Any
import asyncio
from app.modules.orbit_assistant.engine.logger import get_logger

log = get_logger("retry")


def with_retry(
    max_attempts: int = 3,
    wait_min: float = 1.0,
    wait_max: float = 10.0,
    exceptions: tuple = (Exception,),
):
    """
    Decorator to add retry logic to async functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        wait_min: Minimum wait time between retries (exponential backoff)
        wait_max: Maximum wait time between retries
        exceptions: Tuple of exceptions to retry on
    """
    def decorator(func: Callable):
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
            retry=retry_if_exception_type(exceptions),
            reraise=True
        )
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                log.error(f"Retry failed for {func.__name__}: {str(e)}")
                raise
        return wrapper
    return decorator


async def retry_async(
    func: Callable,
    *args,
    max_attempts: int = 3,
    wait_min: float = 1.0,
    wait_max: float = 10.0,
    exceptions: tuple = (Exception,),
    **kwargs
) -> Any:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_attempts: Maximum number of retry attempts
        wait_min: Minimum wait time between retries
        wait_max: Maximum wait time between retries
        exceptions: Tuple of exceptions to retry on
    """
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            return await func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            if attempt < max_attempts - 1:
                wait_time = min(wait_min * (2 ** attempt), wait_max)
                log.warning(f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                log.error(f"All {max_attempts} attempts failed for {func.__name__}")
    
    raise last_exception
