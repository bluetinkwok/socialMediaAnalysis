"""
Main API router that includes all v1 endpoints
"""

from fastapi import APIRouter

from .health import router as health_router
from .platforms import router as platforms_router
from .posts import router as posts_router
from .downloads import router as downloads_router
from .websocket import router as websocket_router
from .analytics import router as analytics_router
from .success_patterns import router as success_patterns_router
from .security import router as security_router
from .uploads import router as uploads_router
from .youtube import router as youtube_router
# from .extraction import router as extraction_router  # Temporarily disabled

# Create main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(platforms_router, prefix="/platforms", tags=["platforms"])
api_router.include_router(posts_router, prefix="/posts", tags=["posts"])
api_router.include_router(downloads_router, prefix="/downloads", tags=["downloads"])
api_router.include_router(websocket_router, tags=["websocket"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_router.include_router(success_patterns_router, tags=["success-patterns"])
api_router.include_router(security_router, tags=["security"])
api_router.include_router(uploads_router, prefix="/uploads", tags=["uploads"])
api_router.include_router(youtube_router, prefix="/youtube", tags=["youtube"])

# Additional routers will be added as we develop them:
# from . import extraction
