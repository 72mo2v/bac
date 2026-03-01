from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.core.config import settings
from app.core.middleware import RequestContextMiddleware
from app.core.security_middleware import SecurityHeadersMiddleware
from app.core.exceptions import AppException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.event_handlers import setup_event_handlers
from app.background.scheduler import setup_scheduler, shutdown_scheduler

setup_event_handlers()

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.on_event("startup")
async def startup_event():
    setup_scheduler()

@app.on_event("shutdown")
def shutdown_event():
    shutdown_scheduler()

# Set all CORS enabled origins
origins = [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]
# Explicitly add common dev origins for convenience
origins.extend([
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
])

if not origins:
    origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



from fastapi.exceptions import RequestValidationError
import logging

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logging.error(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"success": False, "detail": exc.errors()}
    )

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        },
    )

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": "1.0.0"
    }

# Include API V1 router
from app.api.v1.router import api_router
from app.modules.notifications.routers.websocket_router import router as websocket_router

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(websocket_router)

uploads_dir = Path(__file__).resolve().parents[1] / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

