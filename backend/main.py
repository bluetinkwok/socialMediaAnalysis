"""
Main Application

This module initializes and configures the FastAPI application.
"""

import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.security_headers import add_security_middleware
from core.error_handlers import add_error_handlers
from api.upload import router as upload_router
from api.v1.auth import router as auth_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API for Social Media Analysis Platform with advanced security features",
)

# Define allowed origins based on environment
allowed_origins = settings.cors_allowed_origins.split(",") if settings.cors_allowed_origins else ["http://localhost:3000"]
if settings.debug:
    # In debug mode, allow development origins
    allowed_origins.extend(["http://localhost:3000", "http://localhost:8080"])

# Add CORS middleware with restricted configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Content-Type", 
        "Authorization", 
        "X-Requested-With",
        "Accept",
        "Origin",
        "X-Session-ID",
        "X-CSRF-Token",
    ],
    expose_headers=[
        "Content-Length",
        "X-CSRF-Token",
    ],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Add security middleware
add_security_middleware(app)

# Add custom error handlers
add_error_handlers(app)

# Include routers
app.include_router(upload_router, prefix=f"{settings.api_prefix}/{settings.api_version}")
app.include_router(auth_router, prefix=f"{settings.api_prefix}/{settings.api_version}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "api_prefix": f"{settings.api_prefix}/{settings.api_version}"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
