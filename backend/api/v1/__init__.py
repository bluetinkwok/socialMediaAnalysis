"""
API v1 Router Module

This module initializes the API v1 router and includes all API endpoints.
"""

from fastapi import APIRouter

from api.v1 import audit, metrics, security_monitoring

# Create main API router
api_router = APIRouter()

# Include all API routers
api_router.include_router(audit.router)
api_router.include_router(metrics.router)
api_router.include_router(security_monitoring.router)
