"""
Test script for pattern recognition functionality
"""

import sys
import os
import logging
from datetime import datetime, timezone, timedelta
import json

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.database import SessionLocal
from db.models import Post, AnalyticsData, PlatformType, ContentType
from analytics.engine import AnalyticsEngine
from analytics.pattern_recognizer import PatternRecognizer
from analytics.data_processor import ProcessedMetrics
from analytics.metrics_calculator import AdvancedMetrics

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_post(db, platform, content_type, high_engagement=False):
    """Create a test post with specified characteristics"""
    now = datetime.now(timezone.utc)
    
    # Create engagement metrics based on desired characteristics
    if high_engagement:
        engagement_metrics = {
            'views': 10000,
            'likes': 2000,
            'comments': 500,
            'shares': 300,
            'saves': 150
        }
    else:
        engagement_metrics = {
            'views': 1000,
            'likes': 50,
            'comments': 10,
            'shares': 5,
            'saves': 2
        }
    
    # Create post with specified characteristics
    post = Post(
        platform=platform,
        content_type=content_type,
        url=f"https://example.com/test_{platform.value}_{content_type.value}_{now.timestamp()}",
        title=f"Test {platform.value} {content_type.value} Post",
        description="This is a test post for pattern recognition",
        content_text="Sample content text for testing pattern recognition",
        author="test_user",
        publish_date=now - timedelta(hours=12),
        hashtags=["test", "pattern", "recognition"],
        mentions=["user1", "user2"],
        engagement_metrics=engagement_metrics,
        duration=120 if content_type == ContentType.VIDEO else None
    )
    
    db.add(post)
    db.commit()
    db.refresh(post)
    
    return post


def test_pattern_recognition():
    """Test pattern recognition functionality"""
    db = SessionLocal()
    engine = AnalyticsEngine(db)
    pattern_recognizer = PatternRecognizer(db)
    
    try:
        # Create test posts with different characteristics
        logger.info("Creating test posts...")
        
        # High engagement video post
        video_post = create_test_post(
            db, 
            PlatformType.YOUTUBE, 
            ContentType.VIDEO, 
            high_engagement=True
        )
        
        # High engagement image post
        image_post = create_test_post(
            db, 
            PlatformType.INSTAGRAM, 
            ContentType.IMAGE, 
            high_engagement=True
        )
        
        # Regular text post
        text_post = create_test_post(
            db, 
            PlatformType.THREADS, 
            ContentType.TEXT, 
            high_engagement=False
        )
        
        # Analyze posts
        logger.info("Analyzing posts...")
        
        # Analyze video post
        video_result = engine.analyze_post(video_post.id)
        logger.info(f"Video post analysis result: {json.dumps(video_result, default=str, indent=2)}")
        
        # Analyze image post
        image_result = engine.analyze_post(image_post.id)
        logger.info(f"Image post analysis result: {json.dumps(image_result, default=str, indent=2)}")
        
        # Analyze text post
        text_result = engine.analyze_post(text_post.id)
        logger.info(f"Text post analysis result: {json.dumps(text_result, default=str, indent=2)}")
        
        # Check for detected patterns
        logger.info("Checking detected patterns...")
        
        # Get analytics data
        video_analytics = db.query(AnalyticsData).filter(AnalyticsData.post_id == video_post.id).first()
        image_analytics = db.query(AnalyticsData).filter(AnalyticsData.post_id == image_post.id).first()
        text_analytics = db.query(AnalyticsData).filter(AnalyticsData.post_id == text_post.id).first()
        
        if video_analytics and video_analytics.success_patterns:
            logger.info(f"Video post patterns: {json.dumps(video_analytics.success_patterns, indent=2)}")
        else:
            logger.warning("No patterns detected for video post")
            
        if image_analytics and image_analytics.success_patterns:
            logger.info(f"Image post patterns: {json.dumps(image_analytics.success_patterns, indent=2)}")
        else:
            logger.warning("No patterns detected for image post")
            
        if text_analytics and text_analytics.success_patterns:
            logger.info(f"Text post patterns: {json.dumps(text_analytics.success_patterns, indent=2)}")
        else:
            logger.warning("No patterns detected for text post")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Starting pattern recognition test...")
    test_pattern_recognition()
    logger.info("Pattern recognition test completed.") 