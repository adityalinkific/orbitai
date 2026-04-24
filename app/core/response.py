"""
Standard Response Serializer for Enterprise Service Layer

Enforces single response format across all services:
Response(success: bool, message: str, data: Any)
"""

from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field
from datetime import datetime


class Response(BaseModel):
    """
    Standard response format for all service operations.
    
    Format:
    {
        "success": bool,
        "message": str,
        "data": Any
    }
    """
    success: bool = Field(..., description="Indicates if the operation was successful")
    message: str = Field(..., description="Human-readable message describing the result")
    data: Any = Field(default=None, description="Response data payload")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {"id": 1}
            }
        }


class ResponseBuilder:
    """Builder for creating standardized responses."""
    
    @staticmethod
    def success(message: str, data: Any = None) -> Response:
        """Create a success response."""
        return Response(success=True, message=message, data=data)
    
    @staticmethod
    def error(message: str, data: Any = None) -> Response:
        """Create an error response."""
        return Response(success=False, message=message, data=data)
    
    @staticmethod
    def not_found(resource: str, identifier: Any = None) -> Response:
        """Create a not found error response."""
        if identifier:
            return Response(success=False, message=f"{resource} with identifier '{identifier}' not found", data=None)
        return Response(success=False, message=f"{resource} not found", data=None)
    
    @staticmethod
    def validation_error(message: str, errors: Any = None) -> Response:
        """Create a validation error response."""
        return Response(success=False, message=message, data=errors)
    
    @staticmethod
    def conflict(message: str, data: Any = None) -> Response:
        """Create a conflict error response."""
        return Response(success=False, message=message, data=data)
    
    @staticmethod
    def unauthorized(message: str = "Unauthorized access") -> Response:
        """Create an unauthorized error response."""
        return Response(success=False, message=message, data=None)
    
    @staticmethod
    def forbidden(message: str = "Access forbidden") -> Response:
        """Create a forbidden error response."""
        return Response(success=False, message=message, data=None)
    
    @staticmethod
    def internal_error(message: str = "Internal server error") -> Response:
        """Create an internal server error response."""
        return Response(success=False, message=message, data=None)


def to_dict(response: Response) -> Dict[str, Any]:
    """Convert Response to dictionary."""
    return response.model_dump()


def success(message: str, data: Any = None) -> Dict[str, Any]:
    """Quick success response shortcut."""
    return to_dict(ResponseBuilder.success(message, data))


def error(message: str, data: Any = None) -> Dict[str, Any]:
    """Quick error response shortcut."""
    return to_dict(ResponseBuilder.error(message, data))


def not_found(resource: str, identifier: Any = None) -> Dict[str, Any]:
    """Quick not found response shortcut."""
    return to_dict(ResponseBuilder.not_found(resource, identifier))


def validation_error(message: str, errors: Any = None) -> Dict[str, Any]:
    """Quick validation error response shortcut."""
    return to_dict(ResponseBuilder.validation_error(message, errors))


def conflict(message: str, data: Any = None) -> Dict[str, Any]:
    """Quick conflict response shortcut."""
    return to_dict(ResponseBuilder.conflict(message, data))


def unauthorized(message: str = "Unauthorized access") -> Dict[str, Any]:
    """Quick unauthorized response shortcut."""
    return to_dict(ResponseBuilder.unauthorized(message))


def forbidden(message: str = "Access forbidden") -> Dict[str, Any]:
    """Quick forbidden response shortcut."""
    return to_dict(ResponseBuilder.forbidden(message))


def internal_error(message: str = "Internal server error") -> Dict[str, Any]:
    """Quick internal error response shortcut."""
    return to_dict(ResponseBuilder.internal_error(message))
