"""
Session Validation Middleware
Validates session_id format and ensures proper UUID structure.
"""
import uuid
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


def is_valid_uuid(value: any) -> bool:
    """Check if value is a valid UUID v4 string or UUID object."""
    if not value:
        return False
    try:
        if isinstance(value, uuid.UUID):
            return True
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError):
        return False


class SessionValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate session_id format in requests.
    Ensures only valid UUID v4 format session_ids are accepted.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Only validate endpoints that use session_id
        if request.url.path.startswith("/api/v1/assistant/chat"):
            try:
                body = await request.body()
                
                # Parse JSON body to check session_id
                if body:
                    import json
                    try:
                        data = json.loads(body.decode())
                        session_id = data.get("session_id")
                        
                        # If session_id is provided, validate it
                        if session_id and not is_valid_uuid(session_id):
                            logger.warning(f"Invalid session_id format: {session_id}")
                            return JSONResponse(
                                status_code=400,
                                content={
                                    "status": "error",
                                    "success": False,
                                    "message": "Invalid session_id format. Expected UUID v4 format.",
                                    "error": "INVALID_SESSION_ID_FORMAT"
                                }
                            )
                    except json.JSONDecodeError:
                        pass  # Body is not JSON, skip validation
                        
            except Exception as e:
                logger.error(f"Session validation error: {e}")
                # Continue with request even if validation fails
        
        response = await call_next(request)
        return response
