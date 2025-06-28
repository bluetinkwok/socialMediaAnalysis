"""
Metrics Calculator
Computes advanced engagement metrics from processed post data
"""

import logging
import math
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

from .data_processor import ProcessedMetrics
from db.models import Post, PlatformType

logger = logging.getLogger(__name__)


@dataclass
class AdvancedMetrics:
    """Container for calculated advanced metrics"""
    virality_score: float
    trend_score: float
    engagement_velocity: float
    content_quality_score: float
    audience_reach_score: float
    interaction_depth_score: float
    success_patterns: Dict[str, Any]
    content_features: Dict[str, Any]


class MetricsCalculator:
    """Calculator for advanced engagement metrics and analytics"""
    
    def __init__(self):
        # Weight configurations for different metrics
        self.engagement_weights = {
            'likes': 1.0,
            'comments': 3.0,  # Comments indicate higher engagement
            'shares': 5.0,    # Shares indicate viral potential
            'saves': 4.0,     # Saves indicate content value
            'reactions': 2.0,
            'follows': 10.0,  # Follows indicate strong impact
            'clicks': 1.5
        }
        
        # Platform-specific engagement thresholds
        self.platform_thresholds = {
            PlatformType.YOUTUBE: {
                'high_engagement_rate': 0.05,  # 5%
                'viral_threshold': 100000,     # 100K views
                'quality_indicators': ['comments', 'likes', 'shares']
            },
            PlatformType.INSTAGRAM: {
                'high_engagement_rate': 0.03,  # 3%
                'viral_threshold': 50000,      # 50K likes
                'quality_indicators': ['likes', 'comments', 'saves']
            },
            PlatformType.THREADS: {
                'high_engagement_rate': 0.02,  # 2%
                'viral_threshold': 10000,      # 10K likes
                'quality_indicators': ['likes', 'replies', 'shares']
            },
            PlatformType.REDNOTE: {
                'high_engagement_rate': 0.04,  # 4%
                'viral_threshold': 20000,      # 20K likes
                'quality_indicators': ['likes', 'comments', 'collects']
            }
        }
    
    def _get_platform_thresholds(self, platform) -> Dict[str, Any]:
        """Get platform thresholds, handling both string and enum values"""
        try:
            if isinstance(platform, str):
                # Convert string to enum
                platform_enum = PlatformType(platform)
            else:
                platform_enum = platform
            
            return self.platform_thresholds.get(
                platform_enum,
                self.platform_thresholds[PlatformType.INSTAGRAM]
            )
        except (ValueError, KeyError):
            # Fallback to Instagram if platform not found
            return self.platform_thresholds[PlatformType.INSTAGRAM]
    
    def calculate_advanced_metrics(self, processed_metrics: ProcessedMetrics) -> AdvancedMetrics:
        """
        Calculate advanced metrics from processed data
        
        Args:
            processed_metrics: Processed metrics from data processor
            
        Returns:
            AdvancedMetrics object containing all calculated metrics
        """
        try:
            # Calculate individual advanced metrics
            virality_score = self._calculate_virality_score(processed_metrics)
            trend_score = self._calculate_trend_score(processed_metrics)
            engagement_velocity = self._calculate_engagement_velocity(processed_metrics)
            content_quality_score = self._calculate_content_quality_score(processed_metrics)
            audience_reach_score = self._calculate_audience_reach_score(processed_metrics)
            interaction_depth_score = self._calculate_interaction_depth_score(processed_metrics)
            
            # Identify success patterns
            success_patterns = self._identify_success_patterns(processed_metrics)
            
            # Extract content features
            content_features = self._extract_content_features(processed_metrics)
            
            return AdvancedMetrics(
                virality_score=virality_score,
                trend_score=trend_score,
                engagement_velocity=engagement_velocity,
                content_quality_score=content_quality_score,
                audience_reach_score=audience_reach_score,
                interaction_depth_score=interaction_depth_score,
                success_patterns=success_patterns,
                content_features=content_features
            )
            
        except Exception as e:
            logger.error(f"Error calculating advanced metrics: {str(e)}")
            return self._get_default_metrics()
    
    def _calculate_virality_score(self, metrics: ProcessedMetrics) -> float:
        """Calculate virality score based on sharing behavior and reach"""
        try:
            platform_threshold = self._get_platform_thresholds(metrics.platform)
            
            # Base virality from shares/reposts
            shares_score = min((metrics.shares / metrics.views) * 100 if metrics.views > 0 else 0, 50)
            
            # Boost from absolute reach
            reach_multiplier = min(metrics.views / platform_threshold['viral_threshold'], 2.0)
            
            # Engagement velocity factor
            time_factor = self._calculate_time_decay_factor(metrics.publish_date)
            
            # Calculate final virality score
            virality_score = (shares_score * reach_multiplier * time_factor)
            
            return min(max(virality_score, 0), 100)
            
        except Exception as e:
            logger.error(f"Error calculating virality score: {str(e)}")
            return 0.0
    
    def _calculate_trend_score(self, metrics: ProcessedMetrics) -> float:
        """Calculate trend score based on engagement patterns"""
        try:
            platform_threshold = self._get_platform_thresholds(metrics.platform)
            
            # Engagement rate relative to platform average
            engagement_rate_score = min(
                (metrics.engagement_rate / platform_threshold['high_engagement_rate']) * 50, 
                50
            )
            
            # Weighted engagement quality
            quality_score = self._calculate_engagement_quality(metrics) * 30
            
            # Recency boost
            recency_score = self._calculate_recency_boost(metrics.publish_date) * 20
            
            trend_score = engagement_rate_score + quality_score + recency_score
            
            return min(max(trend_score, 0), 100)
            
        except Exception as e:
            logger.error(f"Error calculating trend score: {str(e)}")
            return 0.0
    
    def _calculate_engagement_velocity(self, metrics: ProcessedMetrics) -> float:
        """Calculate engagement velocity (engagement per hour since posting)"""
        try:
            if not metrics.publish_date:
                return 0.0
            
            # Calculate hours since posting
            now = datetime.now(timezone.utc)
            hours_since_posting = max((now - metrics.publish_date).total_seconds() / 3600, 1)
            
            # Calculate total weighted engagement
            total_engagement = (
                metrics.likes * self.engagement_weights['likes'] +
                metrics.comments * self.engagement_weights['comments'] +
                metrics.shares * self.engagement_weights['shares'] +
                metrics.saves * self.engagement_weights['saves']
            )
            
            # Engagement per hour
            velocity = total_engagement / hours_since_posting
            
            return round(velocity, 2)
            
        except Exception as e:
            logger.error(f"Error calculating engagement velocity: {str(e)}")
            return 0.0
    
    def _calculate_content_quality_score(self, metrics: ProcessedMetrics) -> float:
        """Calculate content quality based on engagement depth"""
        try:
            if metrics.views == 0:
                return 0.0
            
            # Comment-to-view ratio (indicates engagement depth)
            comment_ratio = (metrics.comments / metrics.views) * 1000  # Per 1000 views
            comment_score = min(comment_ratio * 20, 40)
            
            # Save-to-view ratio (indicates content value)
            save_ratio = (metrics.saves / metrics.views) * 1000
            save_score = min(save_ratio * 15, 30)
            
            # Engagement diversity (variety of interaction types)
            engagement_types = sum([
                1 if metrics.likes > 0 else 0,
                1 if metrics.comments > 0 else 0,
                1 if metrics.shares > 0 else 0,
                1 if metrics.saves > 0 else 0
            ])
            diversity_score = (engagement_types / 4) * 30
            
            quality_score = comment_score + save_score + diversity_score
            
            return min(max(quality_score, 0), 100)
            
        except Exception as e:
            logger.error(f"Error calculating content quality score: {str(e)}")
            return 0.0
    
    def _calculate_audience_reach_score(self, metrics: ProcessedMetrics) -> float:
        """Calculate audience reach effectiveness"""
        try:
            platform_threshold = self._get_platform_thresholds(metrics.platform)
            
            # Normalize views against platform viral threshold
            reach_score = min((metrics.views / platform_threshold['viral_threshold']) * 100, 80)
            
            # Bonus for high engagement rate with good reach
            if metrics.views > 1000 and metrics.engagement_rate > platform_threshold['high_engagement_rate']:
                reach_score += 20
            
            return min(max(reach_score, 0), 100)
            
        except Exception as e:
            logger.error(f"Error calculating audience reach score: {str(e)}")
            return 0.0
    
    def _calculate_interaction_depth_score(self, metrics: ProcessedMetrics) -> float:
        """Calculate interaction depth based on meaningful engagements"""
        try:
            if metrics.views == 0:
                return 0.0
            
            # Weight high-intent interactions more heavily
            deep_interactions = (
                metrics.comments * 3 +  # Comments require thought
                metrics.shares * 5 +    # Shares require commitment
                metrics.saves * 4       # Saves indicate future intent
            )
            
            # Calculate depth ratio
            depth_ratio = deep_interactions / metrics.views
            
            # Convert to 0-100 scale
            depth_score = min(depth_ratio * 10000, 100)  # Scale factor for typical ratios
            
            return round(depth_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating interaction depth score: {str(e)}")
            return 0.0
    
    def _identify_success_patterns(self, metrics: ProcessedMetrics) -> Dict[str, Any]:
        """Identify patterns that contribute to success"""
        try:
            patterns = {}
            
            # High engagement rate pattern
            platform_threshold = self._get_platform_thresholds(metrics.platform)
            
            if metrics.engagement_rate > platform_threshold['high_engagement_rate']:
                patterns['high_engagement'] = {
                    'detected': True,
                    'engagement_rate': metrics.engagement_rate,
                    'threshold': platform_threshold['high_engagement_rate']
                }
            
            # Viral potential pattern
            if metrics.shares > 0 and metrics.views > 0:
                share_rate = metrics.shares / metrics.views
                if share_rate > 0.01:  # 1% share rate
                    patterns['viral_potential'] = {
                        'detected': True,
                        'share_rate': share_rate,
                        'total_shares': metrics.shares
                    }
            
            # Content value pattern (high saves)
            if metrics.saves > 0 and metrics.views > 0:
                save_rate = metrics.saves / metrics.views
                if save_rate > 0.005:  # 0.5% save rate
                    patterns['high_content_value'] = {
                        'detected': True,
                        'save_rate': save_rate,
                        'total_saves': metrics.saves
                    }
            
            # Community engagement pattern
            if metrics.comments > 0 and metrics.views > 0:
                comment_rate = metrics.comments / metrics.views
                if comment_rate > 0.01:  # 1% comment rate
                    patterns['strong_community_engagement'] = {
                        'detected': True,
                        'comment_rate': comment_rate,
                        'total_comments': metrics.comments
                    }
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error identifying success patterns: {str(e)}")
            return {}
    
    def _extract_content_features(self, metrics: ProcessedMetrics) -> Dict[str, Any]:
        """Extract content features for analysis"""
        try:
            features = {
                'platform': metrics.platform if isinstance(metrics.platform, str) else metrics.platform.value,
                'engagement_rate_category': self._categorize_engagement_rate(metrics),
                'content_type': metrics.content_type if isinstance(metrics.content_type, str) else metrics.content_type.value,
                'posting_time': {
                    'hour': metrics.publish_date.hour if metrics.publish_date else None,
                    'day_of_week': metrics.publish_date.weekday() if metrics.publish_date else None,
                    'is_weekend': metrics.publish_date.weekday() >= 5 if metrics.publish_date else None
                },
                'engagement_distribution': {
                    'likes_percentage': (metrics.likes / metrics.total_engagement * 100) if metrics.total_engagement > 0 else 0,
                    'comments_percentage': (metrics.comments / metrics.total_engagement * 100) if metrics.total_engagement > 0 else 0,
                    'shares_percentage': (metrics.shares / metrics.total_engagement * 100) if metrics.total_engagement > 0 else 0,
                    'saves_percentage': (metrics.saves / metrics.total_engagement * 100) if metrics.total_engagement > 0 else 0
                }
            }
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting content features: {str(e)}")
            return {}
    
    def _calculate_engagement_quality(self, metrics: ProcessedMetrics) -> float:
        """Calculate engagement quality based on interaction types"""
        if metrics.total_engagement == 0:
            return 0.0
        
        # Weight different engagement types
        weighted_score = (
            (metrics.comments / metrics.total_engagement) * 0.4 +  # Comments are high quality
            (metrics.shares / metrics.total_engagement) * 0.3 +    # Shares indicate value
            (metrics.saves / metrics.total_engagement) * 0.2 +     # Saves indicate future intent
            (metrics.likes / metrics.total_engagement) * 0.1       # Likes are lower quality but volume matters
        )
        
        return weighted_score
    
    def _calculate_time_decay_factor(self, publish_date: Optional[datetime]) -> float:
        """Calculate time decay factor for recency"""
        if not publish_date:
            return 0.5
        
        now = datetime.now(timezone.utc)
        hours_ago = (now - publish_date).total_seconds() / 3600
        
        # Decay factor: content is most valuable in first 24 hours
        if hours_ago <= 24:
            return 1.0
        elif hours_ago <= 168:  # 1 week
            return 0.8
        elif hours_ago <= 720:  # 1 month
            return 0.6
        else:
            return 0.4
    
    def _calculate_recency_boost(self, publish_date: Optional[datetime]) -> float:
        """Calculate recency boost for trending content"""
        if not publish_date:
            return 0.0
        
        now = datetime.now(timezone.utc)
        hours_ago = (now - publish_date).total_seconds() / 3600
        
        # Recent content gets boost for trending
        if hours_ago <= 6:
            return 1.0
        elif hours_ago <= 24:
            return 0.8
        elif hours_ago <= 72:
            return 0.5
        else:
            return 0.2
    
    def _categorize_engagement_rate(self, metrics: ProcessedMetrics) -> str:
        """Categorize engagement rate"""
        platform_threshold = self._get_platform_thresholds(metrics.platform)
        
        high_threshold = platform_threshold['high_engagement_rate']
        
        if metrics.engagement_rate >= high_threshold:
            return 'high'
        elif metrics.engagement_rate >= high_threshold * 0.5:
            return 'medium'
        else:
            return 'low'
    
    def _get_default_metrics(self) -> AdvancedMetrics:
        """Return default metrics in case of error"""
        return AdvancedMetrics(
            virality_score=0.0,
            trend_score=0.0,
            engagement_velocity=0.0,
            content_quality_score=0.0,
            audience_reach_score=0.0,
            interaction_depth_score=0.0,
            success_patterns={},
            content_features={}
        )
    
    def _get_platform_thresholds(self, platform) -> Dict[str, Any]:
        """Get platform thresholds, handling both string and enum values"""
        try:
            if isinstance(platform, str):
                # Convert string to enum
                platform_enum = PlatformType(platform)
            else:
                platform_enum = platform
            
            return self.platform_thresholds.get(
                platform_enum,
                self.platform_thresholds[PlatformType.INSTAGRAM]
            )
        except (ValueError, KeyError):
            # Fallback to Instagram if platform not found
            return self.platform_thresholds[PlatformType.INSTAGRAM]
