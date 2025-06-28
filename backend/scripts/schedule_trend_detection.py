#!/usr/bin/env python
"""
Scheduled Trend Detection
Runs trend detection at regular intervals.
"""

import sys
import os
import time
import logging
import argparse
import schedule
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.run_trend_detection import run_trend_detection
from db.models import PlatformType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), '../logs/scheduled_trends.log'))
    ]
)

logger = logging.getLogger(__name__)


def setup_schedule(realtime_interval=5, short_interval=30, medium_interval=120, long_interval=360):
    """
    Set up scheduled trend detection
    
    Args:
        realtime_interval: Interval in minutes for realtime window
        short_interval: Interval in minutes for short window
        medium_interval: Interval in minutes for medium window
        long_interval: Interval in minutes for long window
    """
    # Schedule realtime trend detection (default: every 5 minutes)
    schedule.every(realtime_interval).minutes.do(
        run_trend_detection, window_name="realtime", platform=None, save_to_db=True
    )
    logger.info(f"Scheduled realtime trend detection every {realtime_interval} minutes")
    
    # Schedule short window trend detection (default: every 30 minutes)
    schedule.every(short_interval).minutes.do(
        run_trend_detection, window_name="short", platform=None, save_to_db=True
    )
    logger.info(f"Scheduled short window trend detection every {short_interval} minutes")
    
    # Schedule medium window trend detection (default: every 2 hours)
    schedule.every(medium_interval).minutes.do(
        run_trend_detection, window_name="medium", platform=None, save_to_db=True
    )
    logger.info(f"Scheduled medium window trend detection every {medium_interval} minutes")
    
    # Schedule long window trend detection (default: every 6 hours)
    schedule.every(long_interval).minutes.do(
        run_trend_detection, window_name="long", platform=None, save_to_db=True
    )
    logger.info(f"Scheduled long window trend detection every {long_interval} minutes")


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description="Schedule regular trend detection")
    parser.add_argument(
        "--realtime", 
        type=int, 
        default=5,
        help="Interval in minutes for realtime window (default: 5)"
    )
    parser.add_argument(
        "--short", 
        type=int, 
        default=30,
        help="Interval in minutes for short window (default: 30)"
    )
    parser.add_argument(
        "--medium", 
        type=int, 
        default=120,
        help="Interval in minutes for medium window (default: 120)"
    )
    parser.add_argument(
        "--long", 
        type=int, 
        default=360,
        help="Interval in minutes for long window (default: 360)"
    )
    parser.add_argument(
        "--initial-run",
        action="store_true",
        help="Run all trend detection immediately on startup"
    )
    
    args = parser.parse_args()
    
    # Set up scheduled tasks
    setup_schedule(
        realtime_interval=args.realtime,
        short_interval=args.short,
        medium_interval=args.medium,
        long_interval=args.long
    )
    
    # Run initial detection if requested
    if args.initial_run:
        logger.info("Running initial trend detection for all windows")
        run_trend_detection(window_name="all", platform=None, save_to_db=True)
    
    # Run the scheduler
    logger.info("Scheduler started, press Ctrl+C to exit")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")


if __name__ == "__main__":
    main() 