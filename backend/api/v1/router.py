"""
Main API router that includes all v1 endpoints
"""

from fastapi import APIRouter

from .health import router as health_router
from .platforms import router as platforms_router
from .posts import router as posts_router
from .downloads import router as downloads_router
# from .extraction import router as extraction_router  # Temporarily disabled

# Create main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(platforms_router, prefix="/platforms", tags=["platforms"])
api_router.include_router(posts_router, prefix="/posts", tags=["posts"])
api_router.include_router(downloads_router, prefix="/downloads", tags=["downloads"])

# Additional routers will be added as we develop them:
# from . import analytics
