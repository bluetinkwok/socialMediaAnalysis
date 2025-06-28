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
            
            # Content feature patterns
            "effective_hashtags": PatternRule(
                name="effective_hashtags",
                description="Content with high-performing hashtags",
                confidence_threshold=0.7
            ),
            "optimal_content_length": PatternRule(
                name="optimal_content_length",
                description="Content with optimal length for its type",
                confidence_threshold=0.7
            ),
            "successful_mentions": PatternRule(
                name="successful_mentions",
                description="Content with effective account mentions",
                confidence_threshold=0.75
            )
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
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error recognizing patterns for post {post.id}: {str(e)}")
            return advanced_metrics.success_patterns or {}
    
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
