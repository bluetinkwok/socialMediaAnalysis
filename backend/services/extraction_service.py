"""
Content Extraction Service

Main service for orchestrating content extraction from various social media platforms.
Manages download jobs, file storage, and database integration.
"""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse

from sqlalchemy.orm import Session
from fastapi import HTTPException, BackgroundTasks

from core.config import settings
from db.database import get_db_session
from db.models import DownloadJob, Post, MediaFile, Platform
from db.schemas import DownloadJobCreate, DownloadJobUpdate, DownloadStatus, PlatformType
from services.base_extractor import BaseContentExtractor
from services.rate_limiter import RateLimiter


class ContentExtractionService:
    """
    Main service for content extraction from social media platforms.
    
    Handles job creation, status tracking, file management, and database operations.
    """
    
    def __init__(self):
        """Initialize the extraction service"""
        # Initialize downloads directory
        self.downloads_dir = Path(settings.downloads_path)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        
        # Create platform-specific directories
        self._create_platform_directories()
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter()
        
        # Store active jobs
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
    
    def _create_platform_directories(self) -> None:
        """Create directory structure for each platform"""
        platforms = ["youtube", "instagram", "threads", "rednote"]
        content_types = ["videos", "images", "text"]
        
        for platform in platforms:
            platform_dir = self.downloads_dir / platform
            platform_dir.mkdir(exist_ok=True)
            
            for content_type in content_types:
                content_dir = platform_dir / content_type
                content_dir.mkdir(exist_ok=True)


# Global instance
content_extraction_service = ContentExtractionService()
