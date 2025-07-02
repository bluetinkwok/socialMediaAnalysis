"""
Recommendation Engine Module
Generates actionable recommendations based on identified success patterns.
"""

import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from db.database import SessionLocal
from db.models import Post, AnalyticsData, PlatformType, ContentType
from analytics.pattern_recognizer import PatternRecognizer

logger = logging.getLogger(__name__)


class RecommendationType:
    """Enum-like class for recommendation types"""
    CONTENT_CREATION = "content_creation"
    POSTING_STRATEGY = "posting_strategy"
    VISUAL_ELEMENTS = "visual_elements"
    TEXT_ELEMENTS = "text_elements"
    ENGAGEMENT_STRATEGY = "engagement_strategy"
    PLATFORM_SPECIFIC = "platform_specific"


class RecommendationEngine:
    """
    Engine for generating actionable recommendations based on identified success patterns
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or SessionLocal()
        self.pattern_recognizer = PatternRecognizer(self.db)
        
        # Initialize recommendation templates
        self._initialize_recommendation_templates()
    
    def _initialize_recommendation_templates(self):
        """Initialize templates for generating recommendations from patterns"""
        self.recommendation_templates = {
            # NLP-based pattern recommendations
            "positive_sentiment": {
                "type": RecommendationType.TEXT_ELEMENTS,
                "template": "Use positive language in your content. {details}",
                "impact_score": 8,
                "platform_specific": False,
                "content_type_specific": False
            },
            "high_readability": {
                "type": RecommendationType.TEXT_ELEMENTS,
                "template": "Keep your text simple and readable. {details}",
                "impact_score": 7,
                "platform_specific": False,
                "content_type_specific": True
            },
            "topic_relevance": {
                "type": RecommendationType.CONTENT_CREATION,
                "template": "Focus on topics relevant to your audience: {details}",
                "impact_score": 9,
                "platform_specific": True,
                "content_type_specific": False
            },
            "keyword_optimized": {
                "type": RecommendationType.TEXT_ELEMENTS,
                "template": "Include these high-performing keywords: {details}",
                "impact_score": 8,
                "platform_specific": True,
                "content_type_specific": False
            },
            "emotional_triggers": {
                "type": RecommendationType.TEXT_ELEMENTS,
                "template": "Use emotional language that resonates with your audience. {details}",
                "impact_score": 8,
                "platform_specific": False,
                "content_type_specific": False
            },
            
            # CV-based pattern recommendations
            "visual_appeal": {
                "type": RecommendationType.VISUAL_ELEMENTS,
                "template": "Create visually appealing content with {details}",
                "impact_score": 8,
                "platform_specific": True,
                "content_type_specific": True
            },
            "human_presence": {
                "type": RecommendationType.VISUAL_ELEMENTS,
                "template": "Include human faces or people in your visuals. {details}",
                "impact_score": 9,
                "platform_specific": False,
                "content_type_specific": True
            },
            "color_harmony": {
                "type": RecommendationType.VISUAL_ELEMENTS,
                "template": "Use harmonious color schemes: {details}",
                "impact_score": 7,
                "platform_specific": False,
                "content_type_specific": True
            },
            "scene_relevance": {
                "type": RecommendationType.VISUAL_ELEMENTS,
                "template": "Ensure visual scenes are relevant to your message. {details}",
                "impact_score": 8,
                "platform_specific": False,
                "content_type_specific": True
            },
            
            # Combined NLP+CV pattern recommendations
            "emotional_visual_harmony": {
                "type": RecommendationType.CONTENT_CREATION,
                "template": "Match emotional tone in text with visual elements. {details}",
                "impact_score": 9,
                "platform_specific": False,
                "content_type_specific": True
            },
            "storytelling_excellence": {
                "type": RecommendationType.CONTENT_CREATION,
                "template": "Tell a compelling story across text and visuals. {details}",
                "impact_score": 9,
                "platform_specific": False,
                "content_type_specific": True
            },
            "topic_scene_alignment": {
                "type": RecommendationType.CONTENT_CREATION,
                "template": "Align discussed topics with visual scenes. {details}",
                "impact_score": 8,
                "platform_specific": False,
                "content_type_specific": True
            },
            "personality_showcase": {
                "type": RecommendationType.CONTENT_CREATION,
                "template": "Showcase personality through both text and visuals. {details}",
                "impact_score": 8,
                "platform_specific": True,
                "content_type_specific": False
            },
            "visual_text_contrast": {
                "type": RecommendationType.CONTENT_CREATION,
                "template": "Create intentional contrast between text and visuals. {details}",
                "impact_score": 7,
                "platform_specific": False,
                "content_type_specific": True
            },
            
            # Temporal pattern recommendations
            "optimal_posting_time": {
                "type": RecommendationType.POSTING_STRATEGY,
                "template": "Post content during optimal engagement hours: {details}",
                "impact_score": 8,
                "platform_specific": True,
                "content_type_specific": False
            },
            "weekend_success": {
                "type": RecommendationType.POSTING_STRATEGY,
                "template": "Consider posting content on weekends. {details}",
                "impact_score": 7,
                "platform_specific": True,
                "content_type_specific": False
            },
            "rapid_growth": {
                "type": RecommendationType.ENGAGEMENT_STRATEGY,
                "template": "Optimize for rapid engagement growth by {details}",
                "impact_score": 9,
                "platform_specific": True,
                "content_type_specific": False
            },
            
            # Content type specific recommendations
            "successful_video": {
                "type": RecommendationType.CONTENT_CREATION,
                "template": "Create video content with these characteristics: {details}",
                "impact_score": 8,
                "platform_specific": True,
                "content_type_specific": True
            },
            "successful_image": {
                "type": RecommendationType.CONTENT_CREATION,
                "template": "Create image content with these characteristics: {details}",
                "impact_score": 8,
                "platform_specific": True,
                "content_type_specific": True
            },
            "successful_text": {
                "type": RecommendationType.CONTENT_CREATION,
                "template": "Create text content with these characteristics: {details}",
                "impact_score": 8,
                "platform_specific": True,
                "content_type_specific": True
            }
        }
        
        # Platform-specific recommendation details
        self.platform_details = {
            PlatformType.YOUTUBE: {
                "positive_sentiment": "Focus on enthusiastic language and upbeat tone.",
                "topic_relevance": "trending topics in your niche on YouTube",
                "keyword_optimized": "research-backed YouTube SEO keywords",
                "visual_appeal": "high-quality thumbnails and video quality",
                "personality_showcase": "consistent on-camera personality",
                "optimal_posting_time": "typically weekday evenings",
                "rapid_growth": "responding to comments in the first hour",
                "successful_video": "clear intro, engaging thumbnails, and strong calls to action"
            },
            PlatformType.INSTAGRAM: {
                "positive_sentiment": "Use aspirational and inspirational language.",
                "topic_relevance": "visually-oriented trending topics",
                "keyword_optimized": "relevant hashtags (7-12 per post)",
                "visual_appeal": "high-contrast, well-composed images",
                "personality_showcase": "consistent visual aesthetic and voice",
                "optimal_posting_time": "typically 10-11am or 7-9pm",
                "rapid_growth": "engaging with similar content before posting",
                "successful_image": "high-quality images with strong focal points"
            },
            PlatformType.THREADS: {
                "positive_sentiment": "Mix positivity with authenticity and humor.",
                "topic_relevance": "current conversations in your niche",
                "keyword_optimized": "trending topics and conversational keywords",
                "visual_appeal": "clean, simple visuals that complement text",
                "personality_showcase": "distinctive voice and perspective",
                "optimal_posting_time": "typically midday and early evening",
                "rapid_growth": "joining active conversations with valuable insights",
                "successful_text": "concise, conversation-starting text with personality"
            },
            PlatformType.REDNOTE: {
                "positive_sentiment": "Combine positivity with authentic expression.",
                "topic_relevance": "music and culture-focused topics",
                "keyword_optimized": "music-related keywords and artist references",
                "visual_appeal": "vibrant, music-culture aligned visuals",
                "personality_showcase": "unique artistic perspective",
                "optimal_posting_time": "typically evenings and late night",
                "rapid_growth": "collaborating with other creators",
                "successful_video": "short, music-focused clips with strong visual identity"
            }
        }
        
        # Content type specific recommendation details
        self.content_type_details = {
            ContentType.VIDEO: {
                "high_readability": "Use clear, concise scripts with short sentences.",
                "visual_appeal": "good lighting, composition, and movement",
                "human_presence": "feature people prominently, especially in thumbnails",
                "color_harmony": "consistent color grading throughout",
                "scene_relevance": "scenes that clearly illustrate your points",
                "emotional_visual_harmony": "matching music and visuals to the emotional tone",
                "storytelling_excellence": "clear narrative arc with beginning, middle, and end",
                "topic_scene_alignment": "visuals that directly support each talking point",
                "visual_text_contrast": "readable on-screen text with good contrast"
            },
            ContentType.IMAGE: {
                "high_readability": "Limit text overlay to essential points with clear fonts.",
                "visual_appeal": "strong composition following rule of thirds",
                "human_presence": "authentic human expressions and interactions",
                "color_harmony": "cohesive color palette with 2-3 main colors",
                "scene_relevance": "imagery that directly conveys your message",
                "emotional_visual_harmony": "visual tone matching caption emotion",
                "storytelling_excellence": "images that imply a narrative",
                "topic_scene_alignment": "visuals directly illustrating caption topics",
                "visual_text_contrast": "text overlay with strong contrast against background"
            },
            ContentType.TEXT: {
                "high_readability": "Short paragraphs, simple words, and clear structure.",
                "visual_appeal": "clean formatting with appropriate spacing",
                "human_presence": "personal stories or perspectives",
                "storytelling_excellence": "narrative structure with clear flow",
                "topic_scene_alignment": "examples that vividly illustrate concepts"
            },
            ContentType.MIXED: {
                "high_readability": "Balance text and visuals, with each enhancing the other.",
                "visual_appeal": "cohesive design across text and visual elements",
                "human_presence": "human elements in both text and visuals",
                "color_harmony": "consistent color theme across all elements",
                "scene_relevance": "visuals that enhance rather than distract from text",
                "emotional_visual_harmony": "consistent emotional tone across elements",
                "storytelling_excellence": "complementary storytelling across formats",
                "topic_scene_alignment": "tight integration of topics across formats",
                "visual_text_contrast": "clear distinction between text and visual elements"
            }
        }
    
    def generate_recommendations(
        self,
        patterns: Dict[str, Any],
        platform: Optional[PlatformType] = None,
        content_type: Optional[ContentType] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate actionable recommendations based on identified success patterns
        
        Args:
            patterns: Dictionary of identified success patterns
            platform: Optional platform type to target recommendations
            content_type: Optional content type to target recommendations
            limit: Maximum number of recommendations to return
            
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        # Process each pattern to generate recommendations
        for pattern_name, pattern_data in patterns.items():
            if pattern_name not in self.recommendation_templates:
                continue
                
            template = self.recommendation_templates[pattern_name]
            details = self._get_recommendation_details(pattern_name, platform, content_type)
            
            # Skip if this is a platform-specific recommendation but no platform provided
            if template["platform_specific"] and not platform:
                continue
                
            # Skip if this is a content-type-specific recommendation but no content type provided
            if template["content_type_specific"] and not content_type:
                continue
            
            # Create recommendation
            recommendation = {
                "id": f"rec_{pattern_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "type": template["type"],
                "text": template["template"].format(details=details),
                "impact_score": template["impact_score"],
                "source_pattern": pattern_name,
                "pattern_confidence": pattern_data.get("confidence", 0.7),
                "created_at": datetime.now().isoformat(),
                "platform_specific": template["platform_specific"],
                "content_type_specific": template["content_type_specific"],
                "platform": platform.value if platform else None,
                "content_type": content_type.value if content_type else None
            }
            
            recommendations.append(recommendation)
        
        # Sort by impact score and pattern confidence
        recommendations.sort(
            key=lambda x: (x["impact_score"] * x["pattern_confidence"]),
            reverse=True
        )
        
        # Return limited number of recommendations
        return recommendations[:limit]
    
    def _get_recommendation_details(
        self,
        pattern_name: str,
        platform: Optional[PlatformType] = None,
        content_type: Optional[ContentType] = None
    ) -> str:
        """
        Get detailed recommendation text based on pattern, platform, and content type
        
        Args:
            pattern_name: Name of the pattern
            platform: Optional platform type
            content_type: Optional content type
            
        Returns:
            String with detailed recommendation text
        """
        details = []
        
        # Add platform-specific details if available
        if platform and platform in self.platform_details:
            platform_details = self.platform_details[platform]
            if pattern_name in platform_details:
                details.append(platform_details[pattern_name])
        
        # Add content-type-specific details if available
        if content_type and content_type in self.content_type_details:
            content_details = self.content_type_details[content_type]
            if pattern_name in content_details:
                details.append(content_details[pattern_name])
        
        # Return combined details or generic message
        if details:
            return " ".join(details)
        return "Analyze your best-performing content for specific implementation details."
    
    def get_recommendations_for_post(
        self,
        post_id: int,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Get recommendations for a specific post
        
        Args:
            post_id: ID of the post
            limit: Maximum number of recommendations to return
            
        Returns:
            Dictionary with recommendations and metadata
        """
        # Get post and analytics data
        post = self.db.query(Post).filter(Post.id == post_id).first()
        if not post:
            return {
                "success": False,
                "message": f"Post with ID {post_id} not found"
            }
            
        analytics = self.db.query(AnalyticsData).filter(AnalyticsData.post_id == post_id).first()
        if not analytics or not analytics.success_patterns:
            return {
                "success": True,
                "post_id": post_id,
                "recommendations": [],
                "count": 0,
                "message": "No success patterns found for this post to base recommendations on"
            }
        
        # Generate recommendations based on patterns
        recommendations = self.generate_recommendations(
            patterns=analytics.success_patterns,
            platform=post.platform,
            content_type=post.content_type,
            limit=limit
        )
        
        return {
            "success": True,
            "post_id": post_id,
            "recommendations": recommendations,
            "count": len(recommendations)
        }
    
    def get_general_recommendations(
        self,
        platform: Optional[str] = None,
        content_type: Optional[str] = None,
        days: int = 30,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Get general recommendations based on top success patterns
        
        Args:
            platform: Optional platform filter
            content_type: Optional content type filter
            days: Number of days to look back for patterns
            limit: Maximum number of recommendations to return
            
        Returns:
            Dictionary with recommendations and metadata
        """
        # Convert string parameters to enums if provided
        platform_enum = None
        if platform:
            try:
                platform_enum = PlatformType(platform.lower())
            except ValueError:
                return {
                    "success": False,
                    "message": f"Invalid platform: {platform}"
                }
                
        content_type_enum = None
        if content_type:
            try:
                content_type_enum = ContentType(content_type.lower())
            except ValueError:
                return {
                    "success": False,
                    "message": f"Invalid content type: {content_type}"
                }
        
        # Get top patterns
        top_patterns = self.pattern_recognizer.get_top_patterns(
            limit=limit * 2,  # Get more patterns than needed to ensure enough recommendations
            start_date=datetime.now() - timedelta(days=days),
            end_date=datetime.now()
        )
        
        # Convert list of patterns to dictionary format needed for recommendation generation
        patterns_dict = {}
        for pattern in top_patterns:
            patterns_dict[pattern["name"]] = {
                "confidence": pattern.get("confidence", 0.7),
                "frequency": pattern.get("frequency", 1),
                "details": pattern.get("details", {})
            }
        
        # Generate recommendations
        recommendations = self.generate_recommendations(
            patterns=patterns_dict,
            platform=platform_enum,
            content_type=content_type_enum,
            limit=limit
        )
        
        return {
            "success": True,
            "recommendations": recommendations,
            "count": len(recommendations),
            "filters": {
                "platform": platform,
                "content_type": content_type,
                "days": days
            }
        }
    
    def get_recommendations_by_type(
        self,
        recommendation_type: str,
        platform: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Get recommendations filtered by type
        
        Args:
            recommendation_type: Type of recommendations to retrieve
            platform: Optional platform filter
            content_type: Optional content type filter
            limit: Maximum number of recommendations to return
            
        Returns:
            Dictionary with recommendations and metadata
        """
        # Validate recommendation type
        valid_types = vars(RecommendationType).values()
        if recommendation_type not in valid_types:
            return {
                "success": False,
                "message": f"Invalid recommendation type: {recommendation_type}. Valid types are: {', '.join(valid_types)}"
            }
        
        # Get general recommendations first
        result = self.get_general_recommendations(
            platform=platform,
            content_type=content_type,
            limit=limit * 2  # Get more recommendations to filter from
        )
        
        if not result["success"]:
            return result
        
        # Filter by type
        filtered_recommendations = [
            rec for rec in result["recommendations"]
            if rec["type"] == recommendation_type
        ]
        
        return {
            "success": True,
            "recommendations": filtered_recommendations[:limit],
            "count": len(filtered_recommendations[:limit]),
            "recommendation_type": recommendation_type,
            "filters": {
                "platform": platform,
                "content_type": content_type
            }
        }
    
    def store_recommendation(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store a recommendation for future reference
        
        Args:
            recommendation: Recommendation dictionary to store
            
        Returns:
            Dictionary with status and stored recommendation
        """
        # In a real implementation, this would store to a database table
        # For now, we'll just return the recommendation as if it was stored
        
        return {
            "success": True,
            "message": "Recommendation stored successfully",
            "recommendation": recommendation
        } 