"""
Performance Scoring Algorithm
Combines advanced engagement metrics into a single performance score
"""

import logging
import math
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

from .data_processor import ProcessedMetrics
from .metrics_calculator import AdvancedMetrics
from db.models import PlatformType

logger = logging.getLogger(__name__)


@dataclass
class ScoringWeights:
    """Configuration for scoring algorithm weights"""
    virality_weight: float = 0.25
    trend_weight: float = 0.25
    content_quality_weight: float = 0.20
    audience_reach_weight: float = 0.15
    interaction_depth_weight: float = 0.15
    
    def validate(self) -> bool:
        """Validate that weights sum to 1.0"""
        total = (
            self.virality_weight + 
            self.trend_weight + 
            self.content_quality_weight + 
            self.audience_reach_weight + 
            self.interaction_depth_weight
        )
        return abs(total - 1.0) < 0.001


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of performance score calculation"""
    final_score: float
    weighted_components: Dict[str, float]
    bonuses: Dict[str, float]
    penalties: Dict[str, float]
    platform_adjustment: float
    confidence_score: float


class ScoringAlgorithm:
    """Advanced performance scoring algorithm"""
    
    def __init__(self, custom_weights: Optional[ScoringWeights] = None):
        self.weights = custom_weights or ScoringWeights()
        
        if not self.weights.validate():
            logger.warning("Scoring weights do not sum to 1.0, using default weights")
            self.weights = ScoringWeights()
        
        # Platform-specific scoring adjustments
        self.platform_adjustments = {
            PlatformType.YOUTUBE: {
                'base_multiplier': 1.0,
                'virality_boost': 1.2,  # YouTube rewards viral content more
                'quality_boost': 1.1,   # Long-form content quality matters
                'reach_penalty': 0.9    # Harder to reach large audiences
            },
            PlatformType.INSTAGRAM: {
                'base_multiplier': 1.0,
                'virality_boost': 1.0,
                'quality_boost': 1.0,
                'reach_penalty': 1.0
            },
            PlatformType.THREADS: {
                'base_multiplier': 0.95,  # Newer platform, lower baseline
                'virality_boost': 1.3,    # High viral potential
                'quality_boost': 0.9,     # Less focus on content quality
                'reach_penalty': 0.8      # Smaller user base
            },
            PlatformType.REDNOTE: {
                'base_multiplier': 1.05,  # High engagement platform
                'virality_boost': 1.1,
                'quality_boost': 1.2,     # Quality content performs well
                'reach_penalty': 0.85     # Niche platform
            }
        }
        
        # Success pattern bonuses
        self.pattern_bonuses = {
            'high_engagement': 5.0,
            'viral_potential': 8.0,
            'high_content_value': 6.0,
            'strong_community_engagement': 4.0,
            'trending_hashtags': 3.0,
            'optimal_timing': 2.0
        }
    
    def calculate_performance_score(
        self, 
        processed_metrics: ProcessedMetrics, 
        advanced_metrics: AdvancedMetrics
    ) -> float:
        """
        Calculate the final performance score
        
        Args:
            processed_metrics: Basic processed metrics
            advanced_metrics: Advanced calculated metrics
            
        Returns:
            float: Performance score (0-100)
        """
        try:
            # Calculate base weighted score
            base_score = self._calculate_base_score(advanced_metrics)
            
            # Apply platform-specific adjustments
            platform_adjusted_score = self._apply_platform_adjustments(
                base_score, processed_metrics, advanced_metrics
            )
            
            # Apply success pattern bonuses
            bonus_adjusted_score = self._apply_pattern_bonuses(
                platform_adjusted_score, advanced_metrics.success_patterns
            )
            
            # Apply engagement quality multiplier
            quality_adjusted_score = self._apply_quality_multiplier(
                bonus_adjusted_score, processed_metrics, advanced_metrics
            )
            
            # Apply recency factor
            final_score = self._apply_recency_factor(
                quality_adjusted_score, processed_metrics.publish_date
            )
            
            # Normalize to 0-100 range
            normalized_score = min(max(final_score, 0), 100)
            
            logger.info(f"Calculated performance score: {normalized_score:.2f}")
            return round(normalized_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating performance score: {str(e)}")
            return 0.0
    
    def calculate_detailed_score(
        self, 
        processed_metrics: ProcessedMetrics, 
        advanced_metrics: AdvancedMetrics
    ) -> ScoreBreakdown:
        """
        Calculate performance score with detailed breakdown
        
        Args:
            processed_metrics: Basic processed metrics
            advanced_metrics: Advanced calculated metrics
            
        Returns:
            ScoreBreakdown: Detailed score breakdown
        """
        try:
            # Calculate weighted components
            weighted_components = {
                'virality': advanced_metrics.virality_score * self.weights.virality_weight,
                'trend': advanced_metrics.trend_score * self.weights.trend_weight,
                'content_quality': advanced_metrics.content_quality_score * self.weights.content_quality_weight,
                'audience_reach': advanced_metrics.audience_reach_score * self.weights.audience_reach_weight,
                'interaction_depth': advanced_metrics.interaction_depth_score * self.weights.interaction_depth_weight
            }
            
            base_score = sum(weighted_components.values())
            
            # Calculate bonuses
            bonuses = self._calculate_bonuses(processed_metrics, advanced_metrics)
            
            # Calculate penalties (if any)
            penalties = self._calculate_penalties(processed_metrics, advanced_metrics)
            
            # Platform adjustment
            platform_adjustment = self._get_platform_adjustment(processed_metrics)
            
            # Confidence score
            confidence_score = self._calculate_confidence_score(processed_metrics, advanced_metrics)
            
            # Final score calculation
            final_score = (
                base_score + 
                sum(bonuses.values()) - 
                sum(penalties.values())
            ) * platform_adjustment
            
            final_score = min(max(final_score, 0), 100)
            
            return ScoreBreakdown(
                final_score=round(final_score, 2),
                weighted_components=weighted_components,
                bonuses=bonuses,
                penalties=penalties,
                platform_adjustment=platform_adjustment,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"Error calculating detailed score: {str(e)}")
            return ScoreBreakdown(
                final_score=0.0,
                weighted_components={},
                bonuses={},
                penalties={},
                platform_adjustment=1.0,
                confidence_score=0.0
            )
    
    def _calculate_base_score(self, advanced_metrics: AdvancedMetrics) -> float:
        """Calculate base weighted score from advanced metrics"""
        return (
            advanced_metrics.virality_score * self.weights.virality_weight +
            advanced_metrics.trend_score * self.weights.trend_weight +
            advanced_metrics.content_quality_score * self.weights.content_quality_weight +
            advanced_metrics.audience_reach_score * self.weights.audience_reach_weight +
            advanced_metrics.interaction_depth_score * self.weights.interaction_depth_weight
        )
    
    def _apply_platform_adjustments(
        self, 
        base_score: float, 
        processed_metrics: ProcessedMetrics, 
        advanced_metrics: AdvancedMetrics
    ) -> float:
        """Apply platform-specific adjustments to the score"""
        try:
            platform_key = processed_metrics.platform
            if isinstance(platform_key, str):
                platform_enum = PlatformType(platform_key)
            else:
                platform_enum = platform_key
            
            adjustments = self.platform_adjustments.get(
                platform_enum, 
                self.platform_adjustments[PlatformType.INSTAGRAM]
            )
            
            # Apply base multiplier
            adjusted_score = base_score * adjustments['base_multiplier']
            
            # Apply component-specific boosts
            if advanced_metrics.virality_score > 50:
                adjusted_score *= adjustments['virality_boost']
            
            if advanced_metrics.content_quality_score > 70:
                adjusted_score *= adjustments['quality_boost']
            
            if advanced_metrics.audience_reach_score < 30:
                adjusted_score *= adjustments['reach_penalty']
            
            return adjusted_score
            
        except Exception as e:
            logger.error(f"Error applying platform adjustments: {str(e)}")
            return base_score
    
    def _apply_pattern_bonuses(self, score: float, success_patterns: Dict[str, Any]) -> float:
        """Apply bonuses based on detected success patterns"""
        try:
            total_bonus = 0.0
            
            for pattern_name, pattern_data in success_patterns.items():
                if isinstance(pattern_data, dict) and pattern_data.get('detected', False):
                    bonus = self.pattern_bonuses.get(pattern_name, 0.0)
                    total_bonus += bonus
                    logger.debug(f"Applied {bonus} bonus for pattern: {pattern_name}")
            
            return score + total_bonus
            
        except Exception as e:
            logger.error(f"Error applying pattern bonuses: {str(e)}")
            return score
    
    def _apply_quality_multiplier(
        self, 
        score: float, 
        processed_metrics: ProcessedMetrics, 
        advanced_metrics: AdvancedMetrics
    ) -> float:
        """Apply quality-based multiplier"""
        try:
            # High engagement rate gets a boost
            if processed_metrics.engagement_rate > 5.0:  # 5% engagement rate
                score *= 1.1
            elif processed_metrics.engagement_rate > 10.0:  # 10% engagement rate
                score *= 1.2
            
            # High interaction depth gets a boost
            if advanced_metrics.interaction_depth_score > 80:
                score *= 1.05
            
            return score
            
        except Exception as e:
            logger.error(f"Error applying quality multiplier: {str(e)}")
            return score
    
    def _apply_recency_factor(self, score: float, publish_date: Optional[datetime]) -> float:
        """Apply recency factor to boost recent high-performing content"""
        try:
            if not publish_date:
                return score
            
            now = datetime.now(timezone.utc)
            hours_ago = (now - publish_date).total_seconds() / 3600
            
            # Boost recent high-performing content
            if score > 70 and hours_ago <= 24:  # Last 24 hours
                return score * 1.1
            elif score > 60 and hours_ago <= 72:  # Last 3 days
                return score * 1.05
            
            return score
            
        except Exception as e:
            logger.error(f"Error applying recency factor: {str(e)}")
            return score
    
    def _calculate_bonuses(
        self, 
        processed_metrics: ProcessedMetrics, 
        advanced_metrics: AdvancedMetrics
    ) -> Dict[str, float]:
        """Calculate all applicable bonuses"""
        bonuses = {}
        
        # Pattern bonuses
        for pattern_name, pattern_data in advanced_metrics.success_patterns.items():
            if isinstance(pattern_data, dict) and pattern_data.get('detected', False):
                bonuses[f"pattern_{pattern_name}"] = self.pattern_bonuses.get(pattern_name, 0.0)
        
        # Performance bonuses
        if processed_metrics.engagement_rate > 10.0:
            bonuses['exceptional_engagement'] = 5.0
        
        if advanced_metrics.virality_score > 80:
            bonuses['viral_content'] = 10.0
        
        return bonuses
    
    def _calculate_penalties(
        self, 
        processed_metrics: ProcessedMetrics, 
        advanced_metrics: AdvancedMetrics
    ) -> Dict[str, float]:
        """Calculate any applicable penalties"""
        penalties = {}
        
        # Low engagement penalty
        if processed_metrics.engagement_rate < 0.5:  # Less than 0.5%
            penalties['low_engagement'] = 5.0
        
        # No meaningful interaction penalty
        if advanced_metrics.interaction_depth_score < 10:
            penalties['shallow_interaction'] = 3.0
        
        return penalties
    
    def _get_platform_adjustment(self, processed_metrics: ProcessedMetrics) -> float:
        """Get platform-specific adjustment multiplier"""
        try:
            platform_key = processed_metrics.platform
            if isinstance(platform_key, str):
                platform_enum = PlatformType(platform_key)
            else:
                platform_enum = platform_key
            
            adjustments = self.platform_adjustments.get(
                platform_enum, 
                self.platform_adjustments[PlatformType.INSTAGRAM]
            )
            
            return adjustments['base_multiplier']
            
        except Exception:
            return 1.0
    
    def _calculate_confidence_score(
        self, 
        processed_metrics: ProcessedMetrics, 
        advanced_metrics: AdvancedMetrics
    ) -> float:
        """Calculate confidence in the score based on data quality"""
        try:
            confidence_factors = []
            
            # Data completeness
            if processed_metrics.views > 0:
                confidence_factors.append(20)
            if processed_metrics.total_engagement > 0:
                confidence_factors.append(20)
            if processed_metrics.publish_date:
                confidence_factors.append(15)
            
            # Engagement diversity
            engagement_types = sum([
                1 if processed_metrics.likes > 0 else 0,
                1 if processed_metrics.comments > 0 else 0,
                1 if processed_metrics.shares > 0 else 0,
                1 if processed_metrics.saves > 0 else 0
            ])
            confidence_factors.append(engagement_types * 5)
            
            # Sample size confidence
            if processed_metrics.views > 1000:
                confidence_factors.append(20)
            elif processed_metrics.views > 100:
                confidence_factors.append(10)
            
            return min(sum(confidence_factors), 100)
            
        except Exception as e:
            logger.error(f"Error calculating confidence score: {str(e)}")
            return 50.0  # Default medium confidence 