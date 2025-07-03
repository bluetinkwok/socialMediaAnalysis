"""
Monitoring API Routes
Endpoints for managing automated monitoring of social media channels/accounts
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import MonitoringFrequency, MonitoringStatus, PlatformType
from services.monitoring_service import MonitoringService
from api.schemas.monitoring import (
    MonitoringJobCreate,
    MonitoringJobUpdate,
    MonitoringJobResponse,
    MonitoringRunResponse,
    MonitoringJobFilterParams
)
from api.auth import get_current_user

router = APIRouter()


@router.post("/monitoring/jobs", response_model=MonitoringJobResponse)
def create_monitoring_job(
    job_data: MonitoringJobCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new monitoring job
    """
    # Add the user ID to the job data
    job_dict = job_data.dict()
    job_dict["user_id"] = current_user.id
    
    service = MonitoringService(db)
    try:
        job = service.create_monitoring_job(job_dict)
        return job
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create monitoring job: {str(e)}"
        )


@router.get("/monitoring/jobs", response_model=List[MonitoringJobResponse])
def get_monitoring_jobs(
    params: MonitoringJobFilterParams = Depends(),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all monitoring jobs for the current user
    """
    service = MonitoringService(db)
    
    # Convert string parameters to enums if provided
    platform = PlatformType(params.platform) if params.platform else None
    status = MonitoringStatus(params.status) if params.status else None
    
    jobs = service.get_monitoring_jobs(
        user_id=current_user.id,
        platform=platform,
        status=status,
        skip=params.skip,
        limit=params.limit
    )
    return jobs


@router.get("/monitoring/jobs/{job_id}", response_model=MonitoringJobResponse)
def get_monitoring_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get a specific monitoring job by ID
    """
    service = MonitoringService(db)
    job = service.get_monitoring_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring job not found"
        )
    
    # Check if the job belongs to the current user
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return job


@router.put("/monitoring/jobs/{job_id}", response_model=MonitoringJobResponse)
def update_monitoring_job(
    job_id: int,
    job_data: MonitoringJobUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update an existing monitoring job
    """
    service = MonitoringService(db)
    
    # Check if the job exists and belongs to the current user
    existing_job = service.get_monitoring_job(job_id)
    if not existing_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring job not found"
        )
    
    if existing_job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Update the job
    try:
        updated_job = service.update_monitoring_job(job_id, job_data.dict(exclude_unset=True))
        if not updated_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Monitoring job not found"
            )
        return updated_job
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update monitoring job: {str(e)}"
        )


@router.delete("/monitoring/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monitoring_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Delete a monitoring job
    """
    service = MonitoringService(db)
    
    # Check if the job exists and belongs to the current user
    existing_job = service.get_monitoring_job(job_id)
    if not existing_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring job not found"
        )
    
    if existing_job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Delete the job
    success = service.delete_monitoring_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete monitoring job"
        )
    
    return None


@router.post("/monitoring/jobs/{job_id}/execute", response_model=MonitoringRunResponse)
def execute_monitoring_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Execute a monitoring job immediately
    """
    service = MonitoringService(db)
    
    # Check if the job exists and belongs to the current user
    existing_job = service.get_monitoring_job(job_id)
    if not existing_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring job not found"
        )
    
    if existing_job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Execute the job
    try:
        run = service.execute_job(job_id)
        return run
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute monitoring job: {str(e)}"
        )


@router.post("/monitoring/jobs/{job_id}/pause", response_model=MonitoringJobResponse)
def pause_monitoring_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Pause a monitoring job
    """
    service = MonitoringService(db)
    
    # Check if the job exists and belongs to the current user
    existing_job = service.get_monitoring_job(job_id)
    if not existing_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring job not found"
        )
    
    if existing_job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Pause the job
    updated_job = service.pause_job(job_id)
    if not updated_job:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pause monitoring job"
        )
    
    return updated_job


@router.post("/monitoring/jobs/{job_id}/resume", response_model=MonitoringJobResponse)
def resume_monitoring_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Resume a paused monitoring job
    """
    service = MonitoringService(db)
    
    # Check if the job exists and belongs to the current user
    existing_job = service.get_monitoring_job(job_id)
    if not existing_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring job not found"
        )
    
    if existing_job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Resume the job
    updated_job = service.resume_job(job_id)
    if not updated_job:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume monitoring job"
        )
    
    return updated_job


@router.get("/monitoring/jobs/{job_id}/runs", response_model=List[MonitoringRunResponse])
def get_monitoring_job_runs(
    job_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get the run history for a monitoring job
    """
    service = MonitoringService(db)
    
    # Check if the job exists and belongs to the current user
    existing_job = service.get_monitoring_job(job_id)
    if not existing_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring job not found"
        )
    
    if existing_job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get the job runs
    runs = service.get_job_runs(job_id, skip, limit)
    return runs
