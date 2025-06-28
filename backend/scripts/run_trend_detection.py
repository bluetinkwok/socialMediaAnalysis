#!/usr/bin/env python
"""
Trend Detection Script
Runs trend detection algorithms and stores results in the database.
"""

import sys
import os
import logging
import argparse
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.database import SessionLocal
from analytics.trend_detector import TrendDetector, TrendWindow, TrendType
from db.models import PlatformType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), '../logs/trend_detection.log'))
    ]
)

logger = logging.getLogger(__name__)


def run_trend_detection(window_name="all", platform=None, save_to_db=True):
    """
    Run trend detection for the specified window and platform
    
    Args:
        window_name: Window name ('realtime', 'short', 'medium', 'long', or 'all')
        platform: Optional platform filter
        save_to_db: Whether to save results to database
    """
    logger.info(f"Starting trend detection: window={window_name}, platform={platform}, save_to_db={save_to_db}")
    
    try:
        # Create database session
        db = SessionLocal()
        
        # Initialize trend detector
        trend_detector = TrendDetector(db)
        
        # If window is 'all', run for all windows
        if window_name == "all":
            windows = ["realtime", "short", "medium", "long"]
        else:
            windows = [window_name]
        
        # Run trend detection for each window
        for window in windows:
            logger.info(f"Running trend detection for window: {window}")
            
            # Detect performance trends
            performance_trends = trend_detector.detect_performance_trends(window, platform)
            logger.info(f"Found {len(performance_trends)} performance trends")
            
            # Detect viral content
            viral_trends = trend_detector.detect_viral_content(window, platform)
            logger.info(f"Found {len(viral_trends)} viral trends")
            
            # Detect rising trends
            rising_trends = trend_detector.detect_rising_trends(window, platform)
            logger.info(f"Found {len(rising_trends)} rising trends")
            
            # Detect quality trends
            quality_trends = trend_detector.detect_quality_trends(window, platform)
            logger.info(f"Found {len(quality_trends)} quality trends")
            
            # Detect hashtag trends
            hashtag_trends = trend_detector.detect_hashtag_trends(window, platform)
            logger.info(f"Found {len(hashtag_trends)} hashtag trends")
            
            # Detect content patterns
            pattern_trends = trend_detector.detect_content_patterns(window, platform)
            logger.info(f"Found {len(pattern_trends)} content pattern trends")
            
            # If save_to_db is True, store trends in database
            if save_to_db:
                logger.info("Saving trends to database")
                # Collect all trends
                all_trends = []
                all_trends.extend(performance_trends)
                all_trends.extend(viral_trends)
                all_trends.extend(rising_trends)
                all_trends.extend(quality_trends)
                all_trends.extend(hashtag_trends)
                all_trends.extend(pattern_trends)
                
                # Save to database
                trend_detector.save_trends(all_trends)
        
        logger.info("Trend detection completed successfully")
        
    except Exception as e:
        logger.error(f"Error during trend detection: {str(e)}", exc_info=True)
    finally:
        db.close()


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description="Run trend detection algorithms")
    parser.add_argument(
        "--window", 
        choices=["realtime", "short", "medium", "long", "all"], 
        default="all",
        help="Time window for trend detection"
    )
    parser.add_argument(
        "--platform", 
        choices=["youtube", "instagram", "threads", "rednote", "all"], 
        default="all",
        help="Platform filter"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Run without saving to database"
    )
    
    args = parser.parse_args()
    
    # Convert platform string to enum if not 'all'
    platform = None
    if args.platform != "all":
        platform = PlatformType(args.platform)
    
    # Run trend detection
    run_trend_detection(
        window_name=args.window,
        platform=platform,
        save_to_db=not args.dry_run
    )


if __name__ == "__main__":
    main() 