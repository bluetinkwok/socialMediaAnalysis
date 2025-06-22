"""
Social Media Analysis Platform - FastAPI Backend
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import uvicorn

# Import database components
from db.database import ensure_database_exists, get_database_info, get_database
from db.models import Platform
from db.schemas import ApiResponse, OverallStats
from core.config import get_settings

# Import API routes
from api.v1.router import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting Social Media Analysis Platform")
    try:
        # Ensure database exists and is initialized
        ensure_database_exists()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Social Media Analysis Platform")


# Create FastAPI application
app = FastAPI(
    title="Social Media Analysis Platform",
    description="A comprehensive platform for downloading, analyzing, and understanding successful social media content",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/", response_model=ApiResponse)
async def root():
    """Root endpoint with API information"""
    return ApiResponse(
        success=True,
        message="Social Media Analysis Platform API",
        data={
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "api": "/api/v1"
        }
    )


# Health check endpoint
@app.get("/health", response_model=ApiResponse)
async def health_check(db=Depends(get_database)):
    """Health check endpoint"""
    try:
        # Test database connection
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        
        # Get basic database info
        platform_count = db.query(Platform).count()
        
        return ApiResponse(
            success=True,
            message="Service is healthy",
            data={
                "status": "healthy",
                "database": "connected",
                "platforms_configured": platform_count
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return ApiResponse(
            success=False,
            message="Service is unhealthy",
            error=str(e)
        )


# Database info endpoint
@app.get("/database/info", response_model=ApiResponse)
async def database_info():
    """Get database information"""
    try:
        info = get_database_info()
        return ApiResponse(
            success=True,
            message="Database information retrieved",
            data=info
        )
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve database information"
        )


# Statistics endpoint
@app.get("/stats", response_model=ApiResponse)
async def get_stats(db=Depends(get_database)):
    """Get overall platform statistics"""
    try:
        from db.models import Post, MediaFile, DownloadJob
        
        # Get basic counts
        total_posts = db.query(Post).count()
        total_files = db.query(MediaFile).count()
        total_downloads = db.query(DownloadJob).count()
        active_platforms = db.query(Platform).filter(Platform.is_active == True).count()
        
        # Get recent activity (last 10 posts)
        recent_posts = db.query(Post).order_by(Post.created_at.desc()).limit(10).all()
        
        stats = {
            "total_posts": total_posts,
            "total_files": total_files,
            "total_downloads": total_downloads,
            "active_platforms": active_platforms,
            "recent_activity": [
                {
                    "id": post.id,
                    "title": post.title[:50] + "..." if len(post.title) > 50 else post.title,
                    "platform": post.platform.value,
                    "author": post.author,
                    "created_at": post.created_at.isoformat()
                }
                for post in recent_posts
            ]
        }
        
        return ApiResponse(
            success=True,
            message="Statistics retrieved successfully",
            data=stats
        )
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "message": "Endpoint not found",
            "error": "The requested resource was not found"
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error": "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 