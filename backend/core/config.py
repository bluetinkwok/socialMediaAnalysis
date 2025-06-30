"""
Application Configuration

This module provides configuration settings for the application.
"""

import os
from typing import List, Set, Dict, Any, Optional
from functools import lru_cache
from pathlib import Path
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    """Application settings"""
    
    # Base settings
    app_name: str = "Social Media Analysis Platform"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # API settings
    api_prefix: str = "/api"
    api_version: str = "v1"
    
    # Security settings
    secret_key: str = "your-secret-key-here"  # Should be overridden in .env
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # File upload settings
    upload_dir: str = "uploads"
    allowed_file_extensions: Set[str] = {
        "jpg", "jpeg", "png", "gif", "bmp", "webp",  # Images
        "mp4", "mov", "avi", "webm",                 # Videos
        "mp3", "wav", "ogg",                         # Audio
        "pdf", "doc", "docx", "xls", "xlsx",         # Documents
        "txt", "csv", "json", "xml"                  # Data files
    }
    allowed_mime_types: Set[str] = {
        # Images
        "image/jpeg", "image/png", "image/gif", "image/bmp", "image/webp",
        # Videos
        "video/mp4", "video/quicktime", "video/x-msvideo", "video/webm",
        # Audio
        "audio/mpeg", "audio/wav", "audio/ogg",
        # Documents
        "application/pdf", 
        "application/msword", 
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        # Data files
        "text/plain", "text/csv", "application/json", "application/xml"
    }
    max_file_size_mb: int = 100
    
    # Security component settings
    clamav_socket_path: str = "/var/run/clamav/clamd.sock"
    clamav_timeout: int = 30
    yara_rules_path: str = "security/rules"
    security_log_path: str = "logs/security.log"
    
    # Rate limiting
    rate_limit_uploads: int = 10  # uploads per minute
    
    # Database settings
    database_url: str = "sqlite:///./app.db"
    
    @validator("upload_dir")
    def create_upload_dir(cls, v):
        """Ensure upload directory exists"""
        os.makedirs(v, exist_ok=True)
        return v
    
    @validator("yara_rules_path")
    def validate_yara_rules_path(cls, v):
        """Validate YARA rules path"""
        rules_dir = Path(v)
        if not rules_dir.exists():
            os.makedirs(v, exist_ok=True)
        return v
    
    @validator("security_log_path")
    def validate_security_log_path(cls, v):
        """Validate security log path"""
        log_path = Path(v)
        log_dir = log_path.parent
        if not log_dir.exists():
            os.makedirs(log_dir, exist_ok=True)
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings.
    
    Returns:
        Settings: Application settings
    """
    return Settings()
