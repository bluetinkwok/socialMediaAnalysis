"""
Trend Detector Module
Implements statistical analysis methods for identifying trends in social media content.
"""

import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from db.models import Post, AnalyticsData, TrendData, PlatformType, ContentType
from db.database import SessionLocal

logger = logging.getLogger(__name__)


@dataclass
class TrendWindow:
    """Time window for trend analysis"""
    name: str
    duration: timedelta
    min_posts: int  # Minimum posts needed for analysis
    z_score_threshold: float  # Standard deviations above mean for trend detection
    
    @property
    def start_date(self) -> datetime:
        """Get start date for the window based on current time"""
        return datetime.now(tz=timezone.utc) - self.duration


class TrendType:
    """Types of trends that can be detected"""
    PERFORMANCE = "performance"  # Overall performance trends
    VIRAL = "viral"  # Viral content detection
    RISING = "rising"  # Rising engagement patterns
    QUALITY = "quality"  # High-quality content trends
    HASHTAG = "hashtag"  # Trending hashtags
    PATTERN = "pattern"  # Content pattern trends


class TrendDetector:
    """Main class for detecting trends in social media content"""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or SessionLocal()
        
        # Define analysis windows
        self.windows = {
            "realtime": TrendWindow(
                name="realtime",
                duration=timedelta(hours=24),
                min_posts=10,
                z_score_threshold=2.0
            ),
            "short": TrendWindow(
                name="short",
                duration=timedelta(days=7),
                min_posts=20,
                z_score_threshold=2.0
            ),
            "medium": TrendWindow(
                name="medium",
                duration=timedelta(days=30),
                min_posts=50,
                z_score_threshold=2.5
            ),
            "long": TrendWindow(
                name="long",
                duration=timedelta(days=90),
                min_posts=100,
                z_score_threshold=3.0
            )
        }
        
        # Platform-specific minimum engagement thresholds
        self.min_engagement = {
            PlatformType.YOUTUBE: {
                "views": 1000,
                "likes": 50,
                "comments": 10
            },
            PlatformType.INSTAGRAM: {
                "likes": 100,
                "comments": 5,
                "saves": 10
            },
            PlatformType.THREADS: {
                "likes": 50,
                "replies": 5,
                "reposts": 3
            },
            PlatformType.REDNOTE: {
                "likes": 30,
                "comments": 5,
                "collections": 3
            }
        }
    
    def detect_performance_trends(
        self, 
        window: str = "short",
        platform: Optional[PlatformType] = None,
        content_type: Optional[ContentType] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect posts with significantly higher performance scores
        
        Args:
            window: Analysis window ('realtime', 'short', 'medium', 'long')
            platform: Optional platform filter
            content_type: Optional content type filter
            
        Returns:
            List of trending posts with scores and statistics
        """
        window_obj = self.windows[window]
        
        # Base query for analytics data within window
        query = self.db.query(AnalyticsData).join(Post)
        query = query.filter(
            and_(
                Post.publish_date >= window_obj.start_date,
                AnalyticsData.confidence_score >= 70,
                Post.is_analyzed == True
            )
        )
        
        # Apply filters
        if platform:
            query = query.filter(Post.platform == platform)
        if content_type:
            query = query.filter(Post.content_type == content_type)
            
        # Get performance scores
        scores = [record.performance_score for record in query.all()]
        
        if len(scores) < window_obj.min_posts:
            logger.warning(f"Insufficient data for {window} window analysis")
            return []
            
        # Calculate statistics
        mean_score = np.mean(scores)
        std_score = np.std(scores)
        threshold = mean_score + (window_obj.z_score_threshold * std_score)
        
        # Find trending posts
        trending = query.filter(AnalyticsData.performance_score >= threshold)
        trending = trending.order_by(desc(AnalyticsData.performance_score))
        
        return [
            {
                "post_id": record.post_id,
                "performance_score": record.performance_score,
                "z_score": (record.performance_score - mean_score) / std_score,
                "platform": record.post.platform.value,
                "content_type": record.post.content_type.value,
                "publish_date": record.post.publish_date,
                "trend_type": TrendType.PERFORMANCE,
                "window": window
            }
            for record in trending.all()
        ]
    
    def detect_viral_content(
        self,
        window: str = "realtime",
        platform: Optional[PlatformType] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect potentially viral content based on virality score and velocity
        
        Args:
            window: Analysis window ('realtime', 'short', 'medium', 'long')
            platform: Optional platform filter
            
        Returns:
            List of viral posts with scores and statistics
        """
        window_obj = self.windows[window]
        
        # Query for potential viral content
        query = self.db.query(AnalyticsData).join(Post)
        query = query.filter(
            and_(
                Post.publish_date >= window_obj.start_date,
                AnalyticsData.confidence_score >= 70,
                AnalyticsData.virality_score >= 80,
                AnalyticsData.engagement_velocity > 0
            )
        )
        
        if platform:
            query = query.filter(Post.platform == platform)
            
        # Get velocity scores for threshold calculation
        velocities = [record.engagement_velocity for record in query.all()]
        
        if len(velocities) < window_obj.min_posts:
            logger.warning(f"Insufficient data for viral detection in {window} window")
            return []
            
        # Calculate velocity threshold
        mean_velocity = np.mean(velocities)
        std_velocity = np.std(velocities)
        velocity_threshold = mean_velocity + std_velocity
        
        # Filter for high velocity content
        viral = query.filter(AnalyticsData.engagement_velocity >= velocity_threshold)
        viral = viral.order_by(desc(AnalyticsData.virality_score))
        
        return [
            {
                "post_id": record.post_id,
                "virality_score": record.virality_score,
                "engagement_velocity": record.engagement_velocity,
                "velocity_percentile": (
                    (record.engagement_velocity - mean_velocity) / std_velocity
                    if std_velocity > 0 else 0
                ),
                "platform": record.post.platform.value,
                "publish_date": record.post.publish_date,
                "trend_type": TrendType.VIRAL,
                "window": window
            }
            for record in viral.all()
        ]
    
    def detect_rising_trends(
        self,
        window: str = "short",
        platform: Optional[PlatformType] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect content with rising engagement trends
        
        Args:
            window: Analysis window ('realtime', 'short', 'medium', 'long')
            platform: Optional platform filter
            
        Returns:
            List of rising trend posts with scores and statistics
        """
        window_obj = self.windows[window]
        
        # Query for potential rising trends
        query = self.db.query(AnalyticsData).join(Post)
        query = query.filter(
            and_(
                Post.publish_date >= window_obj.start_date,
                AnalyticsData.confidence_score >= 70,
                AnalyticsData.trend_score >= 70
            )
        )
        
        if platform:
            query = query.filter(Post.platform == platform)
            
        # Calculate platform average velocity
        avg_velocity = query.with_entities(
            func.avg(AnalyticsData.engagement_velocity)
        ).scalar() or 0
        
        # Find rising trends
        rising = query.filter(AnalyticsData.engagement_velocity > avg_velocity)
        rising = rising.order_by(desc(AnalyticsData.trend_score))
        
        return [
            {
                "post_id": record.post_id,
                "trend_score": record.trend_score,
                "engagement_velocity": record.engagement_velocity,
                "velocity_ratio": record.engagement_velocity / avg_velocity if avg_velocity > 0 else 0,
                "platform": record.post.platform.value,
                "publish_date": record.post.publish_date,
                "trend_type": TrendType.RISING,
                "window": window
            }
            for record in rising.all()
        ]
    
    def detect_quality_trends(
        self,
        window: str = "medium",
        platform: Optional[PlatformType] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect high-quality content trends
        
        Args:
            window: Analysis window ('realtime', 'short', 'medium', 'long')
            platform: Optional platform filter
            
        Returns:
            List of high-quality trending posts with scores
        """
        window_obj = self.windows[window]
        
        # Query for high-quality content
        query = self.db.query(AnalyticsData).join(Post)
        query = query.filter(
            and_(
                Post.publish_date >= window_obj.start_date,
                AnalyticsData.confidence_score >= 70,
                AnalyticsData.content_quality_score >= 85
            )
        )
        
        if platform:
            query = query.filter(Post.platform == platform)
            
        # Calculate average reach score
        avg_reach = query.with_entities(
            func.avg(AnalyticsData.audience_reach_score)
        ).scalar() or 0
        
        # Find quality trends with good reach
        quality = query.filter(AnalyticsData.audience_reach_score > avg_reach)
        quality = quality.order_by(desc(AnalyticsData.content_quality_score))
        
        return [
            {
                "post_id": record.post_id,
                "quality_score": record.content_quality_score,
                "reach_score": record.audience_reach_score,
                "reach_ratio": record.audience_reach_score / avg_reach if avg_reach > 0 else 0,
                "platform": record.post.platform.value,
                "publish_date": record.post.publish_date,
                "trend_type": TrendType.QUALITY,
                "window": window
            }
            for record in quality.all()
        ]
    
    def detect_hashtag_trends(
        self,
        window: str = "short",
        platform: Optional[PlatformType] = None,
        min_occurrences: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Detect trending hashtags
        
        Args:
            window: Analysis window ('realtime', 'short', 'medium', 'long')
            platform: Optional platform filter
            min_occurrences: Minimum number of occurrences to consider
            
        Returns:
            List of trending hashtags with statistics
        """
        window_obj = self.windows[window]
        
        # Query posts with hashtags
        query = self.db.query(Post)
        query = query.filter(
            and_(
                Post.publish_date >= window_obj.start_date,
                Post.hashtags != None,
                Post.is_analyzed == True
            )
        )
        
        if platform:
            query = query.filter(Post.platform == platform)
            
        posts = query.all()
        
        if len(posts) < window_obj.min_posts:
            logger.warning(f"Insufficient data for hashtag analysis in {window} window")
            return []
            
        # Count hashtag occurrences and total engagement
        hashtag_stats = {}
        for post in posts:
            if not post.hashtags:
                continue
                
            engagement = sum(post.engagement_metrics.values()) if post.engagement_metrics else 0
            
            for tag in post.hashtags:
                if tag not in hashtag_stats:
                    hashtag_stats[tag] = {"count": 0, "engagement": 0}
                hashtag_stats[tag]["count"] += 1
                hashtag_stats[tag]["engagement"] += engagement
        
        # Filter and sort trending hashtags
        trending_tags = []
        for tag, stats in hashtag_stats.items():
            if stats["count"] >= min_occurrences:
                trending_tags.append({
                    "hashtag": tag,
                    "occurrences": stats["count"],
                    "total_engagement": stats["engagement"],
                    "avg_engagement": stats["engagement"] / stats["count"],
                    "platform": platform.value if platform else "all",
                    "trend_type": TrendType.HASHTAG,
                    "window": window
                })
        
        return sorted(
            trending_tags,
            key=lambda x: (x["occurrences"], x["total_engagement"]),
            reverse=True
        )
    
    def detect_content_patterns(
        self,
        window: str = "medium",
        platform: Optional[PlatformType] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect successful content patterns
        
        Args:
            window: Analysis window ('realtime', 'short', 'medium', 'long')
            platform: Optional platform filter
            
        Returns:
            List of trending content patterns with statistics
        """
        window_obj = self.windows[window]
        
        # Query for posts with success patterns
        query = self.db.query(AnalyticsData).join(Post)
        query = query.filter(
            and_(
                Post.publish_date >= window_obj.start_date,
                AnalyticsData.confidence_score >= 70,
                AnalyticsData.success_patterns != None
            )
        )
        
        if platform:
            query = query.filter(Post.platform == platform)
            
        records = query.all()
        
        if len(records) < window_obj.min_posts:
            logger.warning(f"Insufficient data for pattern analysis in {window} window")
            return []
            
        # Aggregate pattern occurrences and performance
        pattern_stats = {}
        for record in records:
            if not record.success_patterns:
                continue
                
            for pattern in record.success_patterns:
                if pattern not in pattern_stats:
                    pattern_stats[pattern] = {
                        "count": 0,
                        "total_score": 0,
                        "posts": []
                    }
                pattern_stats[pattern]["count"] += 1
                pattern_stats[pattern]["total_score"] += record.performance_score
                pattern_stats[pattern]["posts"].append(record.post_id)
        
        # Filter and format trending patterns
        trending_patterns = []
        for pattern, stats in pattern_stats.items():
            if stats["count"] >= 3:  # Minimum pattern occurrences
                trending_patterns.append({
                    "pattern": pattern,
                    "occurrences": stats["count"],
                    "avg_performance": stats["total_score"] / stats["count"],
                    "example_posts": stats["posts"][:3],  # Top 3 examples
                    "platform": platform.value if platform else "all",
                    "trend_type": TrendType.PATTERN,
                    "window": window
                })
        
        return sorted(
            trending_patterns,
            key=lambda x: (x["occurrences"], x["avg_performance"]),
            reverse=True
        )
    
    def save_trends(self, trends: List[Dict[str, Any]]) -> None:
        """
        Save detected trends to the database
        
        Args:
            trends: List of trend dictionaries to save
        """
        for trend in trends:
            trend_data = TrendData(
                trend_type=trend["trend_type"],
                trend_value=str(trend.get("post_id", trend.get("hashtag", trend.get("pattern", "")))),
                platform=trend.get("platform"),
                occurrence_count=trend.get("occurrences", 1),
                engagement_sum=trend.get("total_engagement", 0),
                trend_score=trend.get("performance_score", trend.get("virality_score", 0.0)),
                window_start=self.windows[trend["window"]].start_date,
                window_end=datetime.now(tz=timezone.utc)
            )
            self.db.add(trend_data)
        
        try:
            self.db.commit()
            logger.info(f"Saved {len(trends)} trends to database")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving trends: {str(e)}")
    
    def analyze_all_trends(
        self,
        window: str = "short",
        platform: Optional[PlatformType] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Run all trend detection methods and return combined results
        
        Args:
            window: Analysis window ('realtime', 'short', 'medium', 'long')
            platform: Optional platform filter
            
        Returns:
            Dictionary of trend types and their detected trends
        """
        all_trends = {
            "performance": self.detect_performance_trends(window, platform),
            "viral": self.detect_viral_content(window, platform),
            "rising": self.detect_rising_trends(window, platform),
            "quality": self.detect_quality_trends(window, platform),
            "hashtags": self.detect_hashtag_trends(window, platform),
            "patterns": self.detect_content_patterns(window, platform)
        }
        
        # Save all detected trends
        for trend_list in all_trends.values():
            if trend_list:
                self.save_trends(trend_list)
        
        return all_trends 