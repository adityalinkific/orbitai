from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    status: str
    message: str
    data: T


class Response:
    @staticmethod
    async def _success_response(message: str, data = None):
        return {
            'status' : 'success',
            'message' : message.capitalize(),
            'data' : data
        }

    @staticmethod
    async def _error_response(message: str, data = None):
        return {
            'status' : 'error',
            'message' : message.capitalize(),
            'data' : data
        }