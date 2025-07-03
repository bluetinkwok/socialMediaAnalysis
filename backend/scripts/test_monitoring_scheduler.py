"""
Test script for monitoring scheduler

This script tests the monitoring service and scheduler functionality
without running the full scheduler process.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import uuid

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.db.session import get_db
from backend.services.monitoring_service import MonitoringService
from backend.db.models import MonitoringFrequency, MonitoringStatus, PlatformType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("test_monitoring_scheduler")

def test_create_monitoring_job():
    """Test creating a monitoring job"""
    logger.info("Testing monitoring job creation")
    
    # Get database session
    db = next(get_db())
    
    # Create monitoring service
    monitoring_service = MonitoringService(db)
    
    # Create a test monitoring job
    job_data = {
        "name": f"Test Job {uuid.uuid4().hex[:8]}",
        "platform": PlatformType.YOUTUBE,
        "target_url": "https://www.youtube.com/channel/UC-lHJZR3Gqxm24_Vd_AJ5Yw",
        "target_type": "channel",
        "frequency": MonitoringFrequency.HOURLY,
        "interval_minutes": 60,
        "max_items_per_run": 5,
        "notify_on_new_content": True,
        "notify_on_failure": True,
        "notification_email": "test@example.com"
    }
    
    job = monitoring_service.create_monitoring_job(**job_data)
    logger.info(f"Created job: {job.job_id} - {job.name}")
    
    # Set next run time to now to make it eligible for immediate processing
    job.next_run_at = datetime.now() - timedelta(minutes=5)
    db.commit()
    
    return job.job_id

def test_get_pending_jobs():
    """Test retrieving pending monitoring jobs"""
    logger.info("Testing retrieval of pending jobs")
    
    # Get database session
    db = next(get_db())
    
    # Create monitoring service
    monitoring_service = MonitoringService(db)
    
    # Get pending jobs
    pending_jobs = monitoring_service.get_pending_jobs()
    logger.info(f"Found {len(pending_jobs)} pending jobs")
    
    for job in pending_jobs:
        logger.info(f"Pending job: {job.job_id} - {job.name} - Next run: {job.next_run_at}")
    
    return pending_jobs

def test_process_job(job_id):
    """Test processing a specific monitoring job"""
    logger.info(f"Testing processing of job {job_id}")
    
    # Get database session
    db = next(get_db())
    
    # Create monitoring service
    monitoring_service = MonitoringService(db)
    
    # Process the job
    try:
        result = monitoring_service.process_job(job_id)
        logger.info(f"Job processing result: {result}")
    except Exception as e:
        logger.error(f"Error processing job: {e}")
        return False
    
    return True

def main():
    """Main test function"""
    logger.info("Starting monitoring scheduler test")
    
    # Test creating a job
    job_id = test_create_monitoring_job()
    
    # Test getting pending jobs
    pending_jobs = test_get_pending_jobs()
    
    # Test processing a job if we have any
    if job_id:
        test_process_job(job_id)
    elif pending_jobs:
        test_process_job(pending_jobs[0].job_id)
    else:
        logger.warning("No jobs to process")
    
    logger.info("Test completed")

if __name__ == "__main__":
    main()
