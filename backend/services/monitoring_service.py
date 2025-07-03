"""
Monitoring Service
Handles automated monitoring of social media channels/accounts
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from backend.db.models import (
    MonitoringJob, 
    MonitoringRun, 
    MonitoringFrequency, 
    MonitoringStatus, 
    DownloadStatus,
    PlatformType
)
from backend.services.youtube_downloader import YouTubeDownloader
from backend.services.instagram_downloader import InstagramDownloader
from backend.services.threads_downloader import ThreadsDownloader
from backend.services.rednote_downloader import RedNoteDownloader

# Configure logging
logger = logging.getLogger(__name__)


class MonitoringService:
    """Service for managing automated monitoring of social media channels/accounts"""
    
    def __init__(self, db: Session):
        self.db = db
        self.downloaders = {
            PlatformType.YOUTUBE: YouTubeDownloader(),
            PlatformType.INSTAGRAM: InstagramDownloader(),
            PlatformType.THREADS: ThreadsDownloader(),
            PlatformType.REDNOTE: RedNoteDownloader()
        }
    
    def create_monitoring_job(self, job_data: Dict[str, Any]) -> MonitoringJob:
        """
        Create a new monitoring job
        
        Args:
            job_data: Dictionary containing job configuration
            
        Returns:
            The created MonitoringJob instance
        """
        # Generate a unique job ID
        job_id = str(uuid.uuid4())
        
        # Set the next run time based on frequency
        next_run_at = self._calculate_next_run_time(
            job_data.get('frequency', MonitoringFrequency.DAILY),
            job_data.get('interval_minutes')
        )
        
        # Create the monitoring job
        monitoring_job = MonitoringJob(
            job_id=job_id,
            name=job_data['name'],
            platform=job_data['platform'],
            target_url=job_data['target_url'],
            target_id=job_data.get('target_id'),
            target_type=job_data['target_type'],
            frequency=job_data.get('frequency', MonitoringFrequency.DAILY),
            interval_minutes=job_data.get('interval_minutes'),
            max_items_per_run=job_data.get('max_items_per_run', 10),
            status=MonitoringStatus.ACTIVE,
            next_run_at=next_run_at,
            notify_on_new_content=job_data.get('notify_on_new_content', True),
            notify_on_failure=job_data.get('notify_on_failure', True),
            notification_email=job_data.get('notification_email'),
            download_options=job_data.get('download_options', {}),
            filter_criteria=job_data.get('filter_criteria', {}),
            expires_at=job_data.get('expires_at'),
            user_id=job_data.get('user_id')
        )
        
        self.db.add(monitoring_job)
        self.db.commit()
        self.db.refresh(monitoring_job)
        
        logger.info(f"Created monitoring job: {monitoring_job.job_id} ({monitoring_job.name})")
        return monitoring_job
    
    def update_monitoring_job(self, job_id: int, job_data: Dict[str, Any]) -> Optional[MonitoringJob]:
        """
        Update an existing monitoring job
        
        Args:
            job_id: ID of the job to update
            job_data: Dictionary containing updated job configuration
            
        Returns:
            The updated MonitoringJob instance or None if not found
        """
        job = self.db.query(MonitoringJob).filter(MonitoringJob.id == job_id).first()
        if not job:
            logger.warning(f"Monitoring job not found: {job_id}")
            return None
        
        # Update fields
        for key, value in job_data.items():
            if hasattr(job, key) and key != 'id' and key != 'job_id':
                setattr(job, key, value)
        
        # If frequency was updated, recalculate next run time
        if 'frequency' in job_data or 'interval_minutes' in job_data:
            job.next_run_at = self._calculate_next_run_time(
                job.frequency,
                job.interval_minutes
            )
        
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Updated monitoring job: {job.job_id} ({job.name})")
        return job
    
    def delete_monitoring_job(self, job_id: int) -> bool:
        """
        Delete a monitoring job
        
        Args:
            job_id: ID of the job to delete
            
        Returns:
            True if successful, False otherwise
        """
        job = self.db.query(MonitoringJob).filter(MonitoringJob.id == job_id).first()
        if not job:
            logger.warning(f"Monitoring job not found: {job_id}")
            return False
        
        # Delete all associated runs
        self.db.query(MonitoringRun).filter(MonitoringRun.monitoring_job_id == job_id).delete()
        
        # Delete the job
        self.db.delete(job)
        self.db.commit()
        
        logger.info(f"Deleted monitoring job: {job.job_id} ({job.name})")
        return True
    
    def get_monitoring_job(self, job_id: int) -> Optional[MonitoringJob]:
        """
        Get a monitoring job by ID
        
        Args:
            job_id: ID of the job to retrieve
            
        Returns:
            The MonitoringJob instance or None if not found
        """
        return self.db.query(MonitoringJob).filter(MonitoringJob.id == job_id).first()
    
    def get_monitoring_jobs(
        self, 
        user_id: Optional[int] = None, 
        platform: Optional[PlatformType] = None,
        status: Optional[MonitoringStatus] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> List[MonitoringJob]:
        """
        Get monitoring jobs with optional filtering
        
        Args:
            user_id: Filter by user ID
            platform: Filter by platform
            status: Filter by status
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of MonitoringJob instances
        """
        query = self.db.query(MonitoringJob)
        
        # Apply filters
        if user_id is not None:
            query = query.filter(MonitoringJob.user_id == user_id)
        if platform is not None:
            query = query.filter(MonitoringJob.platform == platform)
        if status is not None:
            query = query.filter(MonitoringJob.status == status)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        return query.all()
    
    def get_pending_jobs(self) -> List[MonitoringJob]:
        """
        Get all jobs that are due to run
        
        Returns:
            List of MonitoringJob instances
        """
        now = datetime.utcnow()
        
        # Use a simpler query that doesn't rely on User model relationships
        # This avoids potential circular import issues
        return self.db.query(MonitoringJob).filter(
            and_(
                MonitoringJob.status == MonitoringStatus.ACTIVE,
                MonitoringJob.next_run_at <= now
            )
        ).all()
    
    def execute_job(self, job_id: int) -> MonitoringRun:
        """
        Execute a monitoring job immediately
        
        Args:
            job_id: ID of the job to execute
            
        Returns:
            The MonitoringRun instance
        """
        job = self.get_monitoring_job(job_id)
        if not job:
            raise ValueError(f"Monitoring job not found: {job_id}")
        
        # Create a new monitoring run
        run = MonitoringRun(
            monitoring_job_id=job.id,
            status=DownloadStatus.IN_PROGRESS
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        
        try:
            # Get the appropriate downloader
            downloader = self.downloaders.get(job.platform)
            if not downloader:
                raise ValueError(f"No downloader available for platform: {job.platform}")
            
            # Execute the download based on target type
            if job.target_type == 'channel':
                result = downloader.download_channel(
                    job.target_url, 
                    max_items=job.max_items_per_run,
                    options=job.download_options or {}
                )
            elif job.target_type == 'account':
                result = downloader.download_account(
                    job.target_url,
                    max_items=job.max_items_per_run,
                    options=job.download_options or {}
                )
            elif job.target_type == 'hashtag':
                result = downloader.download_hashtag(
                    job.target_url,
                    max_items=job.max_items_per_run,
                    options=job.download_options or {}
                )
            else:
                raise ValueError(f"Unsupported target type: {job.target_type}")
            
            # Update the monitoring run with results
            run.items_found = result.get('items_found', 0)
            run.items_processed = result.get('items_processed', 0)
            run.new_items_downloaded = result.get('new_items', 0)
            run.download_job_id = result.get('download_job_id')
            run.status = DownloadStatus.COMPLETED
            run.end_time = datetime.utcnow()
            
            # Update the job's statistics
            job.last_run_at = datetime.utcnow()
            job.next_run_at = self._calculate_next_run_time(job.frequency, job.interval_minutes)
            job.total_runs += 1
            job.successful_runs += 1
            
            # Handle notifications if new content was found
            if run.new_items_downloaded > 0 and job.notify_on_new_content:
                self._send_notification(
                    job,
                    f"New content detected: {run.new_items_downloaded} new items from {job.name}"
                )
            
            logger.info(f"Monitoring job executed successfully: {job.job_id} ({job.name})")
            
        except Exception as e:
            # Handle failure
            logger.exception(f"Error executing monitoring job {job.job_id}: {str(e)}")
            
            run.status = DownloadStatus.FAILED
            run.end_time = datetime.utcnow()
            run.error_message = str(e)
            
            # Update the job's statistics
            job.last_run_at = datetime.utcnow()
            job.next_run_at = self._calculate_next_run_time(job.frequency, job.interval_minutes)
            job.total_runs += 1
            job.failed_runs += 1
            
            # Handle failure notification
            if job.notify_on_failure:
                self._send_notification(
                    job,
                    f"Monitoring job failed: {job.name}",
                    error=str(e)
                )
        
        # Commit changes
        self.db.commit()
        self.db.refresh(run)
        
        return run
    
    def process_pending_jobs(self) -> List[MonitoringRun]:
        """
        Process all jobs that are due to run
        
        Returns:
            List of MonitoringRun instances
        """
        pending_jobs = self.get_pending_jobs()
        runs = []
        
        for job in pending_jobs:
            try:
                run = self.execute_job(job.id)
                runs.append(run)
            except Exception as e:
                logger.exception(f"Error processing job {job.job_id}: {str(e)}")
        
        return runs
    
    def pause_job(self, job_id: int) -> Optional[MonitoringJob]:
        """
        Pause a monitoring job
        
        Args:
            job_id: ID of the job to pause
            
        Returns:
            The updated MonitoringJob instance or None if not found
        """
        job = self.get_monitoring_job(job_id)
        if not job:
            return None
        
        job.status = MonitoringStatus.PAUSED
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Paused monitoring job: {job.job_id} ({job.name})")
        return job
    
    def resume_job(self, job_id: int) -> Optional[MonitoringJob]:
        """
        Resume a paused monitoring job
        
        Args:
            job_id: ID of the job to resume
            
        Returns:
            The updated MonitoringJob instance or None if not found
        """
        job = self.get_monitoring_job(job_id)
        if not job:
            return None
        
        job.status = MonitoringStatus.ACTIVE
        job.next_run_at = self._calculate_next_run_time(job.frequency, job.interval_minutes)
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Resumed monitoring job: {job.job_id} ({job.name})")
        return job
    
    def get_job_runs(self, job_id: int, skip: int = 0, limit: int = 100) -> List[MonitoringRun]:
        """
        Get the run history for a monitoring job
        
        Args:
            job_id: ID of the job
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of MonitoringRun instances
        """
        return self.db.query(MonitoringRun).filter(
            MonitoringRun.monitoring_job_id == job_id
        ).order_by(MonitoringRun.start_time.desc()).offset(skip).limit(limit).all()
    
    def _calculate_next_run_time(
        self, 
        frequency: MonitoringFrequency, 
        interval_minutes: Optional[int] = None
    ) -> datetime:
        """
        Calculate the next run time based on frequency
        
        Args:
            frequency: The monitoring frequency
            interval_minutes: Custom interval in minutes (for CUSTOM frequency)
            
        Returns:
            Datetime of the next scheduled run
        """
        now = datetime.utcnow()
        
        if frequency == MonitoringFrequency.HOURLY:
            return now + timedelta(hours=1)
        elif frequency == MonitoringFrequency.DAILY:
            return now + timedelta(days=1)
        elif frequency == MonitoringFrequency.WEEKLY:
            return now + timedelta(weeks=1)
        elif frequency == MonitoringFrequency.MONTHLY:
            # Approximate a month as 30 days
            return now + timedelta(days=30)
        elif frequency == MonitoringFrequency.CUSTOM:
            if not interval_minutes or interval_minutes < 1:
                # Default to hourly if no valid interval provided
                return now + timedelta(hours=1)
            return now + timedelta(minutes=interval_minutes)
        else:
            # Default to daily
            return now + timedelta(days=1)
    
    def _send_notification(self, job: MonitoringJob, message: str, error: Optional[str] = None) -> None:
        """
        Send a notification for a monitoring job
        
        Args:
            job: The monitoring job
            message: The notification message
            error: Optional error message
        """
        # This is a placeholder for the actual notification logic
        # In a real implementation, this would send emails, push notifications, etc.
        logger.info(f"NOTIFICATION for job {job.job_id}: {message}")
        if error:
            logger.info(f"Error details: {error}")
        
        # TODO: Implement actual notification logic
        # Example: Send email notification
        if job.notification_email:
            pass  # Implement email sending
