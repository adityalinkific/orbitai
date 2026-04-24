from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, status
from app.core.config import settings
from app.modules.orbit_assistant.engine.logger import get_logger

log = get_logger("rate_limit")

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],
    storage_uri="memory://",  # Use Redis in production: "redis://localhost:6379"
)


def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded."""
    log.warning(f"Rate limit exceeded for {request.client.host}: {exc.detail}")
    
    return {
        "status": "error",
        "success": False,
        "message": "Rate limit exceeded. Please slow down your requests.",
        "error_code": "RATE_LIMIT_EXCEEDED"
    }
