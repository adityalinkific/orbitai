from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
import logging
from app.core.schema import Response


logger = logging.getLogger(__name__)


# Convert FastAPI validation errors into a human-readable message
def _format_validation_error(exc: RequestValidationError) -> str:
    errors = []
    for err in exc.errors():
        field = err["loc"][-1]
        message = err["msg"]
        errors.append(f"{field}: {message}")
    return ", ".join(errors)


async def custom_request_validation_exception_handler(request: Request, exc: RequestValidationError):
    message = _format_validation_error(exc)

    return JSONResponse(
        status_code=422,
        content= await Response._error_response("validation error", message)
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content= await Response._error_response(exc.detail)
    )


async def response_validation_exception_handler(
    request: Request,
    exc: ResponseValidationError
):
    logger.error(exc)
    return JSONResponse(
        status_code=500,
        content= await Response._error_response("Response validation failed")
    )


async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(exc)

    return JSONResponse(
        status_code=500,
        content= await Response._error_response("Internal server error")
    )
