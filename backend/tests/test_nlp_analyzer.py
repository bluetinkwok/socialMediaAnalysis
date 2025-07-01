"""
Tests for NLP Analyzer
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from analytics.nlp_analyzer import NLPAnalyzer
from services.nlp_service import NLPResult
from db.models import Post, PlatformType, ContentType


class TestNLPAnalyzer:
    """Test suite for NLP Analyzer"""
    
    def setup_method(self):
        """Set up test environment before each test method"""
        self.nlp_analyzer = NLPAnalyzer()
        
        # Create a mock post
        self.mock_post = MagicMock(spec=Post)
        self.mock_post.id = 1
        self.mock_post.title = "How to Make Great Videos"
        self.mock_post.description = "Learn the secrets to creating engaging content"
        self.mock_post.content_text = "In this tutorial, we'll explore techniques for creating high-quality videos that engage your audience. We'll cover lighting, audio, editing, and storytelling."
        self.mock_post.hashtags = ["videotips", "contentcreation", "tutorial"]
        self.mock_post.platform = PlatformType.YOUTUBE
        self.mock_post.content_type = ContentType.VIDEO
        self.mock_post.publish_date = datetime.now(timezone.utc)
    
    @patch('analytics.nlp_analyzer.NLPService')
    def test_analyze_post(self, mock_nlp_service_class):
        """Test analyzing a post with NLP"""
        # Create a mock NLP result
        mock_nlp_result = NLPResult()
        mock_nlp_result.sentiment_score = 0.8
        mock_nlp_result.sentiment_label = "positive"
        mock_nlp_result.keywords = [{"keyword": "video", "relevance": 1.0}, {"keyword": "content", "relevance": 0.9}]
        mock_nlp_result.topics = [{"name": "video production", "keywords": ["video", "production"], "relevance": 1.0}]
        mock_nlp_result.word_count = 30
        mock_nlp_result.sentence_count = 2
        mock_nlp_result.readability_score = 75.0
        
        # Set up the mock NLP service
        mock_nlp_service = mock_nlp_service_class.return_value
        mock_nlp_service.analyze_post.return_value = mock_nlp_result
        
        # Replace the NLP service in the analyzer with our mock
        self.nlp_analyzer.nlp_service = mock_nlp_service
        
        # Call the analyze_post method
        result = self.nlp_analyzer.analyze_post(self.mock_post)
        
        # Verify the NLP service was called with the correct post data
        mock_nlp_service.analyze_post.assert_called_once()
        
        # Verify the result structure
        assert "sentiment" in result
        assert result["sentiment"]["label"] == "positive"
        assert "keywords" in result
        assert "topics" in result
        assert "text_stats" in result
    
    @patch('analytics.nlp_analyzer.NLPService')
    def test_extract_content_features(self, mock_nlp_service_class):
        """Test extracting content features"""
        # Set up the mock NLP result
        mock_nlp_result = {
            "sentiment": {"score": 0.8, "magnitude": 2.0, "label": "positive"},
            "keywords": [{"keyword": "video", "relevance": 1.0}, {"keyword": "content", "relevance": 0.9}],
            "topics": [{"name": "video production", "keywords": ["video", "production"], "relevance": 1.0}],
            "entities": [{"text": "#videotips", "type": "HASHTAG", "confidence": 0.9}],
            "text_stats": {
                "word_count": 30,
                "sentence_count": 2,
                "avg_word_length": 4.5,
                "avg_sentence_length": 15.0,
                "readability_score": 75.0
            }
        }
        
        # Set up the mock NLP service
        mock_nlp_service = mock_nlp_service_class.return_value
        mock_nlp_service.analyze_post.return_value = mock_nlp_result
        
        # Replace the NLP service in the analyzer
        self.nlp_analyzer.nlp_service = mock_nlp_service
        self.nlp_analyzer.analyze_post = MagicMock(return_value=mock_nlp_result)
        
        # Call the extract_content_features method
        features = self.nlp_analyzer.extract_content_features(self.mock_post)
        
        # Verify the features structure
        assert "sentiment" in features
        assert "readability_score" in features
        assert "keywords" in features
        assert "topics" in features
        assert "entities" in features
        assert "text_stats" in features
    
    def test_calculate_content_quality_score(self):
        """Test calculating content quality score"""
        # Test with a high-quality content
        high_quality = {
            "text_stats": {
                "word_count": 300,
                "sentence_count": 20,
                "readability_score": 80.0
            },
            "keywords": [{"keyword": "video", "relevance": 1.0}, {"keyword": "content", "relevance": 0.9}],
            "topics": [{"name": "video production", "keywords": ["video", "production"], "relevance": 1.0}],
            "sentiment": {"score": 0.8, "magnitude": 2.0, "label": "positive"}
        }
        
        high_score = self.nlp_analyzer.calculate_content_quality_score(high_quality)
        assert high_score > 60  # Should be a relatively high score
        
        # Test with a low-quality content
        low_quality = {
            "text_stats": {
                "word_count": 5,
                "sentence_count": 1,
                "readability_score": 30.0
            },
            "keywords": [],
            "topics": [],
            "sentiment": {"score": 0, "magnitude": 0.1, "label": "neutral"}
        }
        
        low_score = self.nlp_analyzer.calculate_content_quality_score(low_quality)
        assert low_score < 30  # Should be a relatively low score
    
    def test_get_sentiment_boost(self):
        """Test sentiment boost calculation"""
        # Test positive sentiment on YouTube
        youtube_positive = self.nlp_analyzer.get_sentiment_boost(0.8, "youtube")
        assert youtube_positive > 1.0  # Should boost performance
        
        # Test negative sentiment on YouTube
        youtube_negative = self.nlp_analyzer.get_sentiment_boost(-0.8, "youtube")
        assert youtube_negative < 1.0  # Should reduce performance
        
        # Test neutral sentiment
        neutral = self.nlp_analyzer.get_sentiment_boost(0, "youtube")
        assert neutral == 1.0  # Should not affect performance
        
        # Test different platforms
        instagram_positive = self.nlp_analyzer.get_sentiment_boost(0.8, "instagram")
        assert instagram_positive > 1.0
        
        # Test unknown platform
        unknown = self.nlp_analyzer.get_sentiment_boost(0.8, "unknown")
        assert unknown == 1.0  # Should default to no adjustment
    
    def test_identify_content_patterns(self):
        """Test identifying content patterns"""
        # Test with various content characteristics
        nlp_result = {
            "sentiment": {"score": 0.8, "magnitude": 2.0, "label": "positive"},
            "text_stats": {
                "word_count": 500,
                "sentence_count": 30,
                "readability_score": 85.0
            },
            "keywords": [
                {"keyword": "video", "relevance": 0.9},
                {"keyword": "content", "relevance": 0.8},
                {"keyword": "tutorial", "relevance": 0.7}
            ]
        }
        
        patterns = self.nlp_analyzer.identify_content_patterns(nlp_result)
        
        # Should identify several patterns
        assert len(patterns) > 0
        
        # Check for specific pattern types
        pattern_types = [p["type"] for p in patterns]
        assert "sentiment" in pattern_types
        assert "readability" in pattern_types
        assert "length" in pattern_types
