from typing import Generic, TypeVar, Any
from pydantic.generics import GenericModel

T = TypeVar("T")


class ApiResponse(GenericModel, Generic[T]):
    status: str
    message: str
    data: T


class Response:
    @staticmethod
    async def _success_response(message: str, data = None):
        return {
            'status' : 'success',
            'message' : str(message).capitalize(),
            'data' : data
        }
        
    @staticmethod
    async def _error_response(message: Any, data = None):
        return {
            'status' : 'error',
            'message' : str(message).capitalize(),
            'data' : data
        }