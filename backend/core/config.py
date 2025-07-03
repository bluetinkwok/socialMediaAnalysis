"""
Configuration settings for Social Media Analysis Platform
"""

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./social_media_analysis.db")
    
    # API settings
    API_V1_STR: str = "/api/v1"
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev_secret_key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Monitoring settings
    MONITORING_CHECK_INTERVAL: int = 60  # seconds

    class Config:
        case_sensitive = True

# Create settings instance
settings = Settings()
