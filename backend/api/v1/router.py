"""
Main API router for v1 endpoints
"""

from fastapi import APIRouter
from .auth import router as auth_router
from .platforms import router as platforms_router
from .posts import router as posts_router
from .analytics import router as analytics_router
from .downloads import router as downloads_router
from .uploads import router as uploads_router
from .security import router as security_router
from .websocket import router as websocket_router
from .metrics import router as metrics_router
from .nlp import router as nlp_router
from .cv import router as cv_router
from .health import router as health_router
from .success_patterns import router as patterns_router
from .audit import router as audit_router
from .security_monitoring import router as security_monitoring_router
from .youtube import router as youtube_router

# Main router for v1 API
router = APIRouter(prefix="/v1")

# Include all sub-routers
router.include_router(auth_router)
router.include_router(platforms_router)
router.include_router(posts_router)
router.include_router(analytics_router)
router.include_router(downloads_router)
router.include_router(uploads_router)
router.include_router(security_router)
router.include_router(websocket_router)
router.include_router(metrics_router)
router.include_router(nlp_router)
router.include_router(cv_router)
router.include_router(health_router)
router.include_router(patterns_router)
router.include_router(audit_router)
router.include_router(security_monitoring_router)
router.include_router(youtube_router)
