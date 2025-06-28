"""
Analytics Engine
Main orchestrator for analytics operations including data processing, 
metrics calculation, and performance scoring
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from .data_processor import DataProcessor, ProcessedMetrics
from .metrics_calculator import MetricsCalculator, AdvancedMetrics
from .scoring_algorithm import ScoringAlgorithm, ScoreBreakdown
from db.models import Post, AnalyticsData, PlatformType
from db.database import SessionLocal

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """Main analytics engine for processing and analyzing social media content"""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or SessionLocal()
        self.data_processor = DataProcessor(self.db)
        self.metrics_calculator = MetricsCalculator()
        self.scoring_algorithm = ScoringAlgorithm()
    
    def analyze_post(self, post_id: int) -> Dict[str, Any]:
        """
        Analyze a single post and store results
        
        Args:
            post_id: ID of the post to analyze
            
        Returns:
            Dictionary containing analysis results
        """
        processing_start_time = datetime.now(timezone.utc)
        
        try:
            # Get post from database
            post = self.db.query(Post).filter(Post.id == post_id).first()
            if not post:
                raise ValueError(f"Post with ID {post_id} not found")
            
            # Process the post data
            processed_metrics = self.data_processor.process_post(post)
            
            # Calculate advanced metrics
            advanced_metrics = self.metrics_calculator.calculate_advanced_metrics(processed_metrics)
            
            # Calculate performance score with detailed breakdown
            score_breakdown = self.scoring_algorithm.calculate_score_detailed(
                advanced_metrics, 
                processed_metrics
            )
            performance_score = score_breakdown.final_score
            
            # Create or update analytics data with full details
            analytics_data = self._create_or_update_analytics_data(
                post, 
                processed_metrics, 
                advanced_metrics, 
                performance_score,
                score_breakdown,
                processing_start_time
            )
            
            # Update post flags
            post.is_analyzed = True
            post.performance_score = performance_score
            
            # Commit changes
            self.db.commit()
            
            return {
                "success": True,
                "post_id": post_id,
                "performance_score": performance_score,
                "analytics_id": analytics_data.id,
                "processed_metrics": {
                    "engagement_rate": processed_metrics.engagement_rate,
                    "total_engagement": processed_metrics.total_engagement,
                    "views": processed_metrics.views
                },
                "advanced_metrics": {
                    "virality_score": advanced_metrics.virality_score,
                    "trend_score": advanced_metrics.trend_score,
                    "content_quality_score": advanced_metrics.content_quality_score,
                    "success_patterns": advanced_metrics.success_patterns
                },
                "score_breakdown": {
                    "final_score": score_breakdown.final_score,
                    "confidence_score": score_breakdown.confidence_score,
                    "platform_adjustment": score_breakdown.platform_adjustment,
                    "bonuses_applied": len(score_breakdown.bonuses) if score_breakdown.bonuses else 0
                },
                "processing_time": analytics_data.processing_duration
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error analyzing post {post_id}: {str(e)}")
            return {
                "success": False,
                "post_id": post_id,
                "error": str(e)
            }
    
    def analyze_post_detailed(self, post_id: int) -> Optional[Dict[str, Any]]:
        """
        Analyze a single post with detailed score breakdown
        
        Args:
            post_id: ID of the post to analyze
            
        Returns:
            Dict containing analytics data and detailed score breakdown
        """
        processing_start_time = datetime.now(timezone.utc)
        
        try:
            # Get the post
            post = self.db.query(Post).filter(Post.id == post_id).first()
            if not post:
                logger.error(f"Post with ID {post_id} not found")
                return None
            
            # Process the post data
            processed_metrics = self.data_processor.process_post(post)
            
            # Calculate advanced metrics
            advanced_metrics = self.metrics_calculator.calculate_advanced_metrics(processed_metrics)
            
            # Calculate detailed score breakdown
            score_breakdown = self.scoring_algorithm.calculate_score_detailed(
                advanced_metrics, processed_metrics
            )
            
            # Create or update analytics data with full details
            analytics_data = self._create_or_update_analytics_data(
                post, 
                processed_metrics, 
                advanced_metrics, 
                score_breakdown.final_score,
                score_breakdown,
                processing_start_time
            )
            
            # Mark post as analyzed
            post.is_analyzed = True
            post.performance_score = score_breakdown.final_score
            
            # Commit changes
            self.db.commit()
            
            return {
                'analytics_data': analytics_data,
                'processed_metrics': processed_metrics,
                'advanced_metrics': advanced_metrics,
                'score_breakdown': score_breakdown
            }
            
        except Exception as e:
            logger.error(f"Error analyzing post {post_id} with details: {str(e)}")
            self.db.rollback()
            return None
    
    def analyze_batch_posts(self, post_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Analyze multiple posts in batch
        
        Args:
            post_ids: List of post IDs to analyze
            
        Returns:
            List[Dict]: List of analysis results
        """
        results = []
        
        for post_id in post_ids:
            result = self.analyze_post(post_id)
            if result.get('success'):
                results.append(result)
        
        logger.info(f"Batch analysis completed: {len(results)}/{len(post_ids)} posts analyzed")
        return results
    
    def analyze_unprocessed_posts(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Analyze all unprocessed posts
        
        Args:
            limit: Maximum number of posts to process
            
        Returns:
            List[Dict]: List of analysis results
        """
        # Get unprocessed posts
        query = self.db.query(Post).filter(Post.is_analyzed == False)
        if limit:
            query = query.limit(limit)
        
        unprocessed_posts = query.all()
        post_ids = [post.id for post in unprocessed_posts]
        
        logger.info(f"Found {len(post_ids)} unprocessed posts")
        return self.analyze_batch_posts(post_ids)
    
    def analyze_platform_posts(self, platform: PlatformType, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Analyze posts from a specific platform
        
        Args:
            platform: Platform to analyze posts from
            limit: Maximum number of posts to process
            
        Returns:
            List[Dict]: List of analysis results
        """
        # Get posts from the specified platform
        query = self.db.query(Post).filter(
            Post.platform == platform,
            Post.is_analyzed == False
        )
        if limit:
            query = query.limit(limit)
        
        platform_posts = query.all()
        post_ids = [post.id for post in platform_posts]
        
        logger.info(f"Found {len(post_ids)} unprocessed {platform.value} posts")
        return self.analyze_batch_posts(post_ids)
    
    def reanalyze_post(self, post_id: int) -> Optional[AnalyticsData]:
        """
        Re-analyze a post (even if already analyzed)
        
        Args:
            post_id: ID of the post to re-analyze
            
        Returns:
            AnalyticsData: Updated analytics record or None if failed
        """
        try:
            # Get the post
            post = self.db.query(Post).filter(Post.id == post_id).first()
            if not post:
                logger.error(f"Post with ID {post_id} not found")
                return None
            
            # Temporarily mark as unanalyzed to force reprocessing
            original_analyzed_state = post.is_analyzed
            post.is_analyzed = False
            
            # Analyze the post
            result = self.analyze_post(post_id)
            
            # If analysis failed, restore original state
            if not result:
                post.is_analyzed = original_analyzed_state
                self.db.commit()
            
            return result
            
        except Exception as e:
            logger.error(f"Error re-analyzing post {post_id}: {str(e)}")
            self.db.rollback()
            return None
    
    def get_analytics_summary(self, platform: Optional[PlatformType] = None) -> Dict[str, Any]:
        """
        Get summary statistics for analytics data
        
        Args:
            platform: Optional platform filter
            
        Returns:
            Dict: Summary statistics
        """
        try:
            # Base query
            query = self.db.query(Post).filter(Post.is_analyzed == True)
            
            if platform:
                query = query.filter(Post.platform == platform)
            
            posts = query.all()
            
            if not posts:
                return {
                    "total_posts": 0,
                    "platform": platform.value if platform else "all",
                    "message": "No analyzed posts found"
                }
            
            # Calculate summary statistics
            total_posts = len(posts)
            avg_performance_score = sum(post.performance_score or 0 for post in posts) / total_posts
            
            # Get performance score distribution
            scores = [post.performance_score or 0 for post in posts]
            scores.sort()
            
            summary = {
                "total_posts": total_posts,
                "platform": platform.value if platform else "all",
                "average_performance_score": round(avg_performance_score, 2),
                "min_score": min(scores),
                "max_score": max(scores),
                "median_score": scores[len(scores) // 2] if scores else 0,
                "score_distribution": {
                    "excellent": len([s for s in scores if s >= 80]),
                    "good": len([s for s in scores if 60 <= s < 80]),
                    "average": len([s for s in scores if 40 <= s < 60]),
                    "poor": len([s for s in scores if s < 40])
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating analytics summary: {str(e)}")
            return {"error": str(e)}
    
    def _create_or_update_analytics_data(
        self, 
        post: Post, 
        processed_metrics: ProcessedMetrics,
        advanced_metrics: AdvancedMetrics,
        performance_score: float,
        score_breakdown: Optional[ScoreBreakdown] = None,
        processing_start_time: Optional[datetime] = None
    ) -> AnalyticsData:
        """
        Create or update analytics data for a post
        
        Args:
            post: Post model instance
            processed_metrics: Processed metrics data
            advanced_metrics: Advanced calculated metrics
            performance_score: Overall performance score
            score_breakdown: Optional detailed score breakdown
            processing_start_time: Optional start time for processing duration calculation
            
        Returns:
            AnalyticsData: Created or updated analytics record
        """
        # Check if analytics data already exists
        existing_analytics = self.db.query(AnalyticsData).filter(
            AnalyticsData.post_id == post.id
        ).first()
        
        if existing_analytics:
            # Update existing record
            analytics_data = existing_analytics
            analytics_data.analyzed_at = datetime.now(timezone.utc)
        else:
            # Create new record
            analytics_data = AnalyticsData(post_id=post.id)
        
        # Core performance metrics
        analytics_data.engagement_rate = processed_metrics.engagement_rate
        analytics_data.performance_score = performance_score
        
        # Advanced metrics from MetricsCalculator
        analytics_data.virality_score = advanced_metrics.virality_score
        analytics_data.trend_score = advanced_metrics.trend_score
        analytics_data.engagement_velocity = advanced_metrics.engagement_velocity
        analytics_data.content_quality_score = advanced_metrics.content_quality_score
        analytics_data.audience_reach_score = advanced_metrics.audience_reach_score
        analytics_data.interaction_depth_score = advanced_metrics.interaction_depth_score
        
        # Scoring breakdown components (if available)
        if score_breakdown:
            analytics_data.weighted_components = score_breakdown.weighted_components
            analytics_data.applied_bonuses = score_breakdown.bonuses
            analytics_data.applied_penalties = score_breakdown.penalties
            analytics_data.platform_adjustment = score_breakdown.platform_adjustment
            analytics_data.confidence_score = score_breakdown.confidence_score
        else:
            # Calculate basic confidence if no breakdown provided
            analytics_data.confidence_score = self._calculate_basic_confidence(processed_metrics)
            analytics_data.platform_adjustment = 1.0
        
        # Time-based metrics
        if processed_metrics.publish_date:
            now = datetime.now(timezone.utc)
            days_since_publish = (now - processed_metrics.publish_date).days
            analytics_data.days_since_publish = days_since_publish
            
            # Estimate peak engagement hour (simplified - could be enhanced)
            analytics_data.peak_engagement_hour = processed_metrics.publish_date.hour
        
        # Pattern recognition and features
        analytics_data.success_patterns = advanced_metrics.success_patterns
        analytics_data.content_features = advanced_metrics.content_features
        
        # Processing metadata
        analytics_data.algorithm_version = "1.0"
        
        if processing_start_time:
            processing_duration = (datetime.now(timezone.utc) - processing_start_time).total_seconds()
            analytics_data.processing_duration = processing_duration
        
        # Data quality flags
        quality_flags = self._assess_data_quality(processed_metrics, advanced_metrics)
        analytics_data.data_quality_flags = quality_flags
        
        # Add to session if new
        if not existing_analytics:
            self.db.add(analytics_data)
        
        return analytics_data
    
    def _calculate_basic_confidence(self, processed_metrics: ProcessedMetrics) -> float:
        """Calculate basic confidence score when detailed breakdown is not available"""
        confidence_factors = []
        
        # Data completeness
        if processed_metrics.views > 0:
            confidence_factors.append(25)
        if processed_metrics.total_engagement > 0:
            confidence_factors.append(25)
        if processed_metrics.publish_date:
            confidence_factors.append(20)
        
        # Sample size confidence
        if processed_metrics.views > 1000:
            confidence_factors.append(30)
        elif processed_metrics.views > 100:
            confidence_factors.append(15)
        
        return min(sum(confidence_factors), 100)
    
    def _assess_data_quality(
        self, 
        processed_metrics: ProcessedMetrics, 
        advanced_metrics: AdvancedMetrics
    ) -> Dict[str, Any]:
        """Assess data quality and return flags for any issues"""
        flags = {}
        
        # Check for missing critical data
        if processed_metrics.views == 0:
            flags['no_views_data'] = True
        
        if processed_metrics.total_engagement == 0:
            flags['no_engagement_data'] = True
        
        if not processed_metrics.publish_date:
            flags['missing_publish_date'] = True
        
        # Check for suspicious data patterns
        if processed_metrics.engagement_rate > 50:  # Unrealistically high engagement
            flags['suspicious_high_engagement'] = True
        
        if processed_metrics.total_engagement > processed_metrics.views:
            flags['engagement_exceeds_views'] = True
        
        # Check for low confidence indicators
        if processed_metrics.views < 10:
            flags['very_low_sample_size'] = True
        
        # Check algorithm-specific issues
        if advanced_metrics.confidence_score and advanced_metrics.confidence_score < 30:
            flags['low_algorithm_confidence'] = True
        
        return flags if flags else None 