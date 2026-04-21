from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from app.routers import api_router
from app.modules.orbit_assistant.router import router as assistant_router
import app.models
from app.core.middleware.error_handlers import http_exception_handler, response_validation_exception_handler, global_exception_handler, custom_request_validation_exception_handler
from app.core.middleware.cors_middleware import register_cors
from app.core.config import settings
from app.modules.orbit_assistant.engine.logger import get_logger
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

log = get_logger("main")

app = FastAPI(
        title= settings.APP_NAME,
        version= settings.APP_VERSION,
        description="Backend Management System",
        contact={
            "name": "API Support",
            "url": "mailto:support@orbit.dev",
        },
        license_info={
            "name": "Proprietary- Internal Use Only",
            'url': "https://demo.com"
        },
    )

register_cors(app)

# Global Error Handling Middleware
@app.middleware("http")
async def error_guard(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        log.exception(f"Unhandled error in request: {request.url}")
        raise

app.add_exception_handler(RequestValidationError, custom_request_validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(ResponseValidationError, response_validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.include_router(api_router)
app.include_router(assistant_router)

@app.on_event("startup")
async def startup_db_check():
    """Database health check on application startup."""
    try:
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
        await engine.dispose()
        log.info("Database health check: PASSED - Database connected successfully")
    except Exception as e:
        log.error(f"Database health check: FAILED - {str(e)}")
        raise RuntimeError(f"Database connection failed: {str(e)}")

@app.get("/")
def root():
    return {
        "status" : "success",
        "message" : "Orbit API Running Successfully!"
    }
