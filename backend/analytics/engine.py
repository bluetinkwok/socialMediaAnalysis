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
from .pattern_recognizer import PatternRecognizer
from .nlp_analyzer import NLPAnalyzer
from .cv_analyzer import CVAnalyzer
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
        self.pattern_recognizer = PatternRecognizer(self.db)
        self.nlp_analyzer = NLPAnalyzer()
        self.cv_analyzer = CVAnalyzer()
        
        logger.info("Analytics Engine initialized with NLP and CV capabilities")
    
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
            
            # Perform NLP analysis
            nlp_results = self.nlp_analyzer.analyze_post(post)
            nlp_content_features = self.nlp_analyzer.extract_content_features(post)
            
            # Perform CV analysis if post has images or videos
            cv_results = {}
            cv_content_features = {}
            if post.images or post.videos:
                post_data = {
                    'images': post.images.split(',') if post.images else [],
                    'videos': post.videos.split(',') if post.videos else []
                }
                cv_results = self.cv_analyzer.analyze_content(post_data)
                cv_content_features = self.cv_analyzer.extract_content_features(post_data)
            
            # Update content quality score with NLP and CV insights
            nlp_content_quality = self.nlp_analyzer.calculate_content_quality_score(nlp_results)
            cv_content_quality = self.cv_analyzer.calculate_content_quality_score(post_data) if post.images or post.videos else 0
            
            # Combine NLP and CV quality scores
            if cv_content_quality > 0:
                # If we have both NLP and CV scores, use weighted average
                combined_quality = (nlp_content_quality * 0.6) + (cv_content_quality * 0.4)
            else:
                # If we only have NLP score, use that
                combined_quality = nlp_content_quality
            
            # Update the content quality score
            advanced_metrics.content_quality_score = combined_quality
            
            # Add NLP-identified patterns
            nlp_patterns = self.nlp_analyzer.identify_content_patterns(nlp_results)
            
            # Add CV-identified patterns
            cv_patterns = self.cv_analyzer.identify_visual_patterns(post_data) if post.images or post.videos else []
            
            # Apply enhanced pattern recognition
            enhanced_patterns = self.pattern_recognizer.recognize_patterns(
                post, processed_metrics, advanced_metrics
            )
            # Combine traditional patterns with NLP and CV identified patterns
            enhanced_patterns.extend(nlp_patterns)
            enhanced_patterns.extend(cv_patterns)
            advanced_metrics.success_patterns = enhanced_patterns
            
            # Calculate performance score with detailed breakdown
            score_breakdown = self.scoring_algorithm.calculate_score_detailed(
                advanced_metrics, 
                processed_metrics
            )
            performance_score = score_breakdown.final_score
            
            # Apply sentiment-based adjustment if applicable
            if "sentiment" in nlp_results and post.platform:
                sentiment_score = nlp_results["sentiment"]["score"]
                sentiment_boost = self.nlp_analyzer.get_sentiment_boost(
                    sentiment_score, 
                    post.platform.value
                )
                performance_score *= sentiment_boost
                score_breakdown.final_score = performance_score
            
            # Combine NLP and CV content features
            content_features = {**nlp_content_features}
            if cv_content_features:
                content_features.update(cv_content_features)
                # If both NLP and CV detected people/entities, mark as high-interest
                if nlp_content_features.get('has_entities', False) and cv_content_features.get('has_people', False):
                    content_features['high_interest_content'] = True
            
            # Create or update analytics data with full details
            analytics_data = self._create_or_update_analytics_data(
                post, 
                processed_metrics, 
                advanced_metrics, 
                performance_score,
                score_breakdown,
                processing_start_time,
                content_features=content_features
            )
            
            # Update post flags
            post.is_analyzed = True
            post.performance_score = performance_score
            
            # Commit changes
            self.db.commit()
            
            # Prepare response with combined NLP and CV analysis
            response = {
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
                "nlp_analysis": {
                    "sentiment": nlp_results.get("sentiment", {}),
                    "topics": [t["name"] for t in nlp_results.get("topics", [])[:3]],
                    "keywords": [k["keyword"] for k in nlp_results.get("keywords", [])[:5]]
                },
                "score_breakdown": {
                    "final_score": score_breakdown.final_score,
                    "confidence_score": score_breakdown.confidence_score,
                    "platform_adjustment": score_breakdown.platform_adjustment,
                    "bonuses_applied": len(score_breakdown.bonuses) if score_breakdown.bonuses else 0
                },
                "processing_time": analytics_data.processing_duration
            }
            
            # Add CV analysis if available
            if cv_results:
                response["cv_analysis"] = {
                    "content_type": cv_results.get("content_type", "none"),
                    "has_people": cv_content_features.get("has_people", False),
                    "visual_quality_score": cv_content_features.get("visual_quality_score", 0)
                }
                
                # Add dominant scene if available
                if "dominant_scene" in cv_content_features:
                    response["cv_analysis"]["dominant_scene"] = cv_content_features["dominant_scene"]
            
            return response
            
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
            
            # Perform NLP analysis
            nlp_results = self.nlp_analyzer.analyze_post(post)
            nlp_content_features = self.nlp_analyzer.extract_content_features(post)
            
            # Perform CV analysis if post has images or videos
            cv_results = {}
            cv_content_features = {}
            if post.images or post.videos:
                post_data = {
                    'images': post.images.split(',') if post.images else [],
                    'videos': post.videos.split(',') if post.videos else []
                }
                cv_results = self.cv_analyzer.analyze_content(post_data)
                cv_content_features = self.cv_analyzer.extract_content_features(post_data)
            
            # Update content quality score with NLP and CV insights
            nlp_content_quality = self.nlp_analyzer.calculate_content_quality_score(nlp_results)
            cv_content_quality = self.cv_analyzer.calculate_content_quality_score(post_data) if post.images or post.videos else 0
            
            # Combine NLP and CV quality scores
            if cv_content_quality > 0:
                # If we have both NLP and CV scores, use weighted average
                combined_quality = (nlp_content_quality * 0.6) + (cv_content_quality * 0.4)
            else:
                # If we only have NLP score, use that
                combined_quality = nlp_content_quality
            
            # Update the content quality score
            advanced_metrics.content_quality_score = combined_quality
            
            # Add NLP-identified patterns
            nlp_patterns = self.nlp_analyzer.identify_content_patterns(nlp_results)
            
            # Add CV-identified patterns
            cv_patterns = self.cv_analyzer.identify_visual_patterns(post_data) if post.images or post.videos else []
            
            # Apply enhanced pattern recognition
            enhanced_patterns = self.pattern_recognizer.recognize_patterns(
                post, processed_metrics, advanced_metrics
            )
            # Combine traditional patterns with NLP and CV identified patterns
            enhanced_patterns.extend(nlp_patterns)
            enhanced_patterns.extend(cv_patterns)
            advanced_metrics.success_patterns = enhanced_patterns
            
            # Calculate detailed score breakdown
            score_breakdown = self.scoring_algorithm.calculate_score_detailed(
                advanced_metrics, processed_metrics
            )
            
            # Apply sentiment-based adjustment if applicable
            if "sentiment" in nlp_results and post.platform:
                sentiment_score = nlp_results["sentiment"]["score"]
                sentiment_boost = self.nlp_analyzer.get_sentiment_boost(
                    sentiment_score, 
                    post.platform.value
                )
                score_breakdown.final_score *= sentiment_boost
            
            # Combine NLP and CV content features
            content_features = {**nlp_content_features}
            if cv_content_features:
                content_features.update(cv_content_features)
                # If both NLP and CV detected people/entities, mark as high-interest
                if nlp_content_features.get('has_entities', False) and cv_content_features.get('has_people', False):
                    content_features['high_interest_content'] = True
            
            # Store the analytics data
            analytics_data = self._create_or_update_analytics_data(
                post,
                processed_metrics,
                advanced_metrics,
                score_breakdown.final_score,
                score_breakdown,
                processing_start_time,
                content_features=content_features
            )
            
            # Update post flags
            post.is_analyzed = True
            post.performance_score = score_breakdown.final_score
            self.db.commit()
            
            # Prepare detailed response with both NLP and CV analysis
            result = {
                "post": {
                    "id": post.id,
                    "title": post.title,
                    "platform": post.platform.value if post.platform else None,
                    "url": post.url,
                    "published_at": post.published_at.isoformat() if post.published_at else None,
                    "has_images": bool(post.images),
                    "has_videos": bool(post.videos)
                },
                "performance": {
                    "score": score_breakdown.final_score,
                    "confidence": score_breakdown.confidence_score,
                    "engagement_rate": processed_metrics.engagement_rate,
                    "total_engagement": processed_metrics.total_engagement,
                    "views": processed_metrics.views,
                    "virality_score": advanced_metrics.virality_score,
                    "trend_score": advanced_metrics.trend_score,
                    "content_quality_score": advanced_metrics.content_quality_score
                },
                "breakdown": {
                    "base_score": score_breakdown.base_score,
                    "platform_adjustment": score_breakdown.platform_adjustment,
                    "bonuses": score_breakdown.bonuses if score_breakdown.bonuses else [],
                    "penalties": score_breakdown.penalties if score_breakdown.penalties else []
                },
                "patterns": enhanced_patterns,
                "nlp_analysis": nlp_results,
                "analytics_id": analytics_data.id,
                "processing_time": analytics_data.processing_duration
            }
            
            # Add CV analysis if available
            if cv_results:
                result["cv_analysis"] = cv_results
            
            return result
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in detailed analysis of post {post_id}: {str(e)}")
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
        
        logger.info(f"Found {len(post_ids)} unanalyzed posts from {platform.value}")
        return self.analyze_batch_posts(post_ids)
    
    def reanalyze_post(self, post_id: int) -> Optional[AnalyticsData]:
        """
        Reanalyze a post that has already been analyzed
        
        Args:
            post_id: ID of the post to reanalyze
            
        Returns:
            AnalyticsData: Updated analytics data
        """
        try:
            # Get the post
            post = self.db.query(Post).filter(Post.id == post_id).first()
            if not post:
                logger.error(f"Post with ID {post_id} not found")
                return None
            
            # Delete existing analytics data
            self.db.query(AnalyticsData).filter(AnalyticsData.post_id == post_id).delete()
            
            # Reset analysis flag
            post.is_analyzed = False
            post.performance_score = None
            self.db.commit()
            
            # Reanalyze the post
            result = self.analyze_post_detailed(post_id)
            if result:
                logger.info(f"Post {post_id} reanalyzed successfully")
                return result.get('analytics_data')
            else:
                logger.error(f"Failed to reanalyze post {post_id}")
                return None
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error reanalyzing post {post_id}: {str(e)}")
            return None
    
    def get_analytics_summary(self, platform: Optional[PlatformType] = None) -> Dict[str, Any]:
        """
        Get summary of analytics data
        
        Args:
            platform: Optional platform filter
            
        Returns:
            Dict[str, Any]: Analytics summary
        """
        try:
            # Base query for posts with analytics
            query = self.db.query(Post).filter(Post.is_analyzed == True)
            
            # Apply platform filter if specified
            if platform:
                query = query.filter(Post.platform == platform)
            
            # Count total analyzed posts
            total_posts = query.count()
            
            if total_posts == 0:
                return {
                    "total_posts": 0,
                    "average_score": 0,
                    "high_performing_count": 0,
                    "low_performing_count": 0,
                    "platform_breakdown": {}
                }
            
            # Calculate average performance score
            avg_score = self.db.query(func.avg(Post.performance_score)).filter(
                Post.is_analyzed == True
            ).scalar() or 0
            
            # Count high and low performing posts
            high_performing = query.filter(Post.performance_score >= 70).count()
            low_performing = query.filter(Post.performance_score <= 30).count()
            
            # Get platform breakdown
            platform_breakdown = {}
            for p in PlatformType:
                platform_count = self.db.query(Post).filter(
                    Post.is_analyzed == True,
                    Post.platform == p
                ).count()
                
                if platform_count > 0:
                    platform_avg = self.db.query(func.avg(Post.performance_score)).filter(
                        Post.is_analyzed == True,
                        Post.platform == p
                    ).scalar() or 0
                    
                    platform_breakdown[p.value] = {
                        "count": platform_count,
                        "average_score": round(platform_avg, 2)
                    }
            
            return {
                "total_posts": total_posts,
                "average_score": round(avg_score, 2),
                "high_performing_count": high_performing,
                "high_performing_percentage": round((high_performing / total_posts) * 100, 1),
                "low_performing_count": low_performing,
                "low_performing_percentage": round((low_performing / total_posts) * 100, 1),
                "platform_breakdown": platform_breakdown
            }
            
        except Exception as e:
            logger.error(f"Error getting analytics summary: {str(e)}")
            return {
                "error": str(e)
            }
    
    def _create_or_update_analytics_data(
        self, 
        post: Post, 
        processed_metrics: ProcessedMetrics,
        advanced_metrics: AdvancedMetrics,
        performance_score: float,
        score_breakdown: Optional[ScoreBreakdown] = None,
        processing_start_time: Optional[datetime] = None,
        content_features: Optional[Dict[str, Any]] = None
    ) -> AnalyticsData:
        """
        Create or update analytics data for a post
        
        Args:
            post: Post model instance
            processed_metrics: Processed metrics
            advanced_metrics: Advanced metrics
            performance_score: Overall performance score
            score_breakdown: Detailed score breakdown
            processing_start_time: Start time of processing
            content_features: NLP-extracted content features
            
        Returns:
            AnalyticsData: Created or updated analytics data
        """
        # Check if analytics data already exists
        analytics_data = self.db.query(AnalyticsData).filter(
            AnalyticsData.post_id == post.id
        ).first()
        
        if not analytics_data:
            # Create new analytics data
            analytics_data = AnalyticsData(
                post_id=post.id,
                engagement_rate=processed_metrics.engagement_rate,
                performance_score=performance_score
            )
            self.db.add(analytics_data)
        else:
            # Update existing analytics data
            analytics_data.engagement_rate = processed_metrics.engagement_rate
            analytics_data.performance_score = performance_score
        
        # Calculate processing duration
        if processing_start_time:
            processing_duration = (datetime.now(timezone.utc) - processing_start_time).total_seconds()
            analytics_data.processing_duration = processing_duration
        
        # Update advanced metrics
        analytics_data.virality_score = advanced_metrics.virality_score
        analytics_data.trend_score = advanced_metrics.trend_score
        analytics_data.engagement_velocity = advanced_metrics.engagement_velocity
        analytics_data.content_quality_score = advanced_metrics.content_quality_score
        analytics_data.audience_reach_score = advanced_metrics.audience_reach_score
        analytics_data.interaction_depth_score = advanced_metrics.interaction_depth_score
        
        # Update success patterns
        analytics_data.success_patterns = [
            pattern.to_dict() if hasattr(pattern, 'to_dict') else pattern
            for pattern in advanced_metrics.success_patterns
        ] if advanced_metrics.success_patterns else []
        
        # Add NLP content features if available
        if content_features:
            analytics_data.content_features = content_features
        
        # Update score breakdown components if available
        if score_breakdown:
            analytics_data.weighted_components = score_breakdown.components
            analytics_data.applied_bonuses = score_breakdown.bonuses
            analytics_data.applied_penalties = score_breakdown.penalties
            analytics_data.platform_adjustment = score_breakdown.platform_adjustment
            analytics_data.confidence_score = score_breakdown.confidence_score
        
        # Update data quality assessment
        data_quality = self._assess_data_quality(processed_metrics, advanced_metrics)
        analytics_data.data_quality_flags = data_quality
        
        # Update analyzed timestamp
        analytics_data.analyzed_at = datetime.now(timezone.utc)
        
        return analytics_data
    
    def _calculate_basic_confidence(self, processed_metrics: ProcessedMetrics) -> float:
        """
        Calculate basic confidence score for analytics
        
        Args:
            processed_metrics: Processed metrics
            
        Returns:
            float: Confidence score (0-100)
        """
        confidence = 100.0
        
        # Reduce confidence for low view counts
        if processed_metrics.views < 100:
            confidence *= 0.7
        elif processed_metrics.views < 1000:
            confidence *= 0.9
        
        # Reduce confidence for very new content (might not have stabilized)
        if processed_metrics.publish_date:
            hours_since_publish = (datetime.now(timezone.utc) - processed_metrics.publish_date).total_seconds() / 3600
            if hours_since_publish < 24:
                confidence *= 0.8
            elif hours_since_publish < 72:
                confidence *= 0.9
        
        return confidence
    
    def _assess_data_quality(
        self, 
        processed_metrics: ProcessedMetrics, 
        advanced_metrics: AdvancedMetrics
    ) -> Dict[str, Any]:
        """
        Assess data quality and identify potential issues
        
        Args:
            processed_metrics: Processed metrics
            advanced_metrics: Advanced metrics
            
        Returns:
            Dict[str, Any]: Data quality assessment
        """
        flags = {}
        
        # Check for missing view data
        if processed_metrics.views == 0:
            flags["missing_view_data"] = True
        
        # Check for suspiciously high engagement rate
        if processed_metrics.engagement_rate > 100:
            flags["suspicious_engagement_rate"] = processed_metrics.engagement_rate
        
        # Check for very low engagement
        if processed_metrics.total_engagement == 0 and processed_metrics.views > 100:
            flags["zero_engagement"] = True
        
        # Check for suspicious virality score
        if advanced_metrics.virality_score > 95:
            flags["suspicious_virality"] = advanced_metrics.virality_score
        
        return flags
