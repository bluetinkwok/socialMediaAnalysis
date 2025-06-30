"""
AWS Content Filter Adapter

This module provides an adapter for AWS services to filter inappropriate content.
It uses AWS Rekognition for image analysis and AWS Comprehend for text analysis.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Tuple
import boto3
from botocore.exceptions import ClientError

from .base_adapter import ContentFilterAdapter, FilterResult, ContentCategory, SeverityLevel

# Configure logging
logger = logging.getLogger(__name__)

class AWSContentFilterAdapter(ContentFilterAdapter):
    """
    AWS Content Filter Adapter
    
    Uses AWS Rekognition for image analysis and AWS Comprehend for text analysis.
    Maps AWS categories to internal categories and determines severity levels.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the AWS content filter adapter.
        
        Args:
            config: Configuration options for the adapter
        """
        super().__init__()
        self.config = config or {}
        self.rekognition_client = None
        self.comprehend_client = None
        self.initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize the adapter by setting up AWS clients.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            logger.info("Initializing AWS content filter adapter")
            
            # Get AWS credentials from config or environment variables
            aws_access_key = self.config.get('aws_access_key_id') or os.environ.get('AWS_ACCESS_KEY_ID')
            aws_secret_key = self.config.get('aws_secret_access_key') or os.environ.get('AWS_SECRET_ACCESS_KEY')
            aws_region = self.config.get('aws_region') or os.environ.get('AWS_REGION', 'us-east-1')
            
            # Check if credentials are available
            if not aws_access_key or not aws_secret_key:
                logger.warning("AWS credentials not provided")
                return False
            
            # Initialize AWS clients
            session = boto3.Session(
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )
            
            self.rekognition_client = session.client('rekognition')
            self.comprehend_client = session.client('comprehend')
            
            # Set confidence thresholds from config or use defaults
            self.min_confidence = self.config.get('min_confidence', 50.0)
            self.severity_thresholds = self.config.get('severity_thresholds', {
                'low': 50.0,
                'medium': 70.0,
                'high': 85.0
            })
            
            self.initialized = True
            logger.info("AWS content filter adapter initialized")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing AWS content filter adapter: {str(e)}")
            return False
    
    def filter_image(self, image_path: str) -> FilterResult:
        """
        Filter an image using AWS Rekognition.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            FilterResult: Results of the content filtering
        """
        if not self.initialized:
            logger.warning("AWS content filter adapter not initialized")
            return FilterResult(is_appropriate=True, categories={})
        
        try:
            # Read image file
            with open(image_path, 'rb') as image_file:
                image_bytes = image_file.read()
            
            # Detect moderation labels using Rekognition
            response = self.rekognition_client.detect_moderation_labels(
                Image={'Bytes': image_bytes},
                MinConfidence=self.min_confidence
            )
            
            # Process moderation labels
            moderation_labels = response.get('ModerationLabels', [])
            
            # Map AWS categories to internal categories
            categories = {}
            detected_categories = set()
            
            for label in moderation_labels:
                name = label.get('Name', '')
                parent_name = label.get('ParentName', '')
                confidence = label.get('Confidence', 0.0)
                
                # Map AWS category to internal category
                internal_category = self._map_aws_image_category_to_internal(name, parent_name)
                
                if internal_category:
                    detected_categories.add(internal_category)
                    
                    # Determine severity based on confidence
                    severity = self._confidence_to_severity(confidence)
                    
                    # Update category data
                    if internal_category not in categories or self._severity_value(severity) > self._severity_value(categories[internal_category]['severity']):
                        categories[internal_category] = {
                            'severity': severity,
                            'confidence': confidence,
                            'details': {
                                'aws_label': name,
                                'aws_parent_label': parent_name
                            }
                        }
            
            # Determine if the image is appropriate
            is_appropriate = len(detected_categories) == 0
            
            return FilterResult(
                is_appropriate=is_appropriate,
                categories=categories,
                service_specific_data={
                    'aws_moderation_labels': moderation_labels
                }
            )
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"AWS Rekognition error ({error_code}): {error_message}")
            
            return FilterResult(
                is_appropriate=True,  # Default to allowing content on error
                categories={},
                error=f"AWS Rekognition error: {error_message}"
            )
            
        except Exception as e:
            logger.error(f"Error filtering image with AWS Rekognition: {str(e)}")
            
            return FilterResult(
                is_appropriate=True,  # Default to allowing content on error
                categories={},
                error=f"Error filtering image: {str(e)}"
            )
    
    def filter_text(self, text: str) -> FilterResult:
        """
        Filter text using AWS Comprehend.
        
        Args:
            text: Text to filter
            
        Returns:
            FilterResult: Results of the content filtering
        """
        if not self.initialized:
            logger.warning("AWS content filter adapter not initialized")
            return FilterResult(is_appropriate=True, categories={})
        
        try:
            # Detect potentially harmful content using Comprehend
            categories = {}
            
            # Detect sentiment
            sentiment_response = self.comprehend_client.detect_sentiment(
                Text=text,
                LanguageCode='en'
            )
            
            sentiment = sentiment_response.get('Sentiment', '')
            sentiment_scores = sentiment_response.get('SentimentScore', {})
            
            # Check for negative sentiment
            if sentiment == 'NEGATIVE' and sentiment_scores.get('Negative', 0) > 0.7:
                categories[ContentCategory.POTENTIALLY_HARMFUL] = {
                    'severity': SeverityLevel.LOW,
                    'confidence': sentiment_scores.get('Negative', 0) * 100,
                    'details': {
                        'aws_sentiment': sentiment,
                        'aws_sentiment_scores': sentiment_scores
                    }
                }
            
            # Detect PII (Personally Identifiable Information)
            pii_response = self.comprehend_client.detect_pii_entities(
                Text=text,
                LanguageCode='en'
            )
            
            pii_entities = pii_response.get('Entities', [])
            
            # Check for PII
            if pii_entities:
                pii_types = [entity.get('Type') for entity in pii_entities]
                sensitive_pii_types = ['SSN', 'CREDIT_DEBIT_NUMBER', 'BANK_ACCOUNT_NUMBER', 'PASSWORD']
                
                # Check if sensitive PII is present
                sensitive_pii_found = any(pii_type in sensitive_pii_types for pii_type in pii_types)
                
                if sensitive_pii_found:
                    categories[ContentCategory.PRIVACY_RISK] = {
                        'severity': SeverityLevel.MEDIUM,
                        'confidence': 90.0,
                        'details': {
                            'aws_pii_entities': pii_types
                        }
                    }
            
            # Detect key phrases for context
            key_phrases_response = self.comprehend_client.detect_key_phrases(
                Text=text,
                LanguageCode='en'
            )
            
            key_phrases = [phrase.get('Text') for phrase in key_phrases_response.get('KeyPhrases', [])]
            
            # Check for toxic content using key phrases
            toxic_phrases = self._detect_toxic_content(text, key_phrases)
            
            if toxic_phrases:
                # Determine category and severity based on toxic phrases
                category, severity = self._categorize_toxic_phrases(toxic_phrases)
                
                if category:
                    categories[category] = {
                        'severity': severity,
                        'confidence': 75.0,
                        'details': {
                            'toxic_phrases': toxic_phrases
                        }
                    }
            
            # Determine if the text is appropriate
            is_appropriate = len(categories) == 0
            
            return FilterResult(
                is_appropriate=is_appropriate,
                categories=categories,
                service_specific_data={
                    'aws_sentiment': sentiment_response,
                    'aws_pii_entities': pii_entities,
                    'aws_key_phrases': key_phrases
                }
            )
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"AWS Comprehend error ({error_code}): {error_message}")
            
            return FilterResult(
                is_appropriate=True,  # Default to allowing content on error
                categories={},
                error=f"AWS Comprehend error: {error_message}"
            )
            
        except Exception as e:
            logger.error(f"Error filtering text with AWS Comprehend: {str(e)}")
            
            return FilterResult(
                is_appropriate=True,  # Default to allowing content on error
                categories={},
                error=f"Error filtering text: {str(e)}"
            )
    
    def _map_aws_image_category_to_internal(self, label: str, parent_label: str = None) -> Optional[str]:
        """
        Map AWS Rekognition moderation label to internal content category.
        
        Args:
            label: AWS moderation label
            parent_label: Parent label (if available)
            
        Returns:
            Optional[str]: Internal content category or None if no mapping
        """
        # Use parent label if available, otherwise use label
        category_name = parent_label or label
        category_name = category_name.lower()
        
        # Map AWS categories to internal categories
        if any(term in category_name for term in ['explicit nudity', 'nudity', 'graphic male nudity', 'graphic female nudity', 'sexual activity']):
            return ContentCategory.ADULT
        elif any(term in category_name for term in ['violence', 'graphic violence', 'physical violence', 'weapon violence', 'weapons']):
            return ContentCategory.VIOLENCE
        elif any(term in category_name for term in ['hate symbols', 'nazi', 'white supremacy', 'extremist']):
            return ContentCategory.HATE_SPEECH
        elif any(term in category_name for term in ['drugs', 'drug products', 'drug use', 'pills', 'drug paraphernalia']):
            return ContentCategory.DRUGS
        elif any(term in category_name for term in ['tobacco', 'smoking', 'alcohol', 'drinking']):
            return ContentCategory.DRUGS  # Map to drugs category
        elif any(term in category_name for term in ['rude gestures', 'middle finger']):
            return ContentCategory.POTENTIALLY_HARMFUL
        
        # If no specific mapping, return None
        return None
    
    def _confidence_to_severity(self, confidence: float) -> str:
        """
        Convert AWS confidence score to internal severity level.
        
        Args:
            confidence: AWS confidence score (0-100)
            
        Returns:
            str: Internal severity level
        """
        if confidence >= self.severity_thresholds['high']:
            return SeverityLevel.HIGH
        elif confidence >= self.severity_thresholds['medium']:
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.LOW
    
    def _severity_value(self, severity: str) -> int:
        """
        Convert severity level to numeric value for comparison.
        
        Args:
            severity: Severity level
            
        Returns:
            int: Numeric value (higher means more severe)
        """
        severity_values = {
            SeverityLevel.LOW: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.HIGH: 3
        }
        
        return severity_values.get(severity, 0)
    
    def _detect_toxic_content(self, text: str, key_phrases: List[str]) -> List[str]:
        """
        Detect potentially toxic content in text using key phrases.
        
        Args:
            text: Text to analyze
            key_phrases: Key phrases extracted from the text
            
        Returns:
            List[str]: List of detected toxic phrases
        """
        # This is a simplified implementation
        # In a real-world scenario, you might use a more sophisticated approach
        # such as a dedicated toxic content detection service or a comprehensive word list
        
        toxic_phrases = []
        
        # Check for common toxic phrases
        toxic_indicators = {
            ContentCategory.HATE_SPEECH: [
                'hate', 'racist', 'bigot', 'nazi', 'white power', 'supremacy',
                'kill all', 'death to', 'exterminate'
            ],
            ContentCategory.SELF_HARM: [
                'suicide', 'kill myself', 'end my life', 'self-harm', 'cut myself',
                'don\'t want to live', 'want to die'
            ],
            ContentCategory.VIOLENCE: [
                'murder', 'kill', 'attack', 'shoot', 'bomb', 'terrorist', 'massacre',
                'assassinate', 'slaughter'
            ],
            ContentCategory.ADULT: [
                'porn', 'xxx', 'sex video', 'explicit content'
            ]
        }
        
        # Check text for toxic phrases
        text_lower = text.lower()
        for category, indicators in toxic_indicators.items():
            for indicator in indicators:
                if indicator in text_lower:
                    toxic_phrases.append({
                        'phrase': indicator,
                        'category': category
                    })
        
        return toxic_phrases
    
    def _categorize_toxic_phrases(self, toxic_phrases: List[Dict[str, Any]]) -> Tuple[Optional[str], str]:
        """
        Determine the most severe category and severity level from toxic phrases.
        
        Args:
            toxic_phrases: List of toxic phrases with categories
            
        Returns:
            Tuple[Optional[str], str]: (category, severity_level) or (None, '')
        """
        if not toxic_phrases:
            return None, ''
        
        # Count occurrences of each category
        category_counts = {}
        for phrase in toxic_phrases:
            category = phrase.get('category')
            if category:
                category_counts[category] = category_counts.get(category, 0) + 1
        
        # Determine the most frequent category
        most_frequent_category = max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else None
        
        # Determine severity based on count
        count = category_counts.get(most_frequent_category, 0)
        if count >= 5:
            severity = SeverityLevel.HIGH
        elif count >= 2:
            severity = SeverityLevel.MEDIUM
        else:
            severity = SeverityLevel.LOW
        
        return most_frequent_category, severity 