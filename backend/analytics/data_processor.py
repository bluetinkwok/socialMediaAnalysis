"""
Analytics Data Processor
Handles ingestion and preprocessing of post data for analytics calculations
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session

from db.models import Post, PlatformType, ContentType, AnalyticsData
from db.database import SessionLocal

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of engagement metrics"""
    VIEWS = "views"
    LIKES = "likes"
    COMMENTS = "comments"
    SHARES = "shares"
    SAVES = "saves"
    REACTIONS = "reactions"
    FOLLOWS = "follows"
    CLICKS = "clicks"


@dataclass
class ProcessedMetrics:
    """Standardized metrics structure"""
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    reactions: int = 0
    follows: int = 0
    clicks: int = 0
    
    # Calculated metrics
    total_engagement: int = 0
    engagement_rate: float = 0.0
    
    # Metadata
    platform: str = ""
    content_type: str = ""
    author: str = ""
    publish_date: Optional[datetime] = None
    
    def calculate_totals(self):
        """Calculate derived metrics"""
        self.total_engagement = (
            self.likes + self.comments + self.shares + 
            self.saves + self.reactions + self.follows + self.clicks
        )
        
        if self.views > 0:
            self.engagement_rate = (self.total_engagement / self.views) * 100
        else:
            self.engagement_rate = 0.0


class DataProcessor:
    """Main data processor for analytics engine"""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or SessionLocal()
        self.platform_processors = {
            PlatformType.YOUTUBE: self._process_youtube_metrics,
            PlatformType.INSTAGRAM: self._process_instagram_metrics,
            PlatformType.THREADS: self._process_threads_metrics,
            PlatformType.REDNOTE: self._process_rednote_metrics,
        }
    
    def process_post_data(self, post: Post) -> ProcessedMetrics:
        """
        Process a single post's data into standardized metrics
        
        Args:
            post: Post model instance
            
        Returns:
            ProcessedMetrics: Standardized metrics object
        """
        try:
            # Get platform-specific processor
            processor = self.platform_processors.get(post.platform)
            if not processor:
                logger.warning(f"No processor found for platform: {post.platform}")
                return self._create_empty_metrics(post)
            
            # Process metrics using platform-specific logic
            metrics = processor(post)
            
            # Add common metadata
            metrics.platform = post.platform.value
            metrics.content_type = post.content_type.value
            metrics.author = post.author
            metrics.publish_date = post.publish_date
            
            # Calculate derived metrics
            metrics.calculate_totals()
            
            logger.info(f"Processed metrics for post {post.id}: {metrics.total_engagement} total engagement")
            return metrics
            
        except Exception as e:
            logger.error(f"Error processing post {post.id}: {str(e)}")
            return self._create_empty_metrics(post)
    
    def process_batch_posts(self, posts: List[Post]) -> List[ProcessedMetrics]:
        """
        Process multiple posts in batch
        
        Args:
            posts: List of Post model instances
            
        Returns:
            List[ProcessedMetrics]: List of processed metrics
        """
        processed_metrics = []
        
        for post in posts:
            metrics = self.process_post_data(post)
            processed_metrics.append(metrics)
        
        logger.info(f"Processed {len(processed_metrics)} posts in batch")
        return processed_metrics
    
    def get_unprocessed_posts(self, limit: Optional[int] = None) -> List[Post]:
        """
        Get posts that haven't been analyzed yet
        
        Args:
            limit: Maximum number of posts to return
            
        Returns:
            List[Post]: Unprocessed posts
        """
        query = self.db.query(Post).filter(Post.is_analyzed == False)
        
        if limit:
            query = query.limit(limit)
            
        posts = query.all()
        logger.info(f"Found {len(posts)} unprocessed posts")
        return posts
    
    def get_posts_by_platform(self, platform: PlatformType, limit: Optional[int] = None) -> List[Post]:
        """
        Get posts from a specific platform
        
        Args:
            platform: Platform type
            limit: Maximum number of posts to return
            
        Returns:
            List[Post]: Posts from the specified platform
        """
        query = self.db.query(Post).filter(Post.platform == platform)
        
        if limit:
            query = query.limit(limit)
            
        posts = query.all()
        logger.info(f"Found {len(posts)} posts from {platform.value}")
        return posts
    
    def _process_youtube_metrics(self, post: Post) -> ProcessedMetrics:
        """Process YouTube-specific metrics"""
        metrics = ProcessedMetrics()
        
        if post.engagement_metrics:
            metrics.views = post.engagement_metrics.get('views', 0)
            metrics.likes = post.engagement_metrics.get('likes', 0)
            metrics.comments = post.engagement_metrics.get('comments', 0)
            metrics.shares = post.engagement_metrics.get('shares', 0)
            # YouTube doesn't have saves/reactions in the same way
            metrics.saves = 0
            metrics.reactions = 0
            metrics.follows = post.engagement_metrics.get('subscribers_gained', 0)
            metrics.clicks = post.engagement_metrics.get('clicks', 0)
        
        return metrics
    
    def _process_instagram_metrics(self, post: Post) -> ProcessedMetrics:
        """Process Instagram-specific metrics"""
        metrics = ProcessedMetrics()
        
        if post.engagement_metrics:
            metrics.views = post.engagement_metrics.get('views', 0)
            metrics.likes = post.engagement_metrics.get('likes', 0)
            metrics.comments = post.engagement_metrics.get('comments', 0)
            metrics.shares = post.engagement_metrics.get('shares', 0)
            metrics.saves = post.engagement_metrics.get('saves', 0)
            metrics.reactions = post.engagement_metrics.get('reactions', 0)
            metrics.follows = post.engagement_metrics.get('follows', 0)
            metrics.clicks = post.engagement_metrics.get('profile_clicks', 0)
        
        return metrics
    
    def _process_threads_metrics(self, post: Post) -> ProcessedMetrics:
        """Process Threads-specific metrics"""
        metrics = ProcessedMetrics()
        
        if post.engagement_metrics:
            # Threads uses similar metrics to Instagram
            metrics.views = post.engagement_metrics.get('views', 0)
            metrics.likes = post.engagement_metrics.get('likes', 0)
            metrics.comments = post.engagement_metrics.get('replies', 0)  # Threads calls them replies
            metrics.shares = post.engagement_metrics.get('reposts', 0)  # Threads calls them reposts
            metrics.saves = post.engagement_metrics.get('saves', 0)
            metrics.reactions = post.engagement_metrics.get('reactions', 0)
            metrics.follows = post.engagement_metrics.get('follows', 0)
            metrics.clicks = post.engagement_metrics.get('clicks', 0)
        
        return metrics
    
    def _process_rednote_metrics(self, post: Post) -> ProcessedMetrics:
        """Process RedNote-specific metrics"""
        metrics = ProcessedMetrics()
        
        if post.engagement_metrics:
            metrics.views = post.engagement_metrics.get('views', 0)
            metrics.likes = post.engagement_metrics.get('likes', 0)
            metrics.comments = post.engagement_metrics.get('comments', 0)
            metrics.shares = post.engagement_metrics.get('shares', 0)
            metrics.saves = post.engagement_metrics.get('collects', 0)  # RedNote calls them collects
            metrics.reactions = post.engagement_metrics.get('reactions', 0)
            metrics.follows = post.engagement_metrics.get('follows', 0)
            metrics.clicks = post.engagement_metrics.get('clicks', 0)
        
        return metrics
    
    def _create_empty_metrics(self, post: Post) -> ProcessedMetrics:
        """Create empty metrics structure for posts with no data"""
        metrics = ProcessedMetrics()
        metrics.platform = post.platform.value if post.platform else ""
        metrics.content_type = post.content_type.value if post.content_type else ""
        metrics.author = post.author or ""
        metrics.publish_date = post.publish_date
        return metrics
    
    def validate_metrics_data(self, metrics: ProcessedMetrics) -> bool:
        """
        Validate that metrics data is reasonable
        
        Args:
            metrics: ProcessedMetrics to validate
            
        Returns:
            bool: True if metrics are valid
        """
        # Basic validation rules
        if metrics.views < 0 or metrics.likes < 0 or metrics.comments < 0:
            return False
        
        # Engagement shouldn't exceed views (with some tolerance for edge cases)
        if metrics.views > 0 and metrics.total_engagement > metrics.views * 2:
            logger.warning(f"Suspicious metrics: engagement ({metrics.total_engagement}) > 2x views ({metrics.views})")
            return False
        
        # Engagement rate shouldn't be impossibly high
        if metrics.engagement_rate > 100:
            logger.warning(f"Suspicious engagement rate: {metrics.engagement_rate}%")
            return False
        
        return True 