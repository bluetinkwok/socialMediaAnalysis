"""
Pattern Recognizer Module
Implements rule-based success pattern recognition for social media content.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
import statistics
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from .data_processor import ProcessedMetrics
from .metrics_calculator import AdvancedMetrics
from db.models import Post, AnalyticsData, PlatformType, ContentType
from db.database import SessionLocal

logger = logging.getLogger(__name__)


@dataclass
class PatternRule:
    """Definition of a success pattern rule"""
    name: str
    description: str
    confidence_threshold: float = 0.7  # Minimum confidence to report pattern


class PatternRecognizer:
    """
    Pattern Recognizer for identifying success patterns in content
    Extends the basic pattern detection with more comprehensive rules
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or SessionLocal()
        
        # Initialize rule definitions
        self._initialize_rules()
        
        # Historical data cache
        self.platform_averages = {}
        self.content_type_averages = {}
        self.temporal_patterns = {}
    
    def _initialize_rules(self):
        """Initialize pattern recognition rules"""
        self.rules = {
            # Content type patterns
            "successful_video": PatternRule(
                name="successful_video",
                description="High-performing video content",
                confidence_threshold=0.75
            ),
            "successful_image": PatternRule(
                name="successful_image",
                description="High-performing image content",
                confidence_threshold=0.75
            ),
            "successful_text": PatternRule(
                name="successful_text",
                description="High-performing text content",
                confidence_threshold=0.8
            ),
            
            # Temporal patterns
            "optimal_posting_time": PatternRule(
                name="optimal_posting_time",
                description="Content posted during optimal engagement hours",
                confidence_threshold=0.7
            ),
            "weekend_success": PatternRule(
                name="weekend_success",
                description="Content performing well on weekends",
                confidence_threshold=0.75
            ),
            "rapid_growth": PatternRule(
                name="rapid_growth",
                description="Content with unusually rapid engagement growth",
                confidence_threshold=0.8
            ),
            
            # NLP-based patterns
            "positive_sentiment": PatternRule(
                name="positive_sentiment",
                description="Content with highly positive sentiment driving engagement",
                confidence_threshold=0.75
            ),
            "high_readability": PatternRule(
                name="high_readability",
                description="Content with excellent readability scores performing well",
                confidence_threshold=0.7
            ),
            "topic_relevance": PatternRule(
                name="topic_relevance",
                description="Content with strong topic relevance to audience interests",
                confidence_threshold=0.75
            ),
            "keyword_optimized": PatternRule(
                name="keyword_optimized",
                description="Content with well-optimized keywords for the platform",
                confidence_threshold=0.7
            ),
            "emotional_triggers": PatternRule(
                name="emotional_triggers",
                description="Content using emotional language that drives engagement",
                confidence_threshold=0.75
            ),
            
            # CV-based patterns
            "visual_appeal": PatternRule(
                name="visual_appeal",
                description="Content with high visual appeal scores",
                confidence_threshold=0.75
            ),
            "human_presence": PatternRule(
                name="human_presence",
                description="Content featuring human faces or people",
                confidence_threshold=0.7
            ),
            "color_harmony": PatternRule(
                name="color_harmony",
                description="Content with harmonious color schemes",
                confidence_threshold=0.7
            ),
            "scene_relevance": PatternRule(
                name="scene_relevance",
                description="Content with scenes highly relevant to the message",
                confidence_threshold=0.75
            ),
            
            # Combined NLP+CV patterns
            "emotional_visual_harmony": PatternRule(
                name="emotional_visual_harmony",
                description="Content where emotional tone matches visual elements",
                confidence_threshold=0.8
            ),
            "storytelling_excellence": PatternRule(
                name="storytelling_excellence",
                description="Content that tells a compelling story across text and visuals",
                confidence_threshold=0.8
            ),
            "topic_scene_alignment": PatternRule(
                name="topic_scene_alignment",
                description="Content where discussed topics align with visual scenes",
                confidence_threshold=0.75
            ),
            "personality_showcase": PatternRule(
                name="personality_showcase",
                description="Content effectively showcasing personality through text and visuals",
                confidence_threshold=0.75
            ),
            "visual_text_contrast": PatternRule(
                name="visual_text_contrast",
                description="Content with intentional contrast between text and visuals",
                confidence_threshold=0.75
            ),
        }
    
    def recognize_patterns(
        self, 
        post: Post, 
        processed_metrics: ProcessedMetrics,
        advanced_metrics: AdvancedMetrics
    ) -> Dict[str, Any]:
        """
        Recognize success patterns in a post based on defined rules
        
        Args:
            post: Post model instance
            processed_metrics: Processed metrics data
            advanced_metrics: Advanced calculated metrics
            
        Returns:
            Dict[str, Any]: Dictionary of recognized patterns with details
        """
        try:
            # Start with any existing patterns from basic detection
            patterns = advanced_metrics.success_patterns.copy() if advanced_metrics.success_patterns else {}
            
            # Get platform and content type averages if needed
            self._ensure_averages_loaded(post.platform, post.content_type)
            
            # Apply content type pattern rules
            self._detect_content_type_patterns(post, processed_metrics, advanced_metrics, patterns)
            
            # Apply temporal pattern rules
            self._detect_temporal_patterns(post, processed_metrics, advanced_metrics, patterns)
            
            # Apply content feature pattern rules
            self._detect_content_feature_patterns(post, processed_metrics, advanced_metrics, patterns)
            
            # Apply NLP pattern rules if NLP data is available
            if hasattr(advanced_metrics, 'nlp_data') and advanced_metrics.nlp_data:
                self._detect_nlp_patterns(post, advanced_metrics.nlp_data, patterns)
            
            # Apply CV pattern rules if CV data is available
            if hasattr(advanced_metrics, 'cv_data') and advanced_metrics.cv_data:
                self._detect_cv_patterns(post, advanced_metrics.cv_data, patterns)
                
                # Apply combined NLP+CV patterns if both are available
                if hasattr(advanced_metrics, 'nlp_data') and advanced_metrics.nlp_data:
                    self._detect_combined_patterns(
                        post, 
                        advanced_metrics.nlp_data, 
                        advanced_metrics.cv_data, 
                        patterns
                    )
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error recognizing patterns: {str(e)}")
            return {}
    
    def _ensure_averages_loaded(self, platform: PlatformType, content_type: ContentType):
        """Ensure we have average metrics for comparison"""
        platform_key = platform.value
        content_key = content_type.value
        
        # Load platform averages if not cached
        if platform_key not in self.platform_averages:
            self._load_platform_averages(platform)
        
        # Load content type averages if not cached
        if content_key not in self.content_type_averages:
            self._load_content_type_averages(content_type)
        
        # Load temporal patterns if not cached
        if platform_key not in self.temporal_patterns:
            self._load_temporal_patterns(platform)
    
    def _load_platform_averages(self, platform: PlatformType):
        """Load average metrics for a platform"""
        try:
            query = self.db.query(
                func.avg(AnalyticsData.performance_score).label('avg_performance'),
                func.avg(AnalyticsData.engagement_rate).label('avg_engagement'),
                func.avg(AnalyticsData.engagement_velocity).label('avg_velocity')
            ).join(Post).filter(Post.platform == platform)
            
            result = query.first()
            
            if result:
                self.platform_averages[platform.value] = {
                    'performance_score': result.avg_performance or 0.0,
                    'engagement_rate': result.avg_engagement or 0.0,
                    'engagement_velocity': result.avg_velocity or 0.0
                }
            else:
                # Default values if no data
                self.platform_averages[platform.value] = {
                    'performance_score': 50.0,
                    'engagement_rate': 2.0,
                    'engagement_velocity': 0.5
                }
                
        except Exception as e:
            logger.error(f"Error loading platform averages: {str(e)}")
            self.platform_averages[platform.value] = {
                'performance_score': 50.0,
                'engagement_rate': 2.0,
                'engagement_velocity': 0.5
            }
    
    def _load_content_type_averages(self, content_type: ContentType):
        """Load average metrics for a content type"""
        try:
            query = self.db.query(
                func.avg(AnalyticsData.performance_score).label('avg_performance'),
                func.avg(AnalyticsData.engagement_rate).label('avg_engagement'),
                func.avg(AnalyticsData.interaction_depth_score).label('avg_interaction')
            ).join(Post).filter(Post.content_type == content_type)
            
            result = query.first()
            
            if result:
                self.content_type_averages[content_type.value] = {
                    'performance_score': result.avg_performance or 0.0,
                    'engagement_rate': result.avg_engagement or 0.0,
                    'interaction_depth_score': result.avg_interaction or 0.0
                }
            else:
                # Default values if no data
                self.content_type_averages[content_type.value] = {
                    'performance_score': 50.0,
                    'engagement_rate': 2.0,
                    'interaction_depth_score': 40.0
                }
                
        except Exception as e:
            logger.error(f"Error loading content type averages: {str(e)}")
            self.content_type_averages[content_type.value] = {
                'performance_score': 50.0,
                'engagement_rate': 2.0,
                'interaction_depth_score': 40.0
            }
    
    def _load_temporal_patterns(self, platform: PlatformType):
        """Load temporal engagement patterns for a platform"""
        try:
            # Get hourly performance averages
            hourly_query = self.db.query(
                func.extract('hour', Post.publish_date).label('hour'),
                func.avg(AnalyticsData.performance_score).label('avg_performance')
            ).join(AnalyticsData).filter(
                Post.platform == platform,
                Post.publish_date != None
            ).group_by(func.extract('hour', Post.publish_date))
            
            hourly_results = hourly_query.all()
            
            # Get day of week performance averages
            daily_query = self.db.query(
                func.extract('dow', Post.publish_date).label('day'),
                func.avg(AnalyticsData.performance_score).label('avg_performance')
            ).join(AnalyticsData).filter(
                Post.platform == platform,
                Post.publish_date != None
            ).group_by(func.extract('dow', Post.publish_date))
            
            daily_results = daily_query.all()
            
            # Process hourly data
            hourly_data = {}
            for result in hourly_results:
                if result.hour is not None and result.avg_performance is not None:
                    hourly_data[int(result.hour)] = result.avg_performance
            
            # Find top performing hours
            top_hours = []
            if hourly_data:
                sorted_hours = sorted(hourly_data.items(), key=lambda x: x[1], reverse=True)
                top_hours = [hour for hour, _ in sorted_hours[:3]]
            
            # Process daily data
            daily_data = {}
            weekend_avg = 0.0
            weekday_avg = 0.0
            weekend_count = 0
            weekday_count = 0
            
            for result in daily_results:
                if result.day is not None and result.avg_performance is not None:
                    day = int(result.day)
                    daily_data[day] = result.avg_performance
                    
                    # Calculate weekend vs weekday averages
                    if day in [0, 6]:  # 0 = Sunday, 6 = Saturday in PostgreSQL
                        weekend_avg += result.avg_performance
                        weekend_count += 1
                    else:
                        weekday_avg += result.avg_performance
                        weekday_count += 1
            
            if weekend_count > 0:
                weekend_avg /= weekend_count
            if weekday_count > 0:
                weekday_avg /= weekday_count
            
            # Store temporal patterns
            self.temporal_patterns[platform.value] = {
                'hourly_performance': hourly_data,
                'daily_performance': daily_data,
                'top_hours': top_hours,
                'weekend_avg': weekend_avg,
                'weekday_avg': weekday_avg
            }
                
        except Exception as e:
            logger.error(f"Error loading temporal patterns: {str(e)}")
            self.temporal_patterns[platform.value] = {
                'hourly_performance': {},
                'daily_performance': {},
                'top_hours': [9, 12, 18],  # Default peak hours
                'weekend_avg': 50.0,
                'weekday_avg': 50.0
            }
    
    def _detect_content_type_patterns(
        self, 
        post: Post, 
        processed_metrics: ProcessedMetrics,
        advanced_metrics: AdvancedMetrics,
        patterns: Dict[str, Any]
    ):
        """Detect content type specific patterns"""
        try:
            content_type = post.content_type
            platform = post.platform
            
            # Get averages for comparison
            platform_avg = self.platform_averages.get(platform.value, {})
            content_avg = self.content_type_averages.get(content_type.value, {})
            
            # Successful Video Content
            if content_type == ContentType.VIDEO and advanced_metrics.performance_score >= 75:
                confidence = min(advanced_metrics.performance_score / 100, 1.0)
                if confidence >= self.rules['successful_video'].confidence_threshold:
                    patterns['successful_video'] = {
                        'detected': True,
                        'confidence': round(confidence, 2),
                        'metrics': {
                            'performance_score': advanced_metrics.performance_score,
                            'platform_avg': platform_avg.get('performance_score', 0.0)
                        }
                    }
            
            # Successful Image Content
            if content_type == ContentType.IMAGE:
                platform_threshold = platform_avg.get('engagement_rate', 2.0) * 1.2
                if processed_metrics.engagement_rate > platform_threshold:
                    confidence = min(processed_metrics.engagement_rate / (platform_threshold * 2), 1.0)
                    if confidence >= self.rules['successful_image'].confidence_threshold:
                        patterns['successful_image'] = {
                            'detected': True,
                            'confidence': round(confidence, 2),
                            'metrics': {
                                'engagement_rate': processed_metrics.engagement_rate,
                                'platform_threshold': platform_threshold
                            }
                        }
            
            # Successful Text Content
            if content_type == ContentType.TEXT and advanced_metrics.interaction_depth_score > 70:
                content_avg_interaction = content_avg.get('interaction_depth_score', 40.0)
                confidence = min(advanced_metrics.interaction_depth_score / 100, 1.0)
                if confidence >= self.rules['successful_text'].confidence_threshold:
                    patterns['successful_text'] = {
                        'detected': True,
                        'confidence': round(confidence, 2),
                        'metrics': {
                            'interaction_depth_score': advanced_metrics.interaction_depth_score,
                            'content_avg': content_avg_interaction
                        }
                    }
                    
        except Exception as e:
            logger.error(f"Error detecting content type patterns: {str(e)}")
    
    def _detect_temporal_patterns(
        self, 
        post: Post, 
        processed_metrics: ProcessedMetrics,
        advanced_metrics: AdvancedMetrics,
        patterns: Dict[str, Any]
    ):
        """Detect temporal patterns"""
        try:
            if not post.publish_date:
                return
            
            platform = post.platform
            temporal_data = self.temporal_patterns.get(platform.value, {})
            
            # Optimal Posting Time
            if post.publish_date:
                hour = post.publish_date.hour
                top_hours = temporal_data.get('top_hours', [])
                
                if hour in top_hours:
                    # Calculate position-based confidence
                    if top_hours:
                        position = top_hours.index(hour) if hour in top_hours else len(top_hours)
                        confidence = 1.0 - (position / len(top_hours) * 0.3)  # Scale: 1.0 to 0.7
                    else:
                        confidence = 0.7
                        
                    if confidence >= self.rules['optimal_posting_time'].confidence_threshold:
                        patterns['optimal_posting_time'] = {
                            'detected': True,
                            'confidence': round(confidence, 2),
                            'metrics': {
                                'post_hour': hour,
                                'top_hours': top_hours
                            }
                        }
            
            # Weekend Success
            if post.publish_date:
                is_weekend = post.publish_date.weekday() >= 5  # 5 = Saturday, 6 = Sunday
                weekend_avg = temporal_data.get('weekend_avg', 50.0)
                
                if is_weekend and advanced_metrics.performance_score > weekend_avg * 1.2:
                    confidence = min(advanced_metrics.performance_score / (weekend_avg * 2), 1.0)
                    if confidence >= self.rules['weekend_success'].confidence_threshold:
                        patterns['weekend_success'] = {
                            'detected': True,
                            'confidence': round(confidence, 2),
                            'metrics': {
                                'performance_score': advanced_metrics.performance_score,
                                'weekend_avg': weekend_avg,
                                'day_of_week': post.publish_date.weekday()
                            }
                        }
            
            # Rapid Growth
            platform_avg_velocity = self.platform_averages.get(platform.value, {}).get('engagement_velocity', 0.5)
            if advanced_metrics.engagement_velocity > platform_avg_velocity * 2:
                confidence = min(advanced_metrics.engagement_velocity / (platform_avg_velocity * 4), 1.0)
                if confidence >= self.rules['rapid_growth'].confidence_threshold:
                    patterns['rapid_growth'] = {
                        'detected': True,
                        'confidence': round(confidence, 2),
                        'metrics': {
                            'engagement_velocity': advanced_metrics.engagement_velocity,
                            'platform_avg_velocity': platform_avg_velocity
                        }
                    }
                    
        except Exception as e:
            logger.error(f"Error detecting temporal patterns: {str(e)}")
    
    def _detect_content_feature_patterns(
        self, 
        post: Post, 
        processed_metrics: ProcessedMetrics,
        advanced_metrics: AdvancedMetrics,
        patterns: Dict[str, Any]
    ):
        """Detect content feature patterns"""
        try:
            platform = post.platform
            platform_avg_engagement = self.platform_averages.get(platform.value, {}).get('engagement_rate', 2.0)
            
            # Effective Hashtags
            if post.hashtags and len(post.hashtags) > 0:
                # Get average performance of posts with these hashtags
                hashtag_performance = self._get_hashtag_performance(post.hashtags, platform)
                
                if hashtag_performance > platform_avg_engagement * 1.2:
                    confidence = min(hashtag_performance / (platform_avg_engagement * 2), 1.0)
                    if confidence >= self.rules['effective_hashtags'].confidence_threshold:
                        patterns['effective_hashtags'] = {
                            'detected': True,
                            'confidence': round(confidence, 2),
                            'metrics': {
                                'hashtag_performance': hashtag_performance,
                                'platform_avg': platform_avg_engagement,
                                'hashtag_count': len(post.hashtags)
                            }
                        }
            
            # Optimal Content Length
            optimal_length = self._check_optimal_length(post)
            if optimal_length['is_optimal']:
                if optimal_length['confidence'] >= self.rules['optimal_content_length'].confidence_threshold:
                    patterns['optimal_content_length'] = {
                        'detected': True,
                        'confidence': round(optimal_length['confidence'], 2),
                        'metrics': optimal_length['metrics']
                    }
            
            # Successful Mentions
            if post.mentions and len(post.mentions) > 0:
                # Compare to posts without mentions
                no_mention_avg = self._get_no_mention_avg(platform)
                
                if processed_metrics.engagement_rate > no_mention_avg * 1.15:
                    confidence = min(processed_metrics.engagement_rate / (no_mention_avg * 2), 1.0)
                    if confidence >= self.rules['successful_mentions'].confidence_threshold:
                        patterns['successful_mentions'] = {
                            'detected': True,
                            'confidence': round(confidence, 2),
                            'metrics': {
                                'engagement_rate': processed_metrics.engagement_rate,
                                'no_mention_avg': no_mention_avg,
                                'mention_count': len(post.mentions)
                            }
                        }
                    
        except Exception as e:
            logger.error(f"Error detecting content feature patterns: {str(e)}")
    
    def _get_hashtag_performance(self, hashtags: List[str], platform: PlatformType) -> float:
        """Get average performance of posts with specific hashtags"""
        try:
            # Get posts with at least one of these hashtags
            hashtag_posts = self.db.query(Post).filter(
                Post.platform == platform,
                Post.hashtags.overlap(hashtags),
                Post.is_analyzed == True
            ).all()
            
            if not hashtag_posts:
                return 0.0
                
            # Calculate average engagement rate
            total_engagement = 0.0
            for post in hashtag_posts:
                analytics = self.db.query(AnalyticsData).filter(
                    AnalyticsData.post_id == post.id
                ).first()
                
                if analytics and analytics.engagement_rate:
                    total_engagement += analytics.engagement_rate
            
            return total_engagement / len(hashtag_posts) if hashtag_posts else 0.0
            
        except Exception as e:
            logger.error(f"Error getting hashtag performance: {str(e)}")
            return 0.0
    
    def _check_optimal_length(self, post: Post) -> Dict[str, Any]:
        """Check if content has optimal length for its platform and type"""
        result = {
            'is_optimal': False,
            'confidence': 0.0,
            'metrics': {}
        }
        
        try:
            content_type = post.content_type
            platform = post.platform
            
            # Define optimal ranges based on content type and platform
            optimal_ranges = {
                ContentType.VIDEO: {
                    PlatformType.YOUTUBE: (480, 1200),    # 8-20 minutes
                    PlatformType.INSTAGRAM: (15, 60),     # 15-60 seconds
                    PlatformType.THREADS: (15, 60),       # 15-60 seconds
                    PlatformType.REDNOTE: (15, 90)        # 15-90 seconds
                },
                ContentType.TEXT: {
                    PlatformType.YOUTUBE: (100, 300),     # 100-300 words (description)
                    PlatformType.INSTAGRAM: (50, 200),    # 50-200 characters
                    PlatformType.THREADS: (50, 500),      # 50-500 characters
                    PlatformType.REDNOTE: (50, 300)       # 50-300 characters
                }
            }
            
            # Get content length
            content_length = 0
            if content_type == ContentType.VIDEO:
                content_length = post.duration or 0
            elif content_type == ContentType.TEXT:
                content_length = len(post.content_text) if post.content_text else 0
            elif content_type == ContentType.IMAGE:
                # For images, we don't have a direct "length" metric
                # Could use resolution or aspect ratio in a real implementation
                return result
            
            # Get optimal range for this content type and platform
            if content_type in optimal_ranges and platform in optimal_ranges[content_type]:
                min_length, max_length = optimal_ranges[content_type][platform]
                
                result['metrics'] = {
                    'content_length': content_length,
                    'optimal_min': min_length,
                    'optimal_max': max_length
                }
                
                # Check if within optimal range
                if min_length <= content_length <= max_length:
                    result['is_optimal'] = True
                    
                    # Calculate confidence based on how centered it is in the range
                    range_size = max_length - min_length
                    if range_size > 0:
                        # Distance from center of range, normalized to 0-1
                        center = (min_length + max_length) / 2
                        distance_from_center = abs(content_length - center) / (range_size / 2)
                        # Higher confidence when closer to center
                        result['confidence'] = 1.0 - (distance_from_center * 0.3)  # Scale: 1.0 to 0.7
                    else:
                        result['confidence'] = 0.7
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking optimal content length: {str(e)}")
            return result
    
    def _get_no_mention_avg(self, platform: PlatformType) -> float:
        """Get average engagement rate for posts without mentions"""
        try:
            # Query posts without mentions
            no_mention_posts = self.db.query(Post).filter(
                Post.platform == platform,
                Post.mentions.is_(None) | (func.array_length(Post.mentions, 1) == 0),
                Post.is_analyzed == True
            ).all()
            
            if not no_mention_posts:
                return self.platform_averages.get(platform.value, {}).get('engagement_rate', 2.0)
                
            # Calculate average engagement rate
            total_engagement = 0.0
            count = 0
            
            for post in no_mention_posts:
                analytics = self.db.query(AnalyticsData).filter(
                    AnalyticsData.post_id == post.id
                ).first()
                
                if analytics and analytics.engagement_rate:
                    total_engagement += analytics.engagement_rate
                    count += 1
            
            return total_engagement / count if count > 0 else 2.0
            
        except Exception as e:
            logger.error(f"Error getting no-mention average: {str(e)}")
            return 2.0

    def get_all_success_patterns(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        platform: Optional[PlatformType] = None,
        content_type: Optional[ContentType] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all detected success patterns across posts
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            platform: Optional platform filter
            content_type: Optional content type filter
            
        Returns:
            List of success pattern dictionaries
        """
        try:
            # Build query for posts with analytics data
            query = self.db.query(Post, AnalyticsData).join(
                AnalyticsData, Post.id == AnalyticsData.post_id
            ).filter(
                AnalyticsData.success_patterns != None,
                AnalyticsData.success_patterns != {}
            )
            
            # Apply filters if provided
            if start_date:
                query = query.filter(Post.publish_date >= start_date)
            if end_date:
                query = query.filter(Post.publish_date <= end_date)
            if platform:
                query = query.filter(Post.platform == platform)
            if content_type:
                query = query.filter(Post.content_type == content_type)
            
            # Execute query
            results = query.all()
            
            # Extract and process patterns
            all_patterns = []
            for post, analytics in results:
                if not analytics.success_patterns:
                    continue
                
                for pattern_name, pattern_data in analytics.success_patterns.items():
                    if not pattern_data.get('detected', False):
                        continue
                    
                    # Get pattern rule info
                    rule = self.rules.get(pattern_name)
                    description = rule.description if rule else pattern_name.replace('_', ' ').title()
                    
                    # Create pattern object
                    pattern = {
                        'name': pattern_name,
                        'description': description,
                        'confidence': pattern_data.get('confidence', 0.0),
                        'post_id': post.id,
                        'platform': post.platform.value,
                        'content_type': post.content_type.value,
                        'publish_date': post.publish_date.isoformat() if post.publish_date else None,
                        'metrics': pattern_data.get('metrics', {})
                    }
                    
                    all_patterns.append(pattern)
            
            return all_patterns
            
        except Exception as e:
            logger.error(f"Error getting all success patterns: {str(e)}")
            return []
    
    def get_top_patterns(
        self,
        limit: int = 10,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top success patterns by frequency
        
        Args:
            limit: Number of patterns to return
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            List of top pattern dictionaries
        """
        try:
            # Get all patterns
            all_patterns = self.get_all_success_patterns(
                start_date=start_date,
                end_date=end_date
            )
            
            # Count pattern occurrences
            pattern_counts = {}
            for pattern in all_patterns:
                name = pattern['name']
                if name not in pattern_counts:
                    pattern_counts[name] = {
                        'name': name,
                        'description': pattern['description'],
                        'count': 0,
                        'total_confidence': 0.0,
                        'platforms': set(),
                        'content_types': set()
                    }
                
                pattern_counts[name]['count'] += 1
                pattern_counts[name]['total_confidence'] += pattern['confidence']
                pattern_counts[name]['platforms'].add(pattern['platform'])
                pattern_counts[name]['content_types'].add(pattern['content_type'])
            
            # Calculate average confidence and format results
            top_patterns = []
            for name, data in pattern_counts.items():
                avg_confidence = data['total_confidence'] / data['count'] if data['count'] > 0 else 0
                
                top_patterns.append({
                    'name': name,
                    'description': data['description'],
                    'frequency': data['count'],
                    'confidence': round(avg_confidence, 2),
                    'platforms': list(data['platforms']),
                    'content_types': list(data['content_types'])
                })
            
            # Sort by frequency and limit results
            top_patterns.sort(key=lambda x: x['frequency'], reverse=True)
            return top_patterns[:limit]
            
        except Exception as e:
            logger.error(f"Error getting top patterns: {str(e)}")
            return []
    
    def get_patterns_by_platform(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get success patterns grouped by platform
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            Dictionary of platform -> patterns
        """
        try:
            # Get all patterns
            all_patterns = self.get_all_success_patterns(
                start_date=start_date,
                end_date=end_date
            )
            
            # Group by platform
            patterns_by_platform = {}
            for pattern in all_patterns:
                platform = pattern['platform']
                if platform not in patterns_by_platform:
                    patterns_by_platform[platform] = []
                
                patterns_by_platform[platform].append(pattern)
            
            return patterns_by_platform
            
        except Exception as e:
            logger.error(f"Error getting patterns by platform: {str(e)}")
            return {}
    
    def get_patterns_by_content_type(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get success patterns grouped by content type
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            Dictionary of content_type -> patterns
        """
        try:
            # Get all patterns
            all_patterns = self.get_all_success_patterns(
                start_date=start_date,
                end_date=end_date
            )
            
            # Group by content type
            patterns_by_content_type = {}
            for pattern in all_patterns:
                content_type = pattern['content_type']
                if content_type not in patterns_by_content_type:
                    patterns_by_content_type[content_type] = []
                
                patterns_by_content_type[content_type].append(pattern)
            
            return patterns_by_content_type
            
        except Exception as e:
            logger.error(f"Error getting patterns by content type: {str(e)}")
            return {}

    def _detect_nlp_patterns(
        self,
        post: Post,
        nlp_data: Dict[str, Any],
        patterns: Dict[str, Any]
    ):
        """
        Detect NLP-based patterns in content
        
        Args:
            post: Post model instance
            nlp_data: NLP analysis data
            patterns: Dictionary to store detected patterns
        """
        try:
            # Skip if no NLP data
            if not nlp_data:
                return
                
            # Extract key NLP features
            sentiment = nlp_data.get('sentiment', {})
            sentiment_score = sentiment.get('score', 0)
            sentiment_magnitude = sentiment.get('magnitude', 0)
            
            text_stats = nlp_data.get('text_stats', {})
            readability_score = text_stats.get('readability_score', 0)
            word_count = text_stats.get('word_count', 0)
            
            keywords = nlp_data.get('keywords', [])
            topics = nlp_data.get('topics', [])
            entities = nlp_data.get('entities', [])
            
            # Pattern: Positive Sentiment
            # High positive sentiment (>0.6) with significant magnitude (>1.0)
            if sentiment_score > 0.6 and sentiment_magnitude > 1.0:
                confidence = min(sentiment_score, sentiment_magnitude / 2)
                
                if confidence >= self.rules["positive_sentiment"].confidence_threshold:
                    patterns["positive_sentiment"] = {
                        "detected": True,
                        "confidence": confidence,
                        "metrics": {
                            "sentiment_score": sentiment_score,
                            "sentiment_magnitude": sentiment_magnitude
                        }
                    }
            
            # Pattern: High Readability
            # Content with high readability score (>75) and sufficient content length
            if readability_score > 75 and word_count >= 50:
                confidence = readability_score / 100
                
                if confidence >= self.rules["high_readability"].confidence_threshold:
                    patterns["high_readability"] = {
                        "detected": True,
                        "confidence": confidence,
                        "metrics": {
                            "readability_score": readability_score,
                            "word_count": word_count
                        }
                    }
            
            # Pattern: Topic Relevance
            # Content with strong topic focus (top topics have high relevance scores)
            if topics and len(topics) >= 2:
                top_topics = topics[:3]
                avg_topic_score = sum(t.get('score', 0) for t in top_topics) / len(top_topics)
                
                if avg_topic_score > 0.7:
                    confidence = avg_topic_score
                    
                    if confidence >= self.rules["topic_relevance"].confidence_threshold:
                        patterns["topic_relevance"] = {
                            "detected": True,
                            "confidence": confidence,
                            "metrics": {
                                "avg_topic_score": avg_topic_score,
                                "top_topics": [t.get('name', '') for t in top_topics]
                            }
                        }
            
            # Pattern: Keyword Optimized
            # Content with well-optimized keywords (high relevance scores)
            if keywords and len(keywords) >= 3:
                top_keywords = keywords[:5]
                avg_keyword_score = sum(k.get('relevance', 0) for k in top_keywords) / len(top_keywords)
                
                if avg_keyword_score > 0.65:
                    confidence = avg_keyword_score
                    
                    if confidence >= self.rules["keyword_optimized"].confidence_threshold:
                        patterns["keyword_optimized"] = {
                            "detected": True,
                            "confidence": confidence,
                            "metrics": {
                                "avg_keyword_score": avg_keyword_score,
                                "top_keywords": [k.get('keyword', '') for k in top_keywords]
                            }
                        }
            
            # Pattern: Emotional Triggers
            # Content with emotional language (high sentiment magnitude regardless of direction)
            # and good engagement metrics
            if sentiment_magnitude > 1.5 and abs(sentiment_score) > 0.4:
                confidence = min(1.0, sentiment_magnitude / 3)
                
                if confidence >= self.rules["emotional_triggers"].confidence_threshold:
                    patterns["emotional_triggers"] = {
                        "detected": True,
                        "confidence": confidence,
                        "metrics": {
                            "sentiment_magnitude": sentiment_magnitude,
                            "sentiment_score": sentiment_score,
                            "sentiment_direction": "positive" if sentiment_score > 0 else "negative"
                        }
                    }
                    
        except Exception as e:
            logger.error(f"Error detecting NLP patterns: {str(e)}")

    def _detect_cv_patterns(
        self,
        post: Post,
        cv_data: Dict[str, Any],
        patterns: Dict[str, Any]
    ):
        """
        Detect CV-based patterns in content
        
        Args:
            post: Post model instance
            cv_data: Computer Vision analysis data
            patterns: Dictionary to store detected patterns
        """
        try:
            # Skip if no CV data
            if not cv_data:
                return
                
            # Extract key CV features
            content_type = cv_data.get('content_type', 'unknown')
            aggregate_metrics = cv_data.get('aggregate_metrics', {})
            
            # Common metrics across image and video
            avg_brightness = aggregate_metrics.get('avg_brightness', 0.5)  # Normalized 0-1
            color_diversity = aggregate_metrics.get('color_diversity', 0)
            face_count = aggregate_metrics.get('face_count', 0)
            object_count = aggregate_metrics.get('object_count', 0)
            has_people = aggregate_metrics.get('has_people', False)
            dominant_scenes = aggregate_metrics.get('dominant_scenes', {})
            
            # Image-specific metrics
            visual_appeal_score = aggregate_metrics.get('visual_appeal_score', 0)
            
            # Video-specific metrics
            scene_changes = aggregate_metrics.get('scene_changes', 0)
            total_duration = aggregate_metrics.get('total_duration', 0)
            
            # Pattern: Visual Appeal
            # Content with high visual appeal scores (>0.7)
            if visual_appeal_score > 0.7:
                confidence = visual_appeal_score
                
                if confidence >= self.rules["visual_appeal"].confidence_threshold:
                    patterns["visual_appeal"] = {
                        "detected": True,
                        "confidence": confidence,
                        "metrics": {
                            "visual_appeal_score": visual_appeal_score,
                            "content_type": content_type
                        }
                    }
            
            # Pattern: Human Presence
            # Content featuring human faces or people
            if has_people and face_count > 0:
                # Confidence based on face count - more faces isn't always better
                # Optimal is 1-3 faces for most content
                if face_count <= 3:
                    confidence = 0.7 + (face_count * 0.1)  # 0.8 for 1 face, 0.9 for 2, 1.0 for 3
                else:
                    confidence = 0.9  # Still good but not optimal
                
                if confidence >= self.rules["human_presence"].confidence_threshold:
                    patterns["human_presence"] = {
                        "detected": True,
                        "confidence": confidence,
                        "metrics": {
                            "face_count": face_count,
                            "has_people": has_people
                        }
                    }
            
            # Pattern: Color Harmony
            # Content with harmonious color schemes
            # Balanced brightness (not too dark, not too bright) and good color diversity
            if 0.3 <= avg_brightness <= 0.7 and color_diversity > 0.4:
                # Higher confidence when brightness is closer to middle (0.5)
                brightness_score = 1.0 - abs(avg_brightness - 0.5) * 2  # 1.0 at 0.5, decreasing toward 0.3/0.7
                
                # Combine with color diversity for overall harmony score
                harmony_score = (brightness_score * 0.6) + (min(color_diversity, 1.0) * 0.4)
                
                if harmony_score >= self.rules["color_harmony"].confidence_threshold:
                    patterns["color_harmony"] = {
                        "detected": True,
                        "confidence": harmony_score,
                        "metrics": {
                            "brightness": avg_brightness,
                            "color_diversity": color_diversity,
                            "harmony_score": harmony_score
                        }
                    }
            
            # Pattern: Scene Relevance
            # Content with scenes highly relevant to the message
            if dominant_scenes and len(dominant_scenes) > 0:
                # Get top scene and its confidence
                top_scenes = sorted(dominant_scenes.items(), key=lambda x: x[1], reverse=True)
                
                if top_scenes:
                    top_scene, top_confidence = top_scenes[0]
                    
                    # Only consider high-confidence scene detections
                    if top_confidence > 0.7:
                        if top_confidence >= self.rules["scene_relevance"].confidence_threshold:
                            patterns["scene_relevance"] = {
                                "detected": True,
                                "confidence": top_confidence,
                                "metrics": {
                                    "dominant_scene": top_scene,
                                    "scene_confidence": top_confidence,
                                    "other_scenes": dict(top_scenes[1:3]) if len(top_scenes) > 1 else {}
                                }
                            }
            
            # Video-specific patterns
            if content_type == 'video' and total_duration > 0:
                # Calculate scene change rate (changes per minute)
                if total_duration > 0:
                    scene_change_rate = scene_changes / (total_duration / 60)
                    
                    # Optimal scene change rate depends on content type
                    # For most social media, 4-12 changes per minute is good
                    if 4 <= scene_change_rate <= 12:
                        # Higher confidence when closer to 8 (middle of optimal range)
                        confidence = 1.0 - abs(scene_change_rate - 8) / 8
                        
                        # Add video pacing pattern
                        patterns["video_pacing"] = {
                            "detected": True,
                            "confidence": confidence,
                            "metrics": {
                                "scene_changes": scene_changes,
                                "duration_minutes": total_duration / 60,
                                "scene_change_rate": scene_change_rate
                            }
                        }
                        
        except Exception as e:
            logger.error(f"Error detecting CV patterns: {str(e)}")

    def _detect_combined_patterns(
        self,
        post: Post,
        nlp_data: Dict[str, Any],
        cv_data: Dict[str, Any],
        patterns: Dict[str, Any]
    ):
        """
        Detect patterns that combine NLP and CV insights
        
        Args:
            post: Post model instance
            nlp_data: NLP analysis data
            cv_data: Computer Vision analysis data
            patterns: Dictionary to store detected patterns
        """
        try:
            # Skip if either data is missing
            if not nlp_data or not cv_data:
                return
                
            # Extract key NLP features
            sentiment = nlp_data.get('sentiment', {})
            sentiment_score = sentiment.get('score', 0)
            sentiment_magnitude = sentiment.get('magnitude', 0)
            
            text_stats = nlp_data.get('text_stats', {})
            readability_score = text_stats.get('readability_score', 0)
            
            keywords = nlp_data.get('keywords', [])
            topics = nlp_data.get('topics', [])
            entities = nlp_data.get('entities', [])
            
            # Extract key CV features
            aggregate_metrics = cv_data.get('aggregate_metrics', {})
            
            avg_brightness = aggregate_metrics.get('avg_brightness', 0.5)
            color_diversity = aggregate_metrics.get('color_diversity', 0)
            face_count = aggregate_metrics.get('face_count', 0)
            has_people = aggregate_metrics.get('has_people', False)
            dominant_scenes = aggregate_metrics.get('dominant_scenes', {})
            visual_appeal_score = aggregate_metrics.get('visual_appeal_score', 0)
            
            # Pattern: Emotional Visual Harmony
            # Content where emotional tone in text matches visual elements
            if abs(sentiment_score) > 0.4 and sentiment_magnitude > 0.7:
                # Check if visual elements match sentiment
                # Positive sentiment often correlates with brighter images
                # Negative sentiment often correlates with darker or more contrasting images
                visual_sentiment_match = False
                
                if sentiment_score > 0.4:  # Positive sentiment
                    # Brighter images, more vibrant colors
                    if avg_brightness > 0.55 and color_diversity > 0.5:
                        visual_sentiment_match = True
                        match_strength = min(1.0, (avg_brightness - 0.55) * 5 + color_diversity)
                elif sentiment_score < -0.4:  # Negative sentiment
                    # Darker images or high contrast
                    if avg_brightness < 0.45 or color_diversity > 0.7:
                        visual_sentiment_match = True
                        match_strength = min(1.0, (0.45 - avg_brightness) * 5 + color_diversity)
                
                if visual_sentiment_match:
                    # Calculate confidence based on sentiment strength and visual match
                    confidence = (abs(sentiment_score) * 0.5 + match_strength * 0.5)
                    
                    if confidence >= self.rules["emotional_visual_harmony"].confidence_threshold:
                        patterns["emotional_visual_harmony"] = {
                            "detected": True,
                            "confidence": confidence,
                            "metrics": {
                                "sentiment_score": sentiment_score,
                                "sentiment_magnitude": sentiment_magnitude,
                                "brightness": avg_brightness,
                                "color_diversity": color_diversity,
                                "sentiment_type": "positive" if sentiment_score > 0 else "negative"
                            }
                        }
            
            # Pattern: Storytelling Excellence
            # Content that tells a compelling story across text and visuals
            if (len(entities) >= 3 and 
                readability_score > 70 and 
                (has_people or len(dominant_scenes) >= 2)):
                
                # Calculate storytelling score based on multiple factors
                entity_score = min(1.0, len(entities) / 10)
                readability_factor = readability_score / 100
                visual_factor = 0.7 if has_people else 0.5
                scene_factor = min(1.0, len(dominant_scenes) / 4) if dominant_scenes else 0.3
                
                storytelling_score = (entity_score * 0.3 + 
                                     readability_factor * 0.3 + 
                                     visual_factor * 0.2 + 
                                     scene_factor * 0.2)
                
                if storytelling_score >= self.rules["storytelling_excellence"].confidence_threshold:
                    patterns["storytelling_excellence"] = {
                        "detected": True,
                        "confidence": storytelling_score,
                        "metrics": {
                            "entity_count": len(entities),
                            "readability_score": readability_score,
                            "has_people": has_people,
                            "scene_count": len(dominant_scenes) if dominant_scenes else 0,
                            "storytelling_score": storytelling_score
                        }
                    }
            
            # Pattern: Topic Scene Alignment
            # Content where discussed topics align with visual scenes
            if topics and dominant_scenes:
                # Get top topics and scenes
                top_topics = [t.get('name', '').lower() for t in topics[:3] if 'name' in t]
                top_scenes = list(dominant_scenes.keys())
                
                # Check for alignment between topics and scenes
                alignment_count = 0
                aligned_pairs = []
                
                for topic in top_topics:
                    for scene in top_scenes:
                        # Simple alignment check - topic words appear in scene or vice versa
                        topic_words = topic.split()
                        scene_words = scene.split()
                        
                        for word in topic_words:
                            if word in scene:
                                alignment_count += 1
                                aligned_pairs.append((topic, scene))
                                break
                                
                        for word in scene_words:
                            if word in topic:
                                alignment_count += 1
                                aligned_pairs.append((topic, scene))
                                break
                
                if alignment_count > 0:
                    # Calculate alignment score based on number of alignments
                    alignment_score = min(1.0, alignment_count / 3)
                    
                    if alignment_score >= self.rules["topic_scene_alignment"].confidence_threshold:
                        patterns["topic_scene_alignment"] = {
                            "detected": True,
                            "confidence": alignment_score,
                            "metrics": {
                                "alignment_count": alignment_count,
                                "aligned_pairs": aligned_pairs[:3],  # Top 3 alignments
                                "top_topics": top_topics,
                                "top_scenes": top_scenes
                            }
                        }
            
            # Pattern: Personality Showcase
            # Content effectively showcasing personality through text and visuals
            if has_people and face_count > 0 and entities:
                # Check for person entities in text
                person_entities = [e for e in entities if e.get('type') == 'PERSON']
                
                if person_entities:
                    # Calculate personality score based on face presence and person mentions
                    personality_score = min(1.0, (face_count * 0.4 + len(person_entities) * 0.2))
                    
                    # Boost score if sentiment is strong (personality often has emotional component)
                    if abs(sentiment_score) > 0.5:
                        personality_score += 0.2
                        
                    personality_score = min(1.0, personality_score)
                    
                    if personality_score >= self.rules["personality_showcase"].confidence_threshold:
                        patterns["personality_showcase"] = {
                            "detected": True,
                            "confidence": personality_score,
                            "metrics": {
                                "face_count": face_count,
                                "person_entities": len(person_entities),
                                "sentiment_strength": abs(sentiment_score),
                                "personality_score": personality_score
                            }
                        }
            
            # Pattern: Visual Text Contrast
            # Content with intentional contrast between text and visuals
            # This can be effective when the contrast is deliberate (not accidental)
            if sentiment_score != 0 and visual_appeal_score > 0.6:
                # Check for contrast between text sentiment and visual brightness
                contrast_exists = False
                
                if sentiment_score > 0.5 and avg_brightness < 0.4:
                    # Positive text with darker visuals
                    contrast_exists = True
                    contrast_strength = abs(sentiment_score - avg_brightness)
                elif sentiment_score < -0.5 and avg_brightness > 0.6:
                    # Negative text with brighter visuals
                    contrast_exists = True
                    contrast_strength = abs(abs(sentiment_score) - avg_brightness)
                
                if contrast_exists and contrast_strength > 0.3:
                    contrast_score = min(1.0, contrast_strength)
                    
                    if contrast_score >= self.rules["visual_text_contrast"].confidence_threshold:
                        patterns["visual_text_contrast"] = {
                            "detected": True,
                            "confidence": contrast_score,
                            "metrics": {
                                "sentiment_score": sentiment_score,
                                "brightness": avg_brightness,
                                "contrast_strength": contrast_strength,
                                "visual_appeal": visual_appeal_score
                            }
                        }
                        
        except Exception as e:
            logger.error(f"Error detecting combined patterns: {str(e)}")
