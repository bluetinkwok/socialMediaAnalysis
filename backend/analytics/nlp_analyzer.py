"""
NLP Analyzer Module
Integrates NLP capabilities into the analytics engine for text analysis
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from db.models import Post, AnalyticsData
from services.nlp_service import NLPService, NLPResult

logger = logging.getLogger(__name__)


class NLPAnalyzer:
    """
    NLP Analyzer for integrating text analysis into the analytics pipeline
    """
    
    def __init__(self):
        """Initialize NLP Analyzer with NLP service"""
        self.nlp_service = NLPService()
        logger.info("NLP Analyzer initialized")
    
    def analyze_post(self, post: Post) -> Dict[str, Any]:
        """
        Analyze post text content using NLP
        
        Args:
            post: Post model instance
            
        Returns:
            Dict[str, Any]: NLP analysis results
        """
        # Extract text content from post
        post_data = {
            "title": post.title,
            "description": post.description,
            "content_text": post.content_text,
            "hashtags": post.hashtags
        }
        
        # Perform NLP analysis
        nlp_result = self.nlp_service.analyze_post(post_data)
        
        # Log analysis completion
        logger.info(f"Completed NLP analysis for post {post.id}: "
                   f"sentiment={nlp_result.sentiment_label}, "
                   f"topics={len(nlp_result.topics)}")
        
        return nlp_result.to_dict()
    
    def extract_content_features(self, post: Post) -> Dict[str, Any]:
        """
        Extract content features from post using NLP analysis
        
        Args:
            post: Post model instance
            
        Returns:
            Dict[str, Any]: Content features
        """
        # Analyze post content
        nlp_result = self.analyze_post(post)
        
        # Extract key features
        features = {
            "sentiment": nlp_result["sentiment"],
            "readability_score": nlp_result["text_stats"]["readability_score"],
            "keywords": [k["keyword"] for k in nlp_result["keywords"][:5]],
            "topics": [t["name"] for t in nlp_result["topics"][:3]],
            "entities": [e["text"] for e in nlp_result["entities"][:10]],
            "text_stats": {
                "word_count": nlp_result["text_stats"]["word_count"],
                "sentence_count": nlp_result["text_stats"]["sentence_count"],
                "avg_sentence_length": nlp_result["text_stats"]["avg_sentence_length"]
            }
        }
        
        return features
    
    def calculate_content_quality_score(self, nlp_result: Dict[str, Any]) -> float:
        """
        Calculate content quality score based on NLP analysis
        
        Args:
            nlp_result: NLP analysis results
            
        Returns:
            float: Content quality score (0-100)
        """
        score = 0.0
        
        # Base score from text statistics
        text_stats = nlp_result["text_stats"]
        
        # Reward reasonable content length (neither too short nor too long)
        word_count = text_stats["word_count"]
        if word_count > 0:
            if word_count < 10:
                length_score = word_count / 10 * 10  # 0-10 for very short content
            elif word_count < 50:
                length_score = 10 + (word_count - 10) / 40 * 15  # 10-25 for short content
            elif word_count < 200:
                length_score = 25 + (word_count - 50) / 150 * 15  # 25-40 for medium content
            elif word_count < 500:
                length_score = 40 + (word_count - 200) / 300 * 10  # 40-50 for long content
            else:
                length_score = 50  # Max for very long content
            
            score += length_score
        
        # Readability score (0-20 points)
        readability = text_stats["readability_score"]
        readability_score = min(20, readability / 5)
        score += readability_score
        
        # Keyword relevance (0-10 points)
        keyword_score = 0
        if nlp_result["keywords"]:
            # Average relevance of top 5 keywords
            top_keywords = nlp_result["keywords"][:5]
            avg_relevance = sum(k["relevance"] for k in top_keywords) / len(top_keywords)
            keyword_score = avg_relevance * 10
        
        score += keyword_score
        
        # Topic coherence (0-10 points)
        topic_score = 0
        if nlp_result["topics"]:
            # Number of topics identified (more is better, up to a point)
            topic_count = min(5, len(nlp_result["topics"]))
            topic_score = topic_count * 2
        
        score += topic_score
        
        # Sentiment impact (0-10 points)
        # Non-neutral content tends to perform better
        sentiment = nlp_result["sentiment"]
        sentiment_magnitude = sentiment["magnitude"]
        sentiment_score = min(10, sentiment_magnitude * 5)
        
        score += sentiment_score
        
        # Cap at 100
        return min(100, score)
    
    def get_sentiment_boost(self, sentiment_score: float, platform: str) -> float:
        """
        Calculate sentiment-based performance boost based on platform
        
        Args:
            sentiment_score: Sentiment score (-1 to 1)
            platform: Platform name
            
        Returns:
            float: Sentiment boost factor
        """
        # Different platforms may respond differently to sentiment
        # For example, positive content might perform better on some platforms
        if platform == "youtube":
            # YouTube tends to favor positive content
            if sentiment_score > 0.5:
                return 1.2  # 20% boost for very positive content
            elif sentiment_score > 0.2:
                return 1.1  # 10% boost for moderately positive content
            elif sentiment_score < -0.5:
                return 0.9  # 10% penalty for very negative content
        
        elif platform == "instagram":
            # Instagram also tends to favor positive content
            if sentiment_score > 0.5:
                return 1.15  # 15% boost for very positive content
            elif sentiment_score > 0.2:
                return 1.05  # 5% boost for moderately positive content
        
        elif platform == "threads":
            # Threads may have different sentiment patterns
            # For now, use a neutral approach
            if abs(sentiment_score) > 0.7:
                return 1.1  # 10% boost for strong sentiment (either direction)
        
        elif platform == "rednote":
            # Rednote may have its own patterns
            # For now, use a neutral approach
            if abs(sentiment_score) > 0.5:
                return 1.05  # 5% boost for strong sentiment (either direction)
        
        # Default: no adjustment
        return 1.0
    
    def identify_content_patterns(self, nlp_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify content patterns based on NLP analysis
        
        Args:
            nlp_result: NLP analysis results
            
        Returns:
            List[Dict[str, Any]]: Identified patterns
        """
        patterns = []
        
        # Sentiment patterns
        sentiment = nlp_result["sentiment"]
        if sentiment["score"] > 0.5:
            patterns.append({
                "type": "sentiment",
                "name": "highly_positive",
                "confidence": min(1.0, sentiment["score"]),
                "description": "Content has a very positive tone"
            })
        elif sentiment["score"] < -0.5:
            patterns.append({
                "type": "sentiment",
                "name": "highly_negative",
                "confidence": min(1.0, abs(sentiment["score"])),
                "description": "Content has a very negative tone"
            })
        
        # Text complexity patterns
        text_stats = nlp_result["text_stats"]
        if text_stats["readability_score"] > 80:
            patterns.append({
                "type": "readability",
                "name": "easy_to_read",
                "confidence": text_stats["readability_score"] / 100,
                "description": "Content is very easy to read"
            })
        elif text_stats["readability_score"] < 30:
            patterns.append({
                "type": "readability",
                "name": "complex_language",
                "confidence": (100 - text_stats["readability_score"]) / 100,
                "description": "Content uses complex language"
            })
        
        # Length patterns
        if text_stats["word_count"] > 300:
            patterns.append({
                "type": "length",
                "name": "long_form",
                "confidence": min(1.0, text_stats["word_count"] / 500),
                "description": "Content is long-form"
            })
        elif text_stats["word_count"] < 50:
            patterns.append({
                "type": "length",
                "name": "concise",
                "confidence": min(1.0, (50 - text_stats["word_count"]) / 50),
                "description": "Content is concise and to the point"
            })
        
        # Keyword patterns
        if nlp_result["keywords"] and len(nlp_result["keywords"]) >= 3:
            top_keywords = nlp_result["keywords"][:3]
            avg_relevance = sum(k["relevance"] for k in top_keywords) / len(top_keywords)
            if avg_relevance > 0.7:
                patterns.append({
                    "type": "keywords",
                    "name": "focused_keywords",
                    "confidence": avg_relevance,
                    "description": "Content has strong focus on specific keywords"
                })
        
        return patterns
