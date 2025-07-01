"""
NLP Service
Provides Natural Language Processing capabilities for analyzing text content
from social media posts, including sentiment analysis, entity recognition,
and topic modeling.
"""

import logging
from typing import Dict, List, Optional, Any, Union, Tuple
import re
from dataclasses import dataclass
import json
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class NLPResult:
    """Container for NLP analysis results"""
    # Sentiment analysis
    sentiment_score: float = 0.0  # -1.0 to 1.0 (negative to positive)
    sentiment_magnitude: float = 0.0  # 0.0 to +inf (strength of sentiment)
    sentiment_label: str = "neutral"  # negative, neutral, positive
    
    # Entity recognition
    entities: List[Dict[str, Any]] = None  # List of detected entities
    
    # Topic modeling
    topics: List[Dict[str, Any]] = None  # List of detected topics
    
    # Keyword extraction
    keywords: List[Dict[str, str]] = None  # List of keywords with relevance scores
    
    # Text statistics
    word_count: int = 0
    sentence_count: int = 0
    avg_word_length: float = 0.0
    avg_sentence_length: float = 0.0
    
    # Readability metrics
    readability_score: float = 0.0  # 0-100 scale
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = []
        if self.topics is None:
            self.topics = []
        if self.keywords is None:
            self.keywords = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert NLP result to dictionary"""
        return {
            "sentiment": {
                "score": self.sentiment_score,
                "magnitude": self.sentiment_magnitude,
                "label": self.sentiment_label
            },
            "entities": self.entities,
            "topics": self.topics,
            "keywords": self.keywords,
            "text_stats": {
                "word_count": self.word_count,
                "sentence_count": self.sentence_count,
                "avg_word_length": self.avg_word_length,
                "avg_sentence_length": self.avg_sentence_length,
                "readability_score": self.readability_score
            }
        }


class NLPService:
    """Service for text analysis using NLP techniques"""
    
    def __init__(self):
        """Initialize NLP service with basic text processing capabilities"""
        # Initialize basic NLP components
        self.stop_words = self._load_stop_words()
        
        # Initialize sentiment analysis components
        self.positive_words = self._load_lexicon("positive")
        self.negative_words = self._load_lexicon("negative")
        
        logger.info("NLP Service initialized with basic text processing capabilities")
    
    def analyze_text(self, text: str) -> NLPResult:
        """
        Analyze text content using NLP techniques
        
        Args:
            text: Text content to analyze
            
        Returns:
            NLPResult: Container with analysis results
        """
        if not text or not isinstance(text, str):
            logger.warning("Invalid text provided for NLP analysis")
            return NLPResult()
        
        # Preprocess text
        clean_text = self._preprocess_text(text)
        
        # Create result container
        result = NLPResult()
        
        # Perform text statistics analysis
        self._analyze_text_statistics(clean_text, result)
        
        # Perform sentiment analysis
        self._analyze_sentiment(clean_text, result)
        
        # Extract keywords
        self._extract_keywords(clean_text, result)
        
        # Extract entities (simple implementation)
        self._extract_entities(clean_text, result)
        
        # Identify topics (simple implementation)
        self._identify_topics(clean_text, result)
        
        logger.info(f"Completed NLP analysis: sentiment={result.sentiment_label}, "
                   f"entities={len(result.entities)}, keywords={len(result.keywords)}")
        
        return result
    
    def analyze_post(self, post_data: Dict[str, Any]) -> NLPResult:
        """
        Analyze a post's text content from various fields
        
        Args:
            post_data: Dictionary containing post data with text fields
            
        Returns:
            NLPResult: Container with analysis results
        """
        # Combine relevant text fields with appropriate weighting
        combined_text = ""
        
        # Add title with more weight (repeat it)
        if "title" in post_data and post_data["title"]:
            combined_text += f"{post_data['title']} {post_data['title']} "
        
        # Add description
        if "description" in post_data and post_data["description"]:
            combined_text += f"{post_data['description']} "
        
        # Add content text
        if "content_text" in post_data and post_data["content_text"]:
            combined_text += f"{post_data['content_text']} "
        
        # Add hashtags
        if "hashtags" in post_data and post_data["hashtags"]:
            if isinstance(post_data["hashtags"], list):
                combined_text += " ".join(post_data["hashtags"]) + " "
            elif isinstance(post_data["hashtags"], str):
                combined_text += post_data["hashtags"] + " "
        
        if not combined_text.strip():
            logger.warning("No text content found in post data for NLP analysis")
            return NLPResult()
        
        return self.analyze_text(combined_text)
    
    def _preprocess_text(self, text: str) -> str:
        """
        Clean and normalize text for analysis
        
        Args:
            text: Raw text input
            
        Returns:
            str: Preprocessed text
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        
        # Remove special characters but keep spaces and basic punctuation for sentence detection
        text = re.sub(r'[^\w\s.,!?]', ' ', text)
        
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _analyze_text_statistics(self, text: str, result: NLPResult) -> None:
        """
        Calculate basic text statistics
        
        Args:
            text: Preprocessed text
            result: NLPResult object to update
        """
        # Count words (excluding stop words for more meaningful count)
        words = [w for w in text.split() if w.lower() not in self.stop_words]
        result.word_count = len(words)
        
        # Count sentences (simple approach)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        result.sentence_count = len(sentences)
        
        # Calculate average word length
        if result.word_count > 0:
            result.avg_word_length = sum(len(word) for word in words) / result.word_count
        
        # Calculate average sentence length
        if result.sentence_count > 0:
            result.avg_sentence_length = result.word_count / result.sentence_count
        
        # Calculate simple readability score (0-100)
        # Based on simplified Flesch Reading Ease
        if result.sentence_count > 0 and result.word_count > 0:
            # Higher score = easier to read
            result.readability_score = max(0, min(100, 
                206.835 - 1.015 * (result.word_count / result.sentence_count) 
                - 84.6 * (sum(len(word) for word in words) / result.word_count / 3)
            ))
    
    def _analyze_sentiment(self, text: str, result: NLPResult) -> None:
        """
        Perform basic sentiment analysis
        
        Args:
            text: Preprocessed text
            result: NLPResult object to update
        """
        words = text.split()
        
        # Count positive and negative words
        positive_count = sum(1 for word in words if word in self.positive_words)
        negative_count = sum(1 for word in words if word in self.negative_words)
        
        # Calculate sentiment score (-1 to 1)
        total_count = positive_count + negative_count
        if total_count > 0:
            result.sentiment_score = (positive_count - negative_count) / total_count
        else:
            result.sentiment_score = 0.0
        
        # Calculate sentiment magnitude (0 to +inf)
        result.sentiment_magnitude = total_count / max(1, len(words)) * 10
        
        # Determine sentiment label
        if result.sentiment_score > 0.1:
            result.sentiment_label = "positive"
        elif result.sentiment_score < -0.1:
            result.sentiment_label = "negative"
        else:
            result.sentiment_label = "neutral"
    
    def _extract_keywords(self, text: str, result: NLPResult) -> None:
        """
        Extract important keywords from text
        
        Args:
            text: Preprocessed text
            result: NLPResult object to update
        """
        words = text.split()
        
        # Filter out stop words
        filtered_words = [word for word in words if word.lower() not in self.stop_words]
        
        # Count word frequencies
        word_freq = {}
        for word in filtered_words:
            if len(word) > 2:  # Only consider words with more than 2 characters
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        # Take top keywords
        top_keywords = sorted_words[:10]
        
        # Calculate relevance score (0-1)
        max_freq = max([freq for _, freq in top_keywords]) if top_keywords else 1
        
        # Format keywords with relevance scores
        result.keywords = [
            {"keyword": word, "relevance": freq / max_freq}
            for word, freq in top_keywords
        ]
    
    def _extract_entities(self, text: str, result: NLPResult) -> None:
        """
        Extract named entities from text (simplified version)
        
        Args:
            text: Preprocessed text
            result: NLPResult object to update
        """
        # This is a simplified placeholder implementation
        # In a real implementation, this would use a proper NER model
        
        # Simple pattern matching for some entity types
        # Email pattern
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        for email in emails:
            result.entities.append({
                "text": email,
                "type": "EMAIL",
                "confidence": 0.9
            })
        
        # URL pattern (simplified)
        urls = re.findall(r'https?://\S+|www\.\S+', text)
        for url in urls:
            result.entities.append({
                "text": url,
                "type": "URL",
                "confidence": 0.9
            })
        
        # Hashtag pattern
        hashtags = re.findall(r'#\w+', text)
        for hashtag in hashtags:
            result.entities.append({
                "text": hashtag,
                "type": "HASHTAG",
                "confidence": 0.9
            })
        
        # Mention pattern
        mentions = re.findall(r'@\w+', text)
        for mention in mentions:
            result.entities.append({
                "text": mention,
                "type": "MENTION",
                "confidence": 0.9
            })
    
    def _identify_topics(self, text: str, result: NLPResult) -> None:
        """
        Identify topics in text (simplified version)
        
        Args:
            text: Preprocessed text
            result: NLPResult object to update
        """
        # This is a simplified placeholder implementation
        # In a real implementation, this would use topic modeling (LDA, etc.)
        
        # Use keyword clusters as simple topics
        if result.keywords:
            # Group similar keywords (simplified)
            topics = []
            used_keywords = set()
            
            for keyword_data in result.keywords:
                keyword = keyword_data["keyword"]
                if keyword in used_keywords:
                    continue
                
                # Find related keywords
                related_keywords = []
                for other_data in result.keywords:
                    other_keyword = other_data["keyword"]
                    if other_keyword not in used_keywords and (
                        other_keyword.startswith(keyword) or 
                        keyword.startswith(other_keyword) or
                        self._calculate_similarity(keyword, other_keyword) > 0.7
                    ):
                        related_keywords.append(other_keyword)
                        used_keywords.add(other_keyword)
                
                if related_keywords:
                    topics.append({
                        "name": keyword,
                        "keywords": related_keywords,
                        "relevance": keyword_data["relevance"]
                    })
                    
                    # Limit to top 5 topics
                    if len(topics) >= 5:
                        break
            
            result.topics = topics
    
    def _calculate_similarity(self, word1: str, word2: str) -> float:
        """
        Calculate simple string similarity (Jaccard similarity)
        
        Args:
            word1: First word
            word2: Second word
            
        Returns:
            float: Similarity score (0-1)
        """
        # Convert to sets of characters
        set1 = set(word1)
        set2 = set(word2)
        
        # Calculate Jaccard similarity
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        if union == 0:
            return 0
        
        return intersection / union
    
    def _load_stop_words(self) -> set:
        """
        Load common English stop words
        
        Returns:
            set: Set of stop words
        """
        # Basic English stop words
        return {
            "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", 
            "while", "of", "at", "by", "for", "with", "about", "against", "between",
            "into", "through", "during", "before", "after", "above", "below", "to",
            "from", "up", "down", "in", "out", "on", "off", "over", "under", "again",
            "further", "then", "once", "here", "there", "when", "where", "why", "how",
            "all", "any", "both", "each", "few", "more", "most", "other", "some", "such",
            "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s",
            "t", "can", "will", "just", "don", "don't", "should", "should've", "now", "d",
            "ll", "m", "o", "re", "ve", "y", "ain", "aren", "aren't", "couldn", "couldn't",
            "didn", "didn't", "doesn", "doesn't", "hadn", "hadn't", "hasn", "hasn't", 
            "haven", "haven't", "isn", "isn't", "ma", "mightn", "mightn't", "mustn",
            "mustn't", "needn", "needn't", "shan", "shan't", "shouldn", "shouldn't", 
            "wasn", "wasn't", "weren", "weren't", "won", "won't", "wouldn", "wouldn't",
            "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your",
            "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", 
            "her", "hers", "herself", "it", "its", "itself", "they", "them", "their",
            "theirs", "themselves", "what", "which", "who", "whom", "this", "that", 
            "these", "those", "am", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "having", "do", "does", "did", "doing"
        }
    
    def _load_lexicon(self, sentiment_type: str) -> set:
        """
        Load sentiment lexicon (positive or negative words)
        
        Args:
            sentiment_type: Type of lexicon ("positive" or "negative")
            
        Returns:
            set: Set of words with the specified sentiment
        """
        if sentiment_type == "positive":
            return {
                "good", "great", "excellent", "amazing", "awesome", "fantastic", 
                "wonderful", "brilliant", "outstanding", "superb", "perfect", "best",
                "love", "happy", "joy", "excited", "beautiful", "impressive", "incredible",
                "enjoy", "liked", "favorite", "positive", "success", "successful", "win",
                "winner", "beneficial", "better", "helpful", "recommend", "recommended",
                "worth", "valuable", "nice", "pleased", "satisfying", "satisfied", 
                "impressive", "innovative", "easy", "useful", "effective", "efficient",
                "quality", "exceptional", "delightful", "pleasant", "superior", "terrific",
                "thrilled", "grateful", "thankful", "appreciate", "appreciated", "praise",
                "congratulations", "congrats", "proud", "inspiring", "inspired", "inspiring",
                "favorite", "fabulous", "fantastic", "remarkable", "sensational", "stunning",
                "extraordinary", "marvelous", "magnificent", "glorious", "splendid", "super"
            }
        elif sentiment_type == "negative":
            return {
                "bad", "terrible", "awful", "horrible", "poor", "disappointing", "worst",
                "hate", "dislike", "disappointed", "sad", "angry", "upset", "annoyed",
                "annoying", "frustrating", "frustrated", "useless", "waste", "problem",
                "difficult", "hard", "complicated", "confusing", "confused", "issue",
                "issues", "bug", "bugs", "error", "errors", "fail", "failed", "failure",
                "negative", "terrible", "horrible", "awful", "mediocre", "subpar", "inferior",
                "unacceptable", "inadequate", "defective", "deficient", "flawed", "broken",
                "unreliable", "ineffective", "inefficient", "overpriced", "expensive",
                "costly", "cheap", "worthless", "regret", "regretful", "sorry", "apology",
                "complaint", "complaining", "unhappy", "dissatisfied", "unsatisfied",
                "unfortunate", "unfortunate", "unpleasant", "unfair", "wrong", "trouble",
                "problematic", "disaster", "catastrophe", "terrible", "dreadful", "appalling",
                "atrocious", "abysmal", "pathetic", "lousy", "unacceptable", "intolerable"
            }
        else:
            return set()
