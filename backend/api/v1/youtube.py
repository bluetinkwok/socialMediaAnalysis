"""
YouTube-specific API endpoints for downloading videos, thumbnails, metadata, and transcripts
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
import uuid
from pydantic import BaseModel, Field, HttpUrl, validator

from db.database import get_database
from db.models import PlatformType, ContentType, DownloadStatus
from db.schemas import ApiResponse
from services.youtube_downloader import YouTubeDownloader
from services.progress_tracker import ProgressTracker, DatabaseProgressCallback, LoggingProgressCallback
from services.websocket_manager import websocket_manager, WebSocketProgressCallback
from core.security import url_validator, malicious_url_detector


# Pydantic models for YouTube API
class YouTubeDownloadRequest(BaseModel):
    """Request schema for YouTube video download"""
    url: str = Field(..., description="YouTube video URL")
    quality: str = Field("medium", description="Video quality (low, medium, high, best)")
    format_id: Optional[str] = Field(None, description="Specific format ID to download")
    include_subtitles: bool = Field(True, description="Whether to download subtitles if available")
    include_thumbnail: bool = Field(True, description="Whether to download thumbnail")
    
    @validator('quality')
    def validate_quality(cls, v):
        allowed_values = ['low', 'medium', 'high', 'best']
        if v.lower() not in allowed_values:
            raise ValueError(f"Quality must be one of: {', '.join(allowed_values)}")
        return v.lower()
    
    @validator('url')
    def validate_url(cls, v):
        if not url_validator(v):
            raise ValueError("Invalid URL format")
        if malicious_url_detector(v):
            raise ValueError("URL flagged as potentially malicious")
        return v


class YouTubeFormatInfo(BaseModel):
    """Format information for YouTube video"""
    format_id: str
    ext: str
    resolution: str
    filesize: Optional[int] = None
    filesize_approx: Optional[int] = None
    fps: Optional[int] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    format_note: Optional[str] = None


class YouTubeInfoRequest(BaseModel):
    """Request schema for fetching YouTube video information"""
    url: str = Field(..., description="YouTube video URL")
    
    @validator('url')
    def validate_url(cls, v):
        if not url_validator(v):
            raise ValueError("Invalid URL format")
        if malicious_url_detector(v):
            raise ValueError("URL flagged as potentially malicious")
        return v


class YouTubeBatchRequest(BaseModel):
    """Request schema for batch YouTube operations"""
    urls: List[str] = Field(..., min_items=1, max_items=50, description="List of YouTube URLs")
    quality: str = Field("medium", description="Video quality (low, medium, high, best)")
    
    @validator('quality')
    def validate_quality(cls, v):
        allowed_values = ['low', 'medium', 'high', 'best']
        if v.lower() not in allowed_values:
            raise ValueError(f"Quality must be one of: {', '.join(allowed_values)}")
        return v.lower()
    
    @validator('urls', each_item=True)
    def validate_urls(cls, v):
        if not url_validator(v):
            raise ValueError(f"Invalid URL format: {v}")
        if malicious_url_detector(v):
            raise ValueError(f"URL flagged as potentially malicious: {v}")
        return v


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/validate", response_model=ApiResponse)
async def validate_youtube_url(url: str = Query(..., description="YouTube URL to validate")):
    """
    Validate if a URL is a valid YouTube URL
    
    Returns validation result and extracted video ID if valid
    """
    try:
        downloader = YouTubeDownloader()
        is_valid = downloader.validate_url(url)
        
        if is_valid:
            video_id = downloader._extract_video_id_from_url(url)
            return ApiResponse(
                success=True,
                data={
                    "is_valid": True,
                    "video_id": video_id,
                    "url": url
                },
                message="Valid YouTube URL"
            )
        else:
            return ApiResponse(
                success=True,
                data={
                    "is_valid": False,
                    "url": url
                },
                message="Not a valid YouTube URL"
            )
    
    except Exception as e:
        logger.error(f"Error validating YouTube URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate URL: {str(e)}"
        )


@router.post("/info", response_model=ApiResponse)
async def get_youtube_info(request: YouTubeInfoRequest):
    """
    Get information about a YouTube video without downloading
    
    Returns metadata, available formats, and other information
    """
    try:
        downloader = YouTubeDownloader()
        
        if not downloader.validate_url(request.url):
            return ApiResponse(
                success=False,
                error="Not a valid YouTube URL",
                data={"url": request.url}
            )
        
        # Extract content information
        info = await downloader.extract_content(request.url)
        
        # Check for extraction error
        if 'error' in info:
            return ApiResponse(
                success=False,
                error=f"Failed to extract video information: {info['error']}",
                data={"url": request.url}
            )
        
        return ApiResponse(
            success=True,
            data={
                "video_id": info["video_id"],
                "title": info["title"],
                "description": info["description"],
                "channel": info["channel"],
                "channel_id": info["channel_id"],
                "duration": info["duration"],
                "upload_date": info["upload_date"],
                "view_count": info["view_count"],
                "like_count": info["like_count"],
                "thumbnail_url": info["thumbnail_url"],
                "available_formats": info.get("available_formats", []),
                "subtitles_available": info.get("subtitles_available", []),
                "automatic_captions_available": info.get("automatic_captions_available", [])
            },
            message=f"Successfully retrieved information for video: {info['title']}"
        )
    
    except Exception as e:
        logger.error(f"Error getting YouTube video info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get video information: {str(e)}"
        )


@router.post("/download", response_model=ApiResponse)
async def download_youtube_video(
    request: YouTubeDownloadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database)
):
    """
    Download a YouTube video with specified options
    
    Returns job ID for tracking download progress
    """
    try:
        # Create a downloader instance
        downloader = YouTubeDownloader()
        
        # Validate URL
        if not downloader.validate_url(request.url):
            return ApiResponse(
                success=False,
                error="Not a valid YouTube URL",
                data={"url": request.url}
            )
        
        # Extract video ID for job tracking
        video_id = downloader._extract_video_id_from_url(request.url)
        
        # Create a unique job ID
        job_id = str(uuid.uuid4())
        
        # Create database record for tracking
        from db.models import DownloadJob
        
        download_job = DownloadJob(
            job_id=job_id,
            status=DownloadStatus.PENDING,
            platform=PlatformType.YOUTUBE,
            urls=[request.url],
            download_options={
                "quality": request.quality,
                "format_id": request.format_id,
                "include_subtitles": request.include_subtitles,
                "include_thumbnail": request.include_thumbnail,
                "video_id": video_id
            }
        )
        
        db.add(download_job)
        db.commit()
        db.refresh(download_job)
        
        # Add background task for download
        background_tasks.add_task(
            process_youtube_download,
            job_id=job_id,
            url=request.url,
            quality=request.quality,
            format_id=request.format_id,
            db_id=download_job.id
        )
        
        return ApiResponse(
            success=True,
            data={
                "job_id": job_id,
                "video_id": video_id,
                "url": request.url,
                "quality": request.quality,
                "format_id": request.format_id
            },
            message=f"Download job created for video ID: {video_id}"
        )
    
    except Exception as e:
        logger.error(f"Error initiating YouTube download: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate download: {str(e)}"
        )


@router.post("/batch", response_model=ApiResponse)
async def batch_youtube_download(
    request: YouTubeBatchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database)
):
    """
    Download multiple YouTube videos in batch
    
    Returns job ID for tracking batch download progress
    """
    try:
        # Create a downloader instance to validate URLs
        downloader = YouTubeDownloader()
        
        # Filter valid YouTube URLs
        valid_urls = []
        invalid_urls = []
        
        for url in request.urls:
            if downloader.validate_url(url):
                valid_urls.append(url)
            else:
                invalid_urls.append(url)
        
        if not valid_urls:
            return ApiResponse(
                success=False,
                error="No valid YouTube URLs provided",
                data={"invalid_urls": invalid_urls}
            )
        
        # Create a unique job ID
        job_id = str(uuid.uuid4())
        
        # Create database record for tracking
        from db.models import DownloadJob
        
        download_job = DownloadJob(
            job_id=job_id,
            status=DownloadStatus.PENDING,
            platform=PlatformType.YOUTUBE,
            urls=valid_urls,
            total_items=len(valid_urls),
            download_options={
                "quality": request.quality,
                "batch": True
            }
        )
        
        db.add(download_job)
        db.commit()
        db.refresh(download_job)
        
        # Add background task for batch download
        background_tasks.add_task(
            process_youtube_batch_download,
            job_id=job_id,
            urls=valid_urls,
            quality=request.quality,
            db_id=download_job.id
        )
        
        return ApiResponse(
            success=True,
            data={
                "job_id": job_id,
                "valid_urls": valid_urls,
                "invalid_urls": invalid_urls,
                "total_valid": len(valid_urls),
                "quality": request.quality
            },
            message=f"Batch download job created for {len(valid_urls)} videos"
        )
    
    except Exception as e:
        logger.error(f"Error initiating batch YouTube download: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate batch download: {str(e)}"
        )


@router.get("/formats/{video_id}", response_model=ApiResponse)
async def get_available_formats(
    video_id: str = Path(..., description="YouTube video ID")
):
    """
    Get available formats for a YouTube video
    
    Returns list of available formats with quality information
    """
    try:
        # Construct URL from video ID
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Create downloader and extract content
        downloader = YouTubeDownloader()
        info = await downloader.extract_content(url)
        
        # Check for extraction error
        if 'error' in info:
            return ApiResponse(
                success=False,
                error=f"Failed to extract video information: {info['error']}",
                data={"video_id": video_id}
            )
        
        return ApiResponse(
            success=True,
            data={
                "video_id": video_id,
                "title": info["title"],
                "formats": info.get("available_formats", [])
            },
            message=f"Retrieved {len(info.get('available_formats', []))} available formats"
        )
    
    except Exception as e:
        logger.error(f"Error getting available formats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available formats: {str(e)}"
        )


# Background task functions
async def process_youtube_download(job_id: str, url: str, quality: str, format_id: Optional[str], db_id: int):
    """
    Process YouTube download in background
    
    Args:
        job_id: Unique job identifier
        url: YouTube video URL
        quality: Video quality
        format_id: Specific format ID (optional)
        db_id: Database ID for the download job
    """
    from sqlalchemy.orm import sessionmaker
    from db.database import engine
    from db.models import DownloadJob
    
    # Create database session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Get job from database
        job = db.query(DownloadJob).filter(DownloadJob.id == db_id).first()
        if not job:
            logger.error(f"Job {job_id} not found in database")
            return
        
        # Create progress tracker with callbacks
        progress_tracker = ProgressTracker(task_id=str(db_id))
        
        # Add database callback
        db_callback = DatabaseProgressCallback(db)
        progress_tracker.add_callback(db_callback)
        
        # Add logging callback
        log_callback = LoggingProgressCallback()
        progress_tracker.add_callback(log_callback)
        
        # Add websocket callback if available
        try:
            ws_callback = WebSocketProgressCallback(websocket_manager, f"download:{job_id}")
            progress_tracker.add_callback(ws_callback)
        except Exception as e:
            logger.warning(f"Could not initialize WebSocket callback: {e}")
        
        # Create downloader with progress tracking
        downloader = YouTubeDownloader(progress_tracker=progress_tracker)
        
        # Download content
        result = await downloader.download_content(url, quality=quality, format_id=format_id)
        
        # Update job with results
        job.completed_at = result.get('completed_at', db.func.now())
        
        if result.get('errors'):
            job.status = DownloadStatus.FAILED
            job.errors = result.get('errors')
            job.error_count = len(result.get('errors', []))
        else:
            job.status = DownloadStatus.COMPLETED
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error processing YouTube download {job_id}: {e}")
        try:
            job = db.query(DownloadJob).filter(DownloadJob.id == db_id).first()
            if job:
                job.status = DownloadStatus.FAILED
                job.errors = [str(e)]
                job.error_count = 1
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update job status: {db_error}")
    
    finally:
        db.close()


async def process_youtube_batch_download(job_id: str, urls: List[str], quality: str, db_id: int):
    """
    Process batch YouTube download in background
    
    Args:
        job_id: Unique job identifier
        urls: List of YouTube URLs
        quality: Video quality
        db_id: Database ID for the download job
    """
    from sqlalchemy.orm import sessionmaker
    from db.database import engine
    from db.models import DownloadJob
    
    # Create database session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Get job from database
        job = db.query(DownloadJob).filter(DownloadJob.id == db_id).first()
        if not job:
            logger.error(f"Job {job_id} not found in database")
            return
        
        # Create progress tracker with callbacks
        progress_tracker = ProgressTracker(task_id=str(db_id))
        progress_tracker.total_items = len(urls)
        
        # Add database callback
        db_callback = DatabaseProgressCallback(db)
        progress_tracker.add_callback(db_callback)
        
        # Add logging callback
        log_callback = LoggingProgressCallback()
        progress_tracker.add_callback(log_callback)
        
        # Add websocket callback if available
        try:
            ws_callback = WebSocketProgressCallback(websocket_manager, f"download:{job_id}")
            progress_tracker.add_callback(ws_callback)
        except Exception as e:
            logger.warning(f"Could not initialize WebSocket callback: {e}")
        
        # Create downloader with progress tracking
        downloader = YouTubeDownloader(progress_tracker=progress_tracker)
        
        # Process each URL
        results = []
        errors = []
        
        for i, url in enumerate(urls):
            try:
                # Update progress for current item
                await progress_tracker.update_item_progress(i, f"Processing URL {i+1}/{len(urls)}")
                
                # Download content
                result = await downloader.download_content(url, quality=quality)
                results.append(result)
                
                if result.get('errors'):
                    errors.extend(result.get('errors'))
                
            except Exception as e:
                errors.append(f"Error processing {url}: {str(e)}")
        
        # Update job with results
        job.completed_at = db.func.now()
        job.processed_items = len(results)
        
        if errors:
            job.errors = errors
            job.error_count = len(errors)
            
            # If all failed, mark as failed, otherwise it's completed with errors
            if len(errors) == len(urls):
                job.status = DownloadStatus.FAILED
            else:
                job.status = DownloadStatus.COMPLETED
        else:
            job.status = DownloadStatus.COMPLETED
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error processing batch YouTube download {job_id}: {e}")
        try:
            job = db.query(DownloadJob).filter(DownloadJob.id == db_id).first()
            if job:
                job.status = DownloadStatus.FAILED
                job.errors = [str(e)]
                job.error_count = 1
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update job status: {db_error}")
    
    finally:
        db.close() 