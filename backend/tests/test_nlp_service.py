"""
Tests for NLP Service
"""

import pytest
import json
from services.nlp_service import NLPService, NLPResult


class TestNLPService:
    """Test suite for NLP Service"""
    
    def setup_method(self):
        """Set up test environment before each test method"""
        self.nlp_service = NLPService()
        
        # Sample text for testing
        self.positive_text = "This is an amazing video! I really loved the content and found it incredibly helpful. The quality is excellent and I would highly recommend it to everyone."
        self.negative_text = "This video was terrible. I hated the content and found it completely useless. The quality is poor and I would not recommend it to anyone."
        self.neutral_text = "This is a video about programming. It shows how to write code and explains some concepts. It has examples and demonstrations."
        
        # Sample post data for testing
        self.sample_post = {
            "title": "How to Build a Web App",
            "description": "Learn to create a web application using modern frameworks",
            "content_text": "In this tutorial, we'll explore how to build a web application from scratch using React and Node.js. We'll cover component design, state management, and API integration.",
            "hashtags": ["webdev", "javascript", "react", "tutorial"]
        }
    
    def test_nlp_service_initialization(self):
        """Test NLP service initialization"""
        assert self.nlp_service is not None
        assert isinstance(self.nlp_service.stop_words, set)
        assert len(self.nlp_service.stop_words) > 0
        assert isinstance(self.nlp_service.positive_words, set)
        assert len(self.nlp_service.positive_words) > 0
        assert isinstance(self.nlp_service.negative_words, set)
        assert len(self.nlp_service.negative_words) > 0
    
    def test_text_preprocessing(self):
        """Test text preprocessing functionality"""
        text = "Check out this AMAZING website: https://example.com! It's really cool. #webdev @johndoe"
        processed = self.nlp_service._preprocess_text(text)
        
        assert "https://example.com" not in processed
        assert processed == "check out this amazing website  its really cool  webdev  johndoe"
    
    def test_sentiment_analysis_positive(self):
        """Test sentiment analysis on positive text"""
        result = self.nlp_service.analyze_text(self.positive_text)
        
        assert result.sentiment_score > 0
        assert result.sentiment_label == "positive"
        assert result.sentiment_magnitude > 0
    
    def test_sentiment_analysis_negative(self):
        """Test sentiment analysis on negative text"""
        result = self.nlp_service.analyze_text(self.negative_text)
        
        assert result.sentiment_score < 0
        assert result.sentiment_label == "negative"
        assert result.sentiment_magnitude > 0
    
    def test_sentiment_analysis_neutral(self):
        """Test sentiment analysis on neutral text"""
        result = self.nlp_service.analyze_text(self.neutral_text)
        
        assert -0.2 < result.sentiment_score < 0.2
        assert result.sentiment_magnitude >= 0
    
    def test_keyword_extraction(self):
        """Test keyword extraction functionality"""
        result = self.nlp_service.analyze_text(self.sample_post["content_text"])
        
        assert len(result.keywords) > 0
        # Check that keywords are relevant to the content
        keywords = [k["keyword"] for k in result.keywords]
        assert any(k in ["web", "application", "react", "node", "build", "tutorial"] for k in keywords)
    
    def test_entity_extraction(self):
        """Test entity extraction functionality"""
        text = "Contact us at info@example.com or visit https://example.com. #webdev @johndoe"
        result = self.nlp_service.analyze_text(text)
        
        assert len(result.entities) > 0
        entity_types = [e["type"] for e in result.entities]
        entity_texts = [e["text"] for e in result.entities]
        
        assert "EMAIL" in entity_types
        assert "info@example.com" in entity_texts
        assert "HASHTAG" in entity_types
        assert "#webdev" in entity_texts
        assert "MENTION" in entity_types
        assert "@johndoe" in entity_texts
    
    def test_topic_identification(self):
        """Test topic identification functionality"""
        # Use a longer text with clear topics
        tech_text = "Python is a programming language. It's used for web development, data science, and machine learning. Many developers prefer Python for its simplicity and readability. Python has libraries like TensorFlow and PyTorch for AI development."
        result = self.nlp_service.analyze_text(tech_text)
        
        assert len(result.topics) > 0
        topic_names = [t["name"] for t in result.topics]
        # Check that at least one relevant topic is identified
        assert any(t in ["python", "programming", "development", "language", "data", "machine"] for t in topic_names)
    
    def test_text_statistics(self):
        """Test text statistics calculation"""
        result = self.nlp_service.analyze_text(self.sample_post["content_text"])
        
        assert result.word_count > 0
        assert result.sentence_count > 0
        assert result.avg_word_length > 0
        assert result.avg_sentence_length > 0
        assert 0 <= result.readability_score <= 100
    
    def test_analyze_post(self):
        """Test analyzing a complete post"""
        result = self.nlp_service.analyze_post(self.sample_post)
        
        assert result is not None
        assert result.sentiment_label in ["positive", "negative", "neutral"]
        assert len(result.keywords) > 0
        assert result.word_count > 0
        
        # Convert to dict and check structure
        result_dict = result.to_dict()
        assert "sentiment" in result_dict
        assert "keywords" in result_dict
        assert "topics" in result_dict
        assert "text_stats" in result_dict
    
    def test_empty_input(self):
        """Test handling of empty input"""
        result = self.nlp_service.analyze_text("")
        assert result.word_count == 0
        assert result.sentiment_label == "neutral"
        
        result = self.nlp_service.analyze_post({})
        assert result.word_count == 0
        assert result.sentiment_label == "neutral"
    
    def test_similarity_calculation(self):
        """Test word similarity calculation"""
        similarity = self.nlp_service._calculate_similarity("python", "python")
        assert similarity == 1.0
        
        similarity = self.nlp_service._calculate_similarity("python", "javascript")
        assert 0 <= similarity < 0.5
        
        similarity = self.nlp_service._calculate_similarity("programming", "program")
        assert similarity > 0.5
