"""
API Router Module

This module initializes the main API router and includes all API versions.
"""

from fastapi import APIRouter

from api.v1 import api_router as api_v1_router

# Create main API router
api_router = APIRouter()

# Include API versions
api_router.include_router(api_v1_router, prefix="/v1")
