"""
ORBIT Global Error Handler
Provides centralized error handling for the application.
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
import traceback as tb

async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for all unhandled exceptions."""
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

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler for HTTP exceptions."""
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
