"""
Downloads API endpoints for managing download jobs and operations
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid

from db.database import get_database
from db.models import DownloadJob, DownloadStatus, PlatformType
from db.schemas import (
    DownloadJob as DownloadJobSchema,
    DownloadJobCreate,
    DownloadJobUpdate,
    ApiResponse
)

router = APIRouter()


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


@router.post("/", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_download_job(
    job_data: DownloadJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database)
):
    """Create a new download job"""
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
        
        # Add background task to process the download
        # Note: This would typically call a service function to handle the actual download
        # background_tasks.add_task(process_download_job, job_id)
        
        job_response = DownloadJobSchema.model_validate(db_job)
        
        return ApiResponse(
            success=True,
            data=job_response,
            message=f"Download job created successfully with ID {job_id}"
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
    """Retry a failed download job"""
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
        
        db.commit()
        db.refresh(db_job)
        
        # Add background task to process the download
        # background_tasks.add_task(process_download_job, job_id)
        
        job_response = DownloadJobSchema.model_validate(db_job)
        
        return ApiResponse(
            success=True,
            data=job_response,
            message=f"Download job {job_id} queued for retry"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry download job: {str(e)}"
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
        from datetime import timedelta
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