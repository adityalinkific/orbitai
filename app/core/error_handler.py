"""
ORBIT Global Error Handler
Provides centralized error handling for the application.
Enhanced with assistant-specific error logging and context.
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
import traceback as tb
import logging

log = logging.getLogger("error_handler")

async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for all unhandled exceptions."""
    # Log full error context
    log.error(
        f"Unhandled exception: {type(exc).__name__}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc),
            "traceback": tb.format_exc()
        }
    )
    
    # Return safe error message (don't expose internals)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "An internal server error occurred. Please try again later.",
            "error_type": "InternalServerError",
            "path": request.url.path,
            "method": request.method,
        },
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler for HTTP exceptions."""
    log.warning(
        f"HTTP exception: {exc.status_code}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "detail": exc.detail
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "error_type": "HTTPException",
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
        },
    )

async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler for request validation errors."""
    log.warning(
        f"Request validation failed",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors()
        }
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "Request validation failed",
            "error_type": "RequestValidationError",
            "details": exc.errors(),
            "path": request.url.path,
            "method": request.method,
        },
    )

async def response_validation_exception_handler(request: Request, exc: ResponseValidationError):
    """Handler for response validation errors."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Response validation failed",
            "error_type": "ResponseValidationError",
            "details": exc.errors(),
            "path": request.url.path,
            "method": request.method,
        },
    )
