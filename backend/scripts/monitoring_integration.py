#!/usr/bin/env python
"""
Monitoring Integration Example

This script demonstrates how to integrate the monitoring scheduler with the main application.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from enum import Enum, auto
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("monitoring_integration")

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import application modules
try:
    from app.models.base_models import Base
    from app.models.monitoring_models import (
        MonitoringFrequency, 
        MonitoringStatus, 
        MonitoringJob, 
        MonitoringRun
    )
    from app.db.session import engine, SessionLocal
    
    # Check if we can connect to the database
    app_db_available = True
    logger.info("Main application database is available")
except ImportError:
    logger.warning("Main application modules not found, using mock implementation")
    app_db_available = False

# Mock implementation for when the main app is not available
if not app_db_available:
    class MonitoringFrequency(Enum):
        HOURLY = "hourly"
        DAILY = "daily"
        WEEKLY = "weekly"
        MONTHLY = "monthly"
        CUSTOM = "custom"
    
    class MonitoringStatus(Enum):
        ACTIVE = "active"
        PAUSED = "paused"
        COMPLETED = "completed"
        FAILED = "failed"
        DELETED = "deleted"
    
    class MockMonitoringJob:
        def __init__(self, **kwargs):
            self.id = kwargs.get('id', str(uuid.uuid4()))
            self.name = kwargs.get('name')
            self.platform = kwargs.get('platform')
            self.target_url = kwargs.get('target_url')
            self.target_type = kwargs.get('target_type')
            self.frequency = kwargs.get('frequency', MonitoringFrequency.DAILY)
            self.interval_minutes = kwargs.get('interval_minutes')
            self.status = kwargs.get('status', MonitoringStatus.ACTIVE)
            self.last_run_at = kwargs.get('last_run_at')
            self.next_run_at = kwargs.get('next_run_at')
            self.total_runs = kwargs.get('total_runs', 0)
            self.successful_runs = kwargs.get('successful_runs', 0)
            self.failed_runs = kwargs.get('failed_runs', 0)
            
        def __repr__(self):
            return f"<MockMonitoringJob {self.id}: {self.name}>"
    
    class MockMonitoringRun:
        def __init__(self, **kwargs):
            self.id = kwargs.get('id', str(uuid.uuid4()))
            self.monitoring_job_id = kwargs.get('monitoring_job_id')
            self.start_time = kwargs.get('start_time', datetime.now())
            self.end_time = kwargs.get('end_time')
            self.status = kwargs.get('status')
            self.items_found = kwargs.get('items_found', 0)
            self.items_processed = kwargs.get('items_processed', 0)
            self.new_items_downloaded = kwargs.get('new_items_downloaded', 0)
            self.error_message = kwargs.get('error_message')
            
        def __repr__(self):
            return f"<MockMonitoringRun {self.id}>"

def create_job(
    name, 
    platform, 
    target_url, 
    target_type, 
    frequency, 
    interval_minutes=None, 
    max_items_per_run=10
):
    """Create a new monitoring job"""
    if app_db_available:
        # Use the actual database
        db = SessionLocal()
        try:
            job = MonitoringJob(
                name=name,
                platform=platform,
                target_url=target_url,
                target_type=target_type,
                frequency=frequency,
                interval_minutes=interval_minutes,
                max_items_per_run=max_items_per_run,
                status=MonitoringStatus.ACTIVE,
                next_run_at=calculate_next_run_time(frequency, interval_minutes)
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            logger.info(f"Created monitoring job: {job.id}")
            return job
        finally:
            db.close()
    else:
        # Use mock implementation
        job = MockMonitoringJob(
            name=name,
            platform=platform,
            target_url=target_url,
            target_type=target_type,
            frequency=frequency,
            interval_minutes=interval_minutes,
            max_items_per_run=max_items_per_run,
            status=MonitoringStatus.ACTIVE,
            next_run_at=calculate_next_run_time(frequency, interval_minutes)
        )
        logger.info(f"Created mock monitoring job: {job.id}")
        return job

def get_pending_jobs():
    """Get all jobs that are due to run"""
    now = datetime.now()
    
    if app_db_available:
        # Use the actual database
        db = SessionLocal()
        try:
            jobs = db.query(MonitoringJob).filter(
                MonitoringJob.status == MonitoringStatus.ACTIVE,
                MonitoringJob.next_run_at <= now
            ).all()
            return jobs
        finally:
            db.close()
    else:
        # Mock implementation
        logger.info("Using mock implementation for get_pending_jobs")
        return []

def process_job(job):
    """Process a single monitoring job"""
    logger.info(f"Processing job: {job.id} ({job.name})")
    
    if app_db_available:
        # Use the actual database
        db = SessionLocal()
        try:
            # Create a run record
            run = MonitoringRun(
                monitoring_job_id=job.id,
                status="in_progress"
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            
            try:
                # Simulate job execution
                logger.info(f"Simulating download for {job.target_url}")
                # TODO: Actual implementation would call the appropriate service
                # based on job.platform (e.g., twitter_service, youtube_service)
                
                # Update job statistics
                job.last_run_at = datetime.now()
                job.total_runs += 1
                job.successful_runs += 1
                job.next_run_at = calculate_next_run_time(job.frequency, job.interval_minutes)
                
                # Complete the run
                run.status = "completed"
                run.end_time = datetime.now()
                run.items_found = 5
                run.items_processed = 5
                run.new_items_downloaded = 3
                
                db.commit()
                logger.info(f"Job {job.id} completed successfully")
                
            except Exception as e:
                logger.error(f"Error processing job {job.id}: {str(e)}", exc_info=True)
                
                # Update job statistics
                job.last_run_at = datetime.now()
                job.total_runs += 1
                job.failed_runs += 1
                job.next_run_at = calculate_next_run_time(job.frequency, job.interval_minutes)
                
                # Mark run as failed
                run.status = "failed"
                run.end_time = datetime.now()
                run.error_message = str(e)
                
                db.commit()
        finally:
            db.close()
    else:
        # Mock implementation
        logger.info(f"Mock processing of job {job.id}")

def calculate_next_run_time(frequency, interval_minutes=None):
    """Calculate the next run time based on frequency"""
    now = datetime.now()
    
    if frequency == MonitoringFrequency.HOURLY:
        return now + timedelta(hours=1)
    elif frequency == MonitoringFrequency.DAILY:
        return now + timedelta(days=1)
    elif frequency == MonitoringFrequency.WEEKLY:
        return now + timedelta(weeks=1)
    elif frequency == MonitoringFrequency.MONTHLY:
        # Approximate a month as 30 days
        return now + timedelta(days=30)
    elif frequency == MonitoringFrequency.CUSTOM and interval_minutes:
        return now + timedelta(minutes=interval_minutes)
    else:
        # Default to daily
        return now + timedelta(days=1)

def process_pending_jobs():
    """Process all pending monitoring jobs"""
    logger.info("Checking for pending monitoring jobs...")
    
    pending_jobs = get_pending_jobs()
    
    if pending_jobs:
        logger.info(f"Found {len(pending_jobs)} pending jobs")
        for job in pending_jobs:
            process_job(job)
    else:
        logger.info("No pending jobs found")

def create_test_job():
    """Create a test job"""
    return create_job(
        name="Test YouTube Channel",
        platform="youtube",
        target_url="https://www.youtube.com/channel/test",
        target_type="channel",
        frequency=MonitoringFrequency.HOURLY
    )

def main():
    """Main function for testing"""
    logger.info("Starting monitoring integration test")
    
    # Create a test job
    job = create_test_job()
    logger.info(f"Created test job: {job}")
    
    # Process pending jobs
    process_pending_jobs()
    
    logger.info("Monitoring integration test completed")

if __name__ == "__main__":
    main()
