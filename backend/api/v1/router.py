"""
API v1 Router - Main router for API version 1
"""

from fastapi import APIRouter

# Import individual route modules
from . import health, platforms

# Create main API router
api_router = APIRouter()

# Include individual routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(platforms.router, prefix="/platforms", tags=["platforms"])

# Additional routers will be added as we develop them:
# from . import posts, downloads, analytics
# api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
# api_router.include_router(downloads.router, prefix="/downloads", tags=["downloads"])
# api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"]) 