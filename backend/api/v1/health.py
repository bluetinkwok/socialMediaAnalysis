"""
Health check API endpoints
"""

from fastapi import APIRouter, Depends
from core.config import get_settings, Settings
import os
import time

router = APIRouter()


@router.get("/health")
async def health_check(settings: Settings = Depends(get_settings)):
    """Comprehensive health check endpoint"""
    
    # Check if downloads directory exists
    downloads_exist = os.path.exists(settings.downloads_path)
    
    # Check if data directory exists (for database)
    data_dir = os.path.dirname(settings.database_url.replace("sqlite:///", ""))
    data_dir_exists = os.path.exists(data_dir) if data_dir != "." else True
    
    return {
        "status": "healthy",
        "timestamp": int(time.time()),
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "checks": {
            "downloads_directory": "ok" if downloads_exist else "missing",
            "data_directory": "ok" if data_dir_exists else "missing",
            "configuration": "loaded"
        },
        "features": {
            "youtube_downloader": "available",
            "instagram_downloader": "available", 
            "threads_downloader": "available",
            "rednote_downloader": "available",
            "analytics_engine": "available",
            "content_analysis": "available"
        }
    }


@router.get("/ping")
async def ping():
    """Simple ping endpoint for basic connectivity checks"""
    return {"message": "pong", "timestamp": int(time.time())} 