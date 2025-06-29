"""
Downloads API endpoints for managing download jobs and operations
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import re
import asyncio
import logging
from pydantic import BaseModel, Field
from typing import Union

from db.database import get_database
from db.models import DownloadJob, DownloadStatus, PlatformType
from db.schemas import (
    DownloadJob as DownloadJobSchema,
    DownloadJobCreate,
    DownloadJobUpdate,
    ApiResponse
)
from core.security import url_validator, malicious_url_detector
from db.storage import store_content
from services.youtube_downloader import YouTubeDownloader
from services.instagram_downloader import InstagramDownloader  
from services.threads_downloader import ThreadsDownloader
from services.rednote_downloader import RedNoteDownloader
from services.progress_tracker import (
    ProgressTracker, 
    DatabaseProgressCallback, 
    LoggingProgressCallback
)
from services.websocket_manager import websocket_manager, WebSocketProgressCallback

# Pydantic models for downloads
class SingleDownloadRequest(BaseModel):
    """Request schema for single URL download"""
    url: str = Field(..., description="URL to download content from")
    platform: Optional[PlatformType] = Field(None, description="Platform type (auto-detected if not provided)")
    download_files: bool = Field(False, description="Whether to download media files")

class BatchDownloadRequest(BaseModel):
    """Request schema for batch URL downloads"""
    urls: List[str] = Field(..., min_length=1, max_length=50, description="List of URLs to download")
    download_files: bool = Field(False, description="Whether to download media files")

class DownloadResult(BaseModel):
    """Response schema for download results"""
    success: bool
    url: str
    platform: Optional[str] = None
    post_id: Optional[int] = None
    error: Optional[str] = None
    warning: Optional[str] = None

# Platform downloader mapping
PLATFORM_DOWNLOADERS = {
    PlatformType.YOUTUBE: YouTubeDownloader,
    PlatformType.INSTAGRAM: InstagramDownloader, 
    PlatformType.THREADS: ThreadsDownloader,
    PlatformType.REDNOTE: RedNoteDownloader
}

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/platforms", response_model=ApiResponse)
async def get_supported_platforms():
    """
    Get list of supported platforms for downloads
    
    Returns information about which platforms are supported for content extraction.
    """
    try:
        platforms_info = []
        
        for platform in PlatformType:
            downloader_class = PLATFORM_DOWNLOADERS.get(platform)
            is_available = downloader_class is not None
            
            if is_available:
                # Get platform domains from downloader
                try:
                    # Handle different downloader initialization patterns
                    if platform == PlatformType.INSTAGRAM:
                        downloader = downloader_class(download_dir="downloads", rate_limit=2.0)
                    else:
                        downloader = downloader_class()
                    
                    domains = downloader.get_platform_domains()
                    supports_download = hasattr(downloader, 'download_content')
                except Exception as e:
                    logger.warning(f"Error instantiating {platform.value} downloader: {e}")
                    domains = []
                    supports_download = False
                
                platforms_info.append({
                    "platform": platform.value,
                    "display_name": platform.value.title(),
                    "is_available": True,
                    "supported_domains": domains,
                    "supports_download": supports_download
                })
            else:
                platforms_info.append({
                    "platform": platform.value,
                    "display_name": platform.value.title(),
                    "is_available": False,
                    "supported_domains": [],
                    "supports_download": False
                })
        
        return ApiResponse(
            success=True,
            data={
                "platforms": platforms_info,
                "total_supported": sum(1 for p in platforms_info if p["is_available"])
            },
            message=f"Retrieved information for {len(platforms_info)} platforms"
        )
        
    except Exception as e:
        logger.error(f"Error getting platform information: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve platform information: {str(e)}"
        )

@router.get("/stats/summary", response_model=ApiResponse)
async def get_download_stats(
    db: Session = Depends(get_database)
):
    """Get summary statistics for download jobs"""
    try:
        # Total jobs
        total_jobs = db.query(DownloadJob).count()
        
        # Jobs by status
        status_stats = db.query(
            DownloadJob.status,
            db.func.count(DownloadJob.id).label('count')
        ).group_by(DownloadJob.status).all()
        
        # Jobs by platform
        platform_stats = db.query(
            DownloadJob.platform,
            db.func.count(DownloadJob.id).label('count')
        ).group_by(DownloadJob.platform).all()
        
        # Recent activity (last 24 hours)
        day_ago = datetime.utcnow() - timedelta(days=1)
        recent_jobs = db.query(DownloadJob).filter(DownloadJob.created_at >= day_ago).count()
        
        # Success rate
        completed_jobs = db.query(DownloadJob).filter(DownloadJob.status == DownloadStatus.COMPLETED).count()
        failed_jobs = db.query(DownloadJob).filter(DownloadJob.status == DownloadStatus.FAILED).count()
        
        total_finished = completed_jobs + failed_jobs
        success_rate = (completed_jobs / total_finished * 100) if total_finished > 0 else 0
        
        return ApiResponse(
            success=True,
            data={
                "total_jobs": total_jobs,
                "status_breakdown": {stat.status.value: stat.count for stat in status_stats},
                "platform_breakdown": {stat.platform.value: stat.count for stat in platform_stats},
                "recent_jobs_24h": recent_jobs,
                "success_rate": round(success_rate, 2),
                "completed_jobs": completed_jobs,
                "failed_jobs": failed_jobs
            },
            message="Download statistics retrieved successfully"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve download statistics: {str(e)}"
        )

@router.get("/active", response_model=ApiResponse)
async def get_active_jobs(
    db: Session = Depends(get_database)
):
    """Get all active (pending or in-progress) download jobs"""
    try:
        active_jobs = db.query(DownloadJob).filter(
            DownloadJob.status.in_([DownloadStatus.PENDING, DownloadStatus.IN_PROGRESS])
        ).order_by(DownloadJob.created_at.desc()).all()
        
        jobs_data = [DownloadJobSchema.model_validate(job) for job in active_jobs]
        
        return ApiResponse(
            success=True,
            data={
                "active_jobs": jobs_data,
                "count": len(jobs_data)
            },
            message=f"Retrieved {len(jobs_data)} active download jobs"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve active download jobs: {str(e)}"
        )

@router.get("/", response_model=ApiResponse)
async def get_download_jobs(
    skip: int = Query(0, ge=0, description="Number of jobs to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of jobs to return"),
    status_filter: Optional[DownloadStatus] = Query(None, description="Filter by status"),
    platform: Optional[PlatformType] = Query(None, description="Filter by platform"),
    db: Session = Depends(get_database)
):
    """Get all download jobs with optional filtering and pagination"""
    try:
        query = db.query(DownloadJob)
        
        # Apply filters
        if status_filter:
            query = query.filter(DownloadJob.status == status_filter)
        
        if platform:
            query = query.filter(DownloadJob.platform == platform)
        
        # Get total count for pagination
        total = query.count()
        
        # Apply pagination and ordering (most recent first)
        jobs = query.order_by(DownloadJob.created_at.desc()).offset(skip).limit(limit).all()
        
        # Convert to Pydantic models
        jobs_data = [DownloadJobSchema.model_validate(job) for job in jobs]
        
        return ApiResponse(
            success=True,
            data={
                "jobs": jobs_data,
                "total": total,
                "skip": skip,
                "limit": limit
            },
            message=f"Retrieved {len(jobs_data)} download jobs"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve download jobs: {str(e)}"
        )


@router.get("/{job_id}", response_model=ApiResponse)
async def get_download_job(
    job_id: str,
    db: Session = Depends(get_database)
):
    """Get a specific download job by ID"""
    try:
        job = db.query(DownloadJob).filter(DownloadJob.job_id == job_id).first()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Download job with ID {job_id} not found"
            )
        
        job_data = DownloadJobSchema.model_validate(job)
        
        return ApiResponse(
            success=True,
            data=job_data,
            message=f"Retrieved download job {job_id}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve download job: {str(e)}"
        )

@router.get("/{job_id}/status", response_model=ApiResponse)
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_database)
):
    """
    Get detailed status information for a download job including progress tracking
    
    This endpoint provides comprehensive status information including:
    - Current progress percentage and step
    - Processing statistics and timing
    - Error details and warnings
    - Estimated completion time
    """
    try:
        job = db.query(DownloadJob).filter(DownloadJob.job_id == job_id).first()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Download job with ID {job_id} not found"
            )
        
        # Calculate additional status information
        status_info = {
            "job_id": job_id,
            "status": job.status.value,
            "progress": {
                "percentage": job.progress_percentage,
                "processed_items": job.processed_items,
                "total_items": job.total_items,
                "remaining_items": job.total_items - job.processed_items if job.total_items > 0 else 0
            },
            "timing": {
                "created_at": job.created_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "updated_at": job.updated_at
            },
            "platform": job.platform.value,
            "urls": job.urls,
            "error_handling": {
                "error_count": job.error_count,
                "errors": job.errors or [],
                "has_errors": job.error_count > 0
            }
        }
        
        # Calculate elapsed time and estimated completion
        if job.started_at:
            elapsed_time = (datetime.utcnow() - job.started_at).total_seconds()
            status_info["timing"]["elapsed_seconds"] = elapsed_time
            
            # Estimate completion time if job is in progress
            if job.status == DownloadStatus.IN_PROGRESS and job.progress_percentage > 0:
                estimated_total_time = elapsed_time / (job.progress_percentage / 100)
                estimated_remaining_time = estimated_total_time - elapsed_time
                status_info["timing"]["estimated_remaining_seconds"] = max(0, estimated_remaining_time)
                status_info["timing"]["estimated_completion"] = datetime.utcnow() + timedelta(seconds=estimated_remaining_time)
        
        # Add processing rate if applicable
        if job.started_at and job.processed_items > 0:
            elapsed_time = (datetime.utcnow() - job.started_at).total_seconds()
            if elapsed_time > 0:
                status_info["progress"]["processing_rate"] = job.processed_items / elapsed_time  # items per second
        
        # Add status-specific information
        if job.status == DownloadStatus.COMPLETED:
            status_info["completion_summary"] = {
                "success_rate": ((job.processed_items - job.error_count) / job.processed_items * 100) if job.processed_items > 0 else 0,
                "successful_items": job.processed_items - job.error_count,
                "failed_items": job.error_count
            }
        elif job.status == DownloadStatus.FAILED:
            status_info["failure_info"] = {
                "primary_error": job.errors[-1] if job.errors else "Unknown error",
                "total_errors": len(job.errors) if job.errors else 0
            }
        
        return ApiResponse(
            success=True,
            data=status_info,
            message=f"Retrieved detailed status for job {job_id}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve job status: {str(e)}"
        )


async def process_single_download(
    url: str, 
    platform: Optional[PlatformType] = None,
    download_files: bool = False,
    db: Session = None
) -> DownloadResult:
    """
    Process a single URL download (backward compatibility wrapper)
    
    Args:
        url: URL to download
        platform: Platform type (auto-detected if None)
        download_files: Whether to download media files
        db: Database session
        
    Returns:
        Download result
    """
    return await process_single_download_with_progress(
        url=url,
        platform=platform,
        download_files=download_files,
        db=db,
        progress_tracker=None
    )


@router.post("/", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_download_job(
    job_data: DownloadJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database)
):
    """Create a new download job with progress tracking"""
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Create new download job
        db_job = DownloadJob(
            job_id=job_id,
            **job_data.model_dump()
        )
        
        db.add(db_job)
        db.commit()
        db.refresh(db_job)
        
        # Add background task to process the download with progress tracking
        background_tasks.add_task(process_download_job_with_progress, job_id)
        
        job_response = DownloadJobSchema.model_validate(db_job)
        
        return ApiResponse(
            success=True,
            data=job_response,
            message=f"Download job created successfully with ID {job_id}. Processing started with progress tracking."
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create download job: {str(e)}"
        )


@router.put("/{job_id}", response_model=ApiResponse)
async def update_download_job(
    job_id: str,
    job_update: DownloadJobUpdate,
    db: Session = Depends(get_database)
):
    """Update an existing download job"""
    try:
        # Get existing job
        db_job = db.query(DownloadJob).filter(DownloadJob.job_id == job_id).first()
        if not db_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Download job with ID {job_id} not found"
            )
        
        # Update fields
        update_data = job_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_job, field, value)
        
        db_job.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_job)
        
        job_response = DownloadJobSchema.model_validate(db_job)
        
        return ApiResponse(
            success=True,
            data=job_response,
            message=f"Download job {job_id} updated successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update download job: {str(e)}"
        )


@router.delete("/{job_id}", response_model=ApiResponse)
async def delete_download_job(
    job_id: str,
    db: Session = Depends(get_database)
):
    """Delete a download job"""
    try:
        db_job = db.query(DownloadJob).filter(DownloadJob.job_id == job_id).first()
        if not db_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Download job with ID {job_id} not found"
            )
        
        # Only allow deletion of completed, failed, or cancelled jobs
        if db_job.status in [DownloadStatus.PENDING, DownloadStatus.IN_PROGRESS]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete active download job. Cancel it first."
            )
        
        db.delete(db_job)
        db.commit()
        
        return ApiResponse(
            success=True,
            data={"deleted_job_id": job_id},
            message=f"Download job {job_id} deleted successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete download job: {str(e)}"
        )


@router.post("/{job_id}/cancel", response_model=ApiResponse)
async def cancel_download_job(
    job_id: str,
    db: Session = Depends(get_database)
):
    """Cancel a download job"""
    try:
        db_job = db.query(DownloadJob).filter(DownloadJob.job_id == job_id).first()
        if not db_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Download job with ID {job_id} not found"
            )
        
        # Only allow cancellation of pending or in-progress jobs
        if db_job.status not in [DownloadStatus.PENDING, DownloadStatus.IN_PROGRESS]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel job with status: {db_job.status.value}"
            )
        
        # Update job status
        db_job.status = DownloadStatus.CANCELLED
        db_job.updated_at = datetime.utcnow()
        db_job.error_message = "Job cancelled by user"
        
        db.commit()
        db.refresh(db_job)
        
        job_response = DownloadJobSchema.model_validate(db_job)
        
        return ApiResponse(
            success=True,
            data=job_response,
            message=f"Download job {job_id} cancelled successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel download job: {str(e)}"
        )


@router.post("/{job_id}/retry", response_model=ApiResponse)
async def retry_download_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database)
):
    """Retry a failed download job with progress tracking"""
    try:
        db_job = db.query(DownloadJob).filter(DownloadJob.job_id == job_id).first()
        if not db_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Download job with ID {job_id} not found"
            )
        
        # Only allow retry of failed jobs
        if db_job.status != DownloadStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot retry job with status: {db_job.status.value}"
            )
        
        # Reset job status
        db_job.status = DownloadStatus.PENDING
        db_job.updated_at = datetime.utcnow()
        db_job.error_message = None
        db_job.progress_percentage = 0
        db_job.processed_items = 0
        
        db.commit()
        db.refresh(db_job)
        
        # Add background task to process the retry with progress tracking
        background_tasks.add_task(process_download_job_with_progress, job_id)
        
        job_response = DownloadJobSchema.model_validate(db_job)
        
        return ApiResponse(
            success=True,
            data=job_response,
            message=f"Download job {job_id} retry started with progress tracking"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry download job: {str(e)}"
        )




def detect_platform_from_url(url: str) -> Optional[PlatformType]:
    """
    Detect platform from URL using the security validator
    
    Args:
        url: URL to analyze
        
    Returns:
        Platform type or None if not detected
    """
    validation_result = url_validator.validate_url_format(url)
    
    if not validation_result['is_valid']:
        return None
        
    platform_info = validation_result.get('validation_details', {}).get('platform', {})
    platform_name = platform_info.get('platform')
    
    if platform_name and platform_info.get('is_supported', False):
        try:
            return PlatformType(platform_name)
        except ValueError:
            return None
    
    return None

async def process_download_job_with_progress(job_id: str):
    """
    Background task to process a download job with progress tracking
    
    Args:
        job_id: The job ID to process
    """
    from db.database import SessionLocal
    db = SessionLocal()
    
    try:
        # Get the job from database
        db_job = db.query(DownloadJob).filter(DownloadJob.job_id == job_id).first()
        if not db_job:
            logger.error(f"Job {job_id} not found in database")
            return
        
        # Set up progress tracking
        progress_tracker = ProgressTracker(
            task_id=job_id,
            callbacks=[
                DatabaseProgressCallback(db_session=db),
                WebSocketProgressCallback(websocket_manager),
                LoggingProgressCallback(logger, log_level=logging.INFO)
            ]
        )
        
        # Start progress tracking
        progress_tracker.start_progress()
        
        try:
            # Determine if this is a single URL or batch
            urls = []
            if db_job.url:
                urls = [db_job.url]
            elif db_job.urls:
                urls = db_job.urls
            else:
                raise ValueError("No URLs found in job")
            
            # Process URLs
            if len(urls) == 1:
                # Single URL processing
                result = await process_single_download_with_progress(
                    url=urls[0],
                    platform=db_job.platform,
                    download_files=db_job.download_files,
                    db=db,
                    progress_tracker=progress_tracker
                )
                
                if result.success:
                    progress_tracker.complete_progress(f"Successfully processed URL from {result.platform}")
                else:
                    progress_tracker.report_error(result.error or "Unknown error occurred")
                    
            else:
                # Batch processing
                await process_batch_download_with_progress(
                    urls=urls,
                    download_files=db_job.download_files,
                    db=db,
                    progress_tracker=progress_tracker
                )
                
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}")
            progress_tracker.report_error(f"Job processing failed: {str(e)}")
            
    except Exception as e:
        logger.error(f"Critical error in job {job_id}: {str(e)}")
    finally:
        db.close()


async def process_single_download_with_progress(
    url: str,
    platform: Optional[PlatformType] = None,
    download_files: bool = False,
    db: Session = None,
    progress_tracker: Optional[ProgressTracker] = None
) -> DownloadResult:
    """
    Process a single download with progress tracking
    
    Args:
        url: URL to download
        platform: Platform type (auto-detected if None)
        download_files: Whether to download media files
        db: Database session
        progress_tracker: Progress tracker instance
        
    Returns:
        DownloadResult with status and details
    """
    try:
        if progress_tracker:
            progress_tracker.update_status("Validating URL...")
        
        # Validate URL format
        validation_result = url_validator.validate_url_format(url)
        if not validation_result['is_valid']:
            return DownloadResult(
                success=False,
                url=url,
                error=f"Invalid URL format: {validation_result.get('error', 'Unknown validation error')}"
            )
            
        # Check for malicious URLs
        if progress_tracker:
            progress_tracker.update_status("Checking URL security...")
            
        malicious_check = malicious_url_detector.check_url(url)
        if malicious_check['is_malicious']:
            return DownloadResult(
                success=False,
                url=url,
                error=f"Malicious URL detected: {malicious_check.get('threat_type', 'security threat')}. " +
                      f"Detection method: {malicious_check.get('detection_method', 'security check')}"
            )
        
        # Auto-detect platform if not provided
        if not platform:
            if progress_tracker:
                progress_tracker.update_status("Detecting platform...")
            
            detected_platform = detect_platform_from_url(url)
            if not detected_platform:
                return DownloadResult(
                    success=False,
                    url=url,
                    error="Could not detect platform from URL"
                )
            platform = detected_platform
        
        # Get appropriate downloader
        downloader_class = PLATFORM_DOWNLOADERS.get(platform)
        if not downloader_class:
            return DownloadResult(
                success=False,
                url=url,
                error=f"No downloader available for platform: {platform.value}"
            )
        
        # Initialize downloader with progress tracking
        if progress_tracker:
            progress_tracker.update_status(f"Initializing {platform.value} downloader...")
        
        # Handle different downloader initialization patterns
        if platform == PlatformType.INSTAGRAM:
            downloader = downloader_class(download_dir="downloads", rate_limit=2.0)
        else:
            downloader = downloader_class()
        
        # Download content
        if progress_tracker:
            progress_tracker.update_status(f"Downloading content from {platform.value}...")
            progress_tracker.update_progress(25)  # 25% progress after initialization
        
        content_data = await downloader.extract_content(url)
        
        if not content_data or not content_data.get('success', False):
            error_msg = content_data.get('error', 'Unknown error during content extraction')
            if progress_tracker:
                progress_tracker.update_status(f"Download failed: {error_msg}")
                progress_tracker.update_progress(0)
            return DownloadResult(
                success=False,
                url=url,
                platform=platform.value,
                error=error_msg
            )
        
        if progress_tracker:
            progress_tracker.update_status("Content extracted successfully")
            progress_tracker.update_progress(50)  # 50% progress after extraction
        
        # Store content in database
        if progress_tracker:
            progress_tracker.update_status("Storing content in database...")
        
        try:
            post_id = await store_content(content_data, platform, db)
            
            if progress_tracker:
                progress_tracker.update_status("Content stored successfully")
                progress_tracker.update_progress(75)  # 75% progress after storing
            
            # Download media files if requested
            if download_files and hasattr(downloader, 'download_media'):
                if progress_tracker:
                    progress_tracker.update_status("Downloading media files...")
                
                media_result = await downloader.download_media(content_data)
                
                if not media_result.get('success', False):
                    warning_msg = f"Content stored but media download failed: {media_result.get('error', 'Unknown error')}"
                    if progress_tracker:
                        progress_tracker.update_status(warning_msg)
                    
                    return DownloadResult(
                        success=True,
                        url=url,
                        platform=platform.value,
                        post_id=post_id,
                        warning=warning_msg
                    )
            
            if progress_tracker:
                progress_tracker.update_status("Download completed successfully")
                progress_tracker.update_progress(100)  # 100% progress when done
            
            return DownloadResult(
                success=True,
                url=url,
                platform=platform.value,
                post_id=post_id
            )
            
        except Exception as e:
            if progress_tracker:
                progress_tracker.update_status(f"Error storing content: {str(e)}")
            logger.error(f"Error storing content: {str(e)}")
            return DownloadResult(
                success=False,
                url=url,
                platform=platform.value,
                error=f"Error storing content: {str(e)}"
            )
    
    except Exception as e:
        error_msg = f"Error processing download: {str(e)}"
        if progress_tracker:
            progress_tracker.update_status(error_msg)
        logger.error(error_msg)
        return DownloadResult(
            success=False,
            url=url,
            error=error_msg
        )


async def process_batch_download_with_progress(
    urls: List[str],
    download_files: bool = False,
    db: Session = None,
    progress_tracker: Optional[ProgressTracker] = None
):
    """
    Process a batch of URLs for download with progress tracking
    
    Args:
        urls: List of URLs to download
        download_files: Whether to download media files
        db: Database session
        progress_tracker: Progress tracker instance
        
    Returns:
        Dict with results and statistics
    """
    if progress_tracker:
        progress_tracker.update_status(f"Processing batch download of {len(urls)} URLs")
    
    # Validate URLs first
    if progress_tracker:
        progress_tracker.update_status("Validating URLs...")
    
    validation_results = url_validator.validate_batch_urls(urls)
    valid_urls = [item['url'] for item in validation_results['valid_urls']]
    invalid_urls = validation_results['invalid_urls']
    
    # Check for malicious URLs
    if progress_tracker:
        progress_tracker.update_status("Checking URL security...")
    
    malicious_check_results = malicious_url_detector.check_batch_urls(valid_urls)
    safe_urls = [item['url'] for item in malicious_check_results['safe_urls']]
    malicious_urls = malicious_check_results['malicious_urls']
    
    # Prepare results for invalid and malicious URLs
    failed_results = []
    
    # Add invalid URLs to failed results
    for invalid in invalid_urls:
        failed_results.append(DownloadResult(
            success=False,
            url=invalid['url'],
            error=f"Invalid URL: {invalid.get('error', 'Unknown validation error')}"
        ))
    
    # Add malicious URLs to failed results
    for malicious in malicious_urls:
        failed_results.append(DownloadResult(
            success=False,
            url=malicious['url'],
            error=f"Malicious URL detected: {malicious.get('threat_type', 'security threat')}. " +
                  f"Detection method: {malicious.get('detection_method', 'security check')}"
        ))
    
    # Process only safe URLs
    results = []
    success_count = 0
    failure_count = len(failed_results)
    
    total_safe_urls = len(safe_urls)
    
    if progress_tracker:
        progress_tracker.update_status(f"Found {total_safe_urls} safe URLs to process")
    
    for i, url in enumerate(safe_urls):
        if progress_tracker:
            progress_tracker.update_status(f"Processing URL {i+1}/{total_safe_urls}: {url}")
            progress_tracker.update_progress(int((i / total_safe_urls) * 100))
        
        result = await process_single_download_with_progress(
            url=url,
            download_files=download_files,
            db=db,
            progress_tracker=None  # Don't pass the tracker to avoid nested updates
        )
        
        results.append(result)
        
        if result.success:
            success_count += 1
        else:
            failure_count += 1
    
    # Combine all results
    all_results = results + failed_results
    
    if progress_tracker:
        progress_tracker.update_status(f"Batch processing complete: {success_count} succeeded, {failure_count} failed")
        progress_tracker.update_progress(100)
    
    return {
        "results": all_results,
        "summary": {
            "total": len(urls),
            "success": success_count,
            "failure": failure_count,
            "invalid_urls": len(invalid_urls),
            "malicious_urls": len(malicious_urls),
            "success_rate": round((success_count / len(urls)) * 100, 2) if urls else 0
        }
    }

@router.post("/single", response_model=ApiResponse, status_code=status.HTTP_200_OK)
async def download_single_url(
    request: SingleDownloadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database)
):
    """
    Download content from a single URL
    
    This endpoint accepts a single URL, validates it, determines the platform,
    extracts content using the appropriate downloader, and stores the result.
    """
    try:
        # Validate input
        if not request.url.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL cannot be empty"
            )
        
        # Process download
        result = await process_single_download_with_progress(
            url=request.url.strip(),
            platform=request.platform,
            download_files=request.download_files,
            db=db
        )
        
        if result.success:
            return ApiResponse(
                success=True,
                data={
                    "result": result.model_dump(),
                    "platform": result.platform,
                    "post_id": result.post_id
                },
                message=f"Successfully processed URL from {result.platform}"
            )
        else:
            return ApiResponse(
                success=False,
                data={"result": result.model_dump()},
                error=result.error
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in single download: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process download: {str(e)}"
        )

@router.post("/batch", response_model=ApiResponse, status_code=status.HTTP_200_OK)
async def download_batch_urls(
    request: BatchDownloadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database)
):
    """
    Download content from multiple URLs in batch
    
    This endpoint accepts multiple URLs, validates them, determines platforms,
    extracts content using appropriate downloaders, and stores the results.
    Processing is done sequentially to avoid overwhelming target sites.
    """
    try:
        # Validate input
        if not request.urls:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URLs list cannot be empty"
            )
        
        # Remove empty URLs and duplicates while preserving order
        clean_urls = []
        seen_urls = set()
        for url in request.urls:
            clean_url = url.strip()
            if clean_url and clean_url not in seen_urls:
                clean_urls.append(clean_url)
                seen_urls.add(clean_url)
        
        if not clean_urls:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid URLs provided"
            )
        
        # Validate batch size
        if len(clean_urls) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch size cannot exceed 50 URLs"
            )
        
        # Process each URL
        results = []
        successful_downloads = 0
        failed_downloads = 0
        platform_stats = {}
        
        for url in clean_urls:
            result = await process_single_download_with_progress(
                url=url,
                platform=None,  # Auto-detect for each URL
                download_files=request.download_files,
                db=db
            )
            
            results.append(result)
            
            if result.success:
                successful_downloads += 1
                platform = result.platform or 'unknown'
                platform_stats[platform] = platform_stats.get(platform, 0) + 1
            else:
                failed_downloads += 1
            
            # Add small delay between requests to be respectful
            await asyncio.sleep(0.5)
        
        # Prepare response
        response_data = {
            "results": [result.model_dump() for result in results],
            "summary": {
                "total_urls": len(clean_urls),
                "successful": successful_downloads,
                "failed": failed_downloads,
                "success_rate": successful_downloads / len(clean_urls) if clean_urls else 0,
                "platform_breakdown": platform_stats
            }
        }
        
        # Determine overall success
        overall_success = successful_downloads > 0
        
        if overall_success:
            message = f"Batch download completed: {successful_downloads}/{len(clean_urls)} successful"
        else:
            message = f"Batch download failed: All {failed_downloads} URLs failed to process"
        
        return ApiResponse(
            success=overall_success,
            data=response_data,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in batch download: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process batch download: {str(e)}"
        ) 