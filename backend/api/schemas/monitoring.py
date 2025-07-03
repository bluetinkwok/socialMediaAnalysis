"""
Monitoring API Schemas
Pydantic models for the monitoring API
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator, root_validator
from fastapi import Query

from db.models import MonitoringFrequency, MonitoringStatus, DownloadStatus, PlatformType


class MonitoringJobFilterParams:
    """Query parameters for filtering monitoring jobs"""
    
    def __init__(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000)
    ):
        self.platform = platform
        self.status = status
        self.skip = skip
        self.limit = limit


class MonitoringJobBase(BaseModel):
    """Base model for monitoring jobs"""
    name: str
    platform: PlatformType
    target_url: str
    target_id: Optional[str] = None
    target_type: str
    frequency: MonitoringFrequency = MonitoringFrequency.DAILY
    interval_minutes: Optional[int] = None
    max_items_per_run: int = 10
    notify_on_new_content: bool = True
    notify_on_failure: bool = True
    notification_email: Optional[str] = None
    download_options: Optional[Dict[str, Any]] = None
    filter_criteria: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    
    @validator('interval_minutes')
    def validate_interval_minutes(cls, v, values):
        """Validate that interval_minutes is provided for CUSTOM frequency"""
        if values.get('frequency') == MonitoringFrequency.CUSTOM and (v is None or v < 1):
            raise ValueError("interval_minutes is required for CUSTOM frequency and must be at least 1")
        return v
    
    @validator('target_type')
    def validate_target_type(cls, v):
        """Validate the target type"""
        valid_types = ['channel', 'account', 'hashtag']
        if v not in valid_types:
            raise ValueError(f"target_type must be one of {valid_types}")
        return v


class MonitoringJobCreate(MonitoringJobBase):
    """Schema for creating a monitoring job"""
    pass


class MonitoringJobUpdate(BaseModel):
    """Schema for updating a monitoring job"""
    name: Optional[str] = None
    frequency: Optional[MonitoringFrequency] = None
    interval_minutes: Optional[int] = None
    max_items_per_run: Optional[int] = None
    status: Optional[MonitoringStatus] = None
    notify_on_new_content: Optional[bool] = None
    notify_on_failure: Optional[bool] = None
    notification_email: Optional[str] = None
    download_options: Optional[Dict[str, Any]] = None
    filter_criteria: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    
    @root_validator
    def validate_frequency_interval(cls, values):
        """Validate that interval_minutes is provided for CUSTOM frequency"""
        frequency = values.get('frequency')
        interval = values.get('interval_minutes')
        
        if frequency == MonitoringFrequency.CUSTOM and interval is not None and interval < 1:
            raise ValueError("interval_minutes must be at least 1 for CUSTOM frequency")
        return values


class MonitoringRunBase(BaseModel):
    """Base model for monitoring runs"""
    monitoring_job_id: int
    status: DownloadStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    items_found: int = 0
    items_processed: int = 0
    new_items_downloaded: int = 0
    download_job_id: Optional[str] = None
    error_message: Optional[str] = None


class MonitoringRunCreate(MonitoringRunBase):
    """Schema for creating a monitoring run"""
    pass


class MonitoringRunResponse(MonitoringRunBase):
    """Schema for monitoring run response"""
    id: int
    
    class Config:
        orm_mode = True


class MonitoringJobResponse(MonitoringJobBase):
    """Schema for monitoring job response"""
    id: int
    job_id: str
    status: MonitoringStatus
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime] = None
    next_run_at: datetime
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    user_id: int
    
    class Config:
        orm_mode = True 