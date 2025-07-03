#!/usr/bin/env python
"""
Monitoring Scheduler

This script runs as a background service to check for pending monitoring jobs
and execute them according to their schedule.
"""

import sys
import os
import time
import logging
import argparse
import signal
from datetime import datetime
import schedule

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.db.session import get_db
from backend.services.monitoring_service import MonitoringService
from backend.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), '../logs/monitoring_scheduler.log'))
    ]
)
logger = logging.getLogger("monitoring_scheduler")

# Global flag to control the main loop
running = True

def signal_handler(sig, frame):
    """Handle termination signals"""
    global running
    logger.info(f"Received signal {sig}, shutting down...")
    running = False

def process_jobs():
    """Process pending monitoring jobs"""
    logger.info("Checking for pending monitoring jobs...")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Create monitoring service
        monitoring_service = MonitoringService(db)
        
        # Process pending jobs
        runs = monitoring_service.process_pending_jobs()
        
        if runs:
            logger.info(f"Processed {len(runs)} monitoring jobs")
            for run in runs:
                logger.info(f"Job {run.monitoring_job_id} - Status: {run.status.value}")
        else:
            logger.info("No pending jobs found")
            
    except Exception as e:
        logger.error(f"Error processing jobs: {e}", exc_info=True)
    finally:
        db.close()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Monitoring scheduler for social media analysis")
    parser.add_argument("--interval", type=int, default=settings.MONITORING_CHECK_INTERVAL,
                        help=f"Check interval in seconds (default: {settings.MONITORING_CHECK_INTERVAL})")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info(f"Starting monitoring scheduler (interval: {args.interval} seconds)")
    
    if args.once:
        # Run once and exit
        process_jobs()
    else:
        # Schedule the job to run at regular intervals
        schedule.every(args.interval).seconds.do(process_jobs)
        
        # Run the scheduler loop
        while running:
            schedule.run_pending()
            time.sleep(1)
    
    logger.info("Monitoring scheduler stopped")

if __name__ == "__main__":
    main()
