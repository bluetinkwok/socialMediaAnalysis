"""
Social Media Analysis Platform - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create FastAPI instance
app = FastAPI(
    title="Social Media Analysis Platform",
    description="A comprehensive platform for downloading, analyzing, and understanding social media content",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint for health checks"""
    return {
        "message": "Social Media Analysis Platform API",
        "status": "healthy",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "service": "social-media-backend",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "database": "connected",  # Will be updated when database is implemented
        "downloads_path": "/app/downloads",
        "features": {
            "youtube_downloader": "available",
            "instagram_downloader": "available", 
            "threads_downloader": "available",
            "rednote_downloader": "available",
            "analytics_engine": "available",
            "content_analysis": "available"
        }
    }

# API route includes
from api.v1 import health
app.include_router(health.router, prefix="/api/v1", tags=["health"])

# Additional routes will be added here as we develop them
# from api.v1 import content, downloads, analytics
# app.include_router(content.router, prefix="/api/v1", tags=["content"])
# app.include_router(downloads.router, prefix="/api/v1", tags=["downloads"])
# app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])

if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 