#!/usr/bin/env python3
"""
Monitoring Scheduler

This script runs a scheduler that periodically checks for pending monitoring jobs
and executes them according to their configured frequency.
"""

import os
import sys
import time
import logging
import signal
import argparse
import schedule
from datetime import datetime
from typing import List, Optional

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import privacy models first to avoid circular import issues
from backend.db.privacy_models import UserConsent, DataSubjectRequest, PrivacySettings
from backend.db.models import MonitoringJob, MonitoringRun, MonitoringStatus
from backend.services.monitoring_service import MonitoringService
from backend.db.session import SessionLocal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global flag to control the main loop
running = True

def signal_handler(sig, frame):
    """Handle termination signals"""
    global running
    logger.info("Received termination signal. Shutting down...")
    running = False

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def process_monitoring_jobs() -> List[MonitoringRun]:
    """
    Process all pending monitoring jobs
    
    Returns:
        List of MonitoringRun instances for jobs that were processed
    """
    logger.info("Processing pending monitoring jobs...")
    db = SessionLocal()
    try:
        service = MonitoringService(db)
        runs = service.process_pending_jobs()
        logger.info(f"Processed {len(runs)} monitoring jobs")
        return runs
    except Exception as e:
        logger.error(f"Error processing monitoring jobs: {str(e)}", exc_info=True)
        return []
    finally:
        db.close()

def main():
    """Main entry point for the scheduler"""
    parser = argparse.ArgumentParser(description='Run the monitoring scheduler')
    parser.add_argument('--interval', type=int, default=5, help='Check interval in minutes')
    parser.add_argument('--run-once', action='store_true', help='Run once and exit')
    args = parser.parse_args()
    
    logger.info("Starting monitoring scheduler...")
    
    if args.run_once:
        logger.info("Running in single execution mode")
        process_monitoring_jobs()
        return
    
    # Schedule the job to run at regular intervals
    schedule.every(args.interval).minutes.do(process_monitoring_jobs)
    logger.info(f"Scheduler configured to check every {args.interval} minutes")
    
    # Run the scheduler loop
    global running
    while running:
        schedule.run_pending()
        time.sleep(1)
    
    logger.info("Monitoring scheduler stopped")

if __name__ == "__main__":
    main() 