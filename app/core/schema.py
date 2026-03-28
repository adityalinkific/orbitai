from typing import Generic, TypeVar
from pydantic.generics import GenericModel

T = TypeVar("T")


class ApiResponse(GenericModel, Generic[T]):
    status: str
    message: str
    data: T


class Response:
    async def _success_response(message: str, data = None):
        return {
            'status' : 'success',
            'message' : message.capitalize(),
            'data' : data
        }
        
    async def _error_response(message: str, data = None):
        return {
            'status' : 'error',
            'message' : message.capitalize(),
            'data' : data
        }