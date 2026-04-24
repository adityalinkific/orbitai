"""
ORBIT Assistant Error Handler
Provides centralized error handling for assistant operations.
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import traceback as tb
from app.modules.orbit_assistant.engine.logger import get_logger

log = get_logger("assistant_error_handler")


async def assistant_exception_handler(request: Request, exc: Exception):
    """Global exception handler for assistant operations."""
    log.exception(f"Assistant error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        },
    )


def handle_execution_error(exc: Exception) -> dict:
    """Handle execution errors from the executor."""
    log.exception(f"Executor error: {str(exc)}")
    return {
        "success": False,
        "error": str(exc),
        "error_type": type(exc).__name__,
    }
