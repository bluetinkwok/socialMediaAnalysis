"""
Google Content Filter Adapter

This module provides an adapter for Google Cloud services to filter inappropriate content.
It uses Google Cloud Vision for image analysis and Google Cloud Natural Language for text analysis.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Tuple
import base64

from google.cloud import vision
from google.cloud import language_v1
from google.cloud.vision_v1 import types as vision_types
from google.api_core.exceptions import GoogleAPIError

from .base_adapter import ContentFilterAdapter, FilterResult, ContentCategory, SeverityLevel

# Configure logging
logger = logging.getLogger(__name__)

class GoogleContentFilterAdapter(ContentFilterAdapter):
    """
    Google Content Filter Adapter
    
    Uses Google Cloud Vision for image analysis and Google Cloud Natural Language for text analysis.
    Maps Google categories to internal categories and determines severity levels.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the Google content filter adapter.
        
        Args:
            config: Configuration options for the adapter
        """
        super().__init__()
        self.config = config or {}
        self.vision_client = None
        self.language_client = None
        self.initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize the adapter by setting up Google Cloud clients.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            logger.info("Initializing Google content filter adapter")
            
            # Check for credentials
            credentials_path = self.config.get('credentials_path') or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            
            if not credentials_path and not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
                logger.warning("Google Cloud credentials not provided")
                return False
            
            # Set credentials if provided in config
            if credentials_path:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
            
            # Initialize Google Cloud clients
            self.vision_client = vision.ImageAnnotatorClient()
            self.language_client = language_v1.LanguageServiceClient()
            
            # Set likelihood thresholds from config or use defaults
            # Google uses LIKELIHOOD values: UNKNOWN, VERY_UNLIKELY, UNLIKELY, POSSIBLE, LIKELY, VERY_LIKELY
            self.likelihood_map = {
                'UNKNOWN': 0,
                'VERY_UNLIKELY': 10,
                'UNLIKELY': 30,
                'POSSIBLE': 50,
                'LIKELY': 75,
                'VERY_LIKELY': 90
            }
            
            # Map likelihood to severity
            self.likelihood_to_severity = {
                'UNKNOWN': SeverityLevel.LOW,
                'VERY_UNLIKELY': SeverityLevel.LOW,
                'UNLIKELY': SeverityLevel.LOW,
                'POSSIBLE': SeverityLevel.MEDIUM,
                'LIKELY': SeverityLevel.MEDIUM,
                'VERY_LIKELY': SeverityLevel.HIGH
            }
            
            self.initialized = True
            logger.info("Google content filter adapter initialized")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Google content filter adapter: {str(e)}")
            return False
    
    def filter_image(self, image_path: str) -> FilterResult:
        """
        Filter an image using Google Cloud Vision.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            FilterResult: Results of the content filtering
        """
        if not self.initialized:
            logger.warning("Google content filter adapter not initialized")
            return FilterResult(is_appropriate=True, categories={})
        
        try:
            # Read image file
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            # Create image object
            image = vision_types.Image(content=content)
            
            # Perform safe search detection
            response = self.vision_client.safe_search_detection(image=image)
            safe_search = response.safe_search_annotation
            
            # Process safe search results
            categories = {}
            
            # Map Google safe search categories to internal categories
            category_mapping = {
                'adult': ContentCategory.ADULT,
                'violence': ContentCategory.VIOLENCE,
                'medical': ContentCategory.POTENTIALLY_HARMFUL,
                'spoof': ContentCategory.SPAM,
                'racy': ContentCategory.ADULT  # Map 'racy' to ADULT category
            }
            
            # Check each category
            for google_category, likelihood in {
                'adult': safe_search.adult,
                'violence': safe_search.violence,
                'medical': safe_search.medical,
                'spoof': safe_search.spoof,
                'racy': safe_search.racy
            }.items():
                # Get likelihood name
                likelihood_name = vision.Likelihood(likelihood).name
                
                # Skip if very unlikely
                if likelihood_name in ['UNKNOWN', 'VERY_UNLIKELY']:
                    continue
                
                # Map to internal category
                internal_category = category_mapping.get(google_category)
                
                if internal_category:
                    # Determine severity based on likelihood
                    severity = self.likelihood_to_severity.get(likelihood_name, SeverityLevel.LOW)
                    
                    # Convert likelihood to confidence score (0-100)
                    confidence = self.likelihood_map.get(likelihood_name, 0)
                    
                    # Add to categories
                    categories[internal_category] = {
                        'severity': severity,
                        'confidence': confidence,
                        'details': {
                            'google_category': google_category,
                            'google_likelihood': likelihood_name
                        }
                    }
            
            # Determine if the image is appropriate
            is_appropriate = len(categories) == 0
            
            # Perform label detection for additional context
            label_response = self.vision_client.label_detection(image=image)
            labels = label_response.label_annotations
            
            # Extract top labels
            top_labels = [{'description': label.description, 'score': label.score} 
                         for label in labels[:10]]  # Limit to top 10 labels
            
            return FilterResult(
                is_appropriate=is_appropriate,
                categories=categories,
                service_specific_data={
                    'google_safe_search': {
                        'adult': vision.Likelihood(safe_search.adult).name,
                        'violence': vision.Likelihood(safe_search.violence).name,
                        'medical': vision.Likelihood(safe_search.medical).name,
                        'spoof': vision.Likelihood(safe_search.spoof).name,
                        'racy': vision.Likelihood(safe_search.racy).name
                    },
                    'google_labels': top_labels
                }
            )
            
        except GoogleAPIError as e:
            logger.error(f"Google Cloud Vision error: {str(e)}")
            
            return FilterResult(
                is_appropriate=True,  # Default to allowing content on error
                categories={},
                error=f"Google Cloud Vision error: {str(e)}"
            )
            
        except Exception as e:
            logger.error(f"Error filtering image with Google Cloud Vision: {str(e)}")
            
            return FilterResult(
                is_appropriate=True,  # Default to allowing content on error
                categories={},
                error=f"Error filtering image: {str(e)}"
            )
    
    def filter_text(self, text: str) -> FilterResult:
        """
        Filter text using Google Cloud Natural Language.
        
        Args:
            text: Text to filter
            
        Returns:
            FilterResult: Results of the content filtering
        """
        if not self.initialized:
            logger.warning("Google content filter adapter not initialized")
            return FilterResult(is_appropriate=True, categories={})
        
        try:
            # Create document object
            document = language_v1.Document(
                content=text,
                type_=language_v1.Document.Type.PLAIN_TEXT
            )
            
            # Analyze sentiment
            sentiment_response = self.language_client.analyze_sentiment(
                request={"document": document}
            )
            
            # Analyze entities
            entity_response = self.language_client.analyze_entities(
                request={"document": document}
            )
            
            # Initialize categories
            categories = {}
            
            # Check for negative sentiment
            sentiment = sentiment_response.document_sentiment
            
            # If sentiment is very negative, flag as potentially harmful
            if sentiment.score < -0.7:
                categories[ContentCategory.POTENTIALLY_HARMFUL] = {
                    'severity': SeverityLevel.MEDIUM,
                    'confidence': abs(sentiment.score) * 100,
                    'details': {
                        'google_sentiment_score': sentiment.score,
                        'google_sentiment_magnitude': sentiment.magnitude
                    }
                }
            
            # Check for sensitive entities
            sensitive_entity_types = {
                'PERSON': ContentCategory.PRIVACY_RISK,
                'LOCATION': ContentCategory.PRIVACY_RISK,
                'PHONE_NUMBER': ContentCategory.PRIVACY_RISK,
                'EMAIL': ContentCategory.PRIVACY_RISK,
                'ADDRESS': ContentCategory.PRIVACY_RISK,
                'CREDIT_CARD_NUMBER': ContentCategory.PRIVACY_RISK
            }
            
            # Track detected sensitive entities
            sensitive_entities = []
            
            # Check for sensitive entities
            for entity in entity_response.entities:
                entity_type = language_v1.Entity.Type(entity.type_).name
                
                if entity_type in sensitive_entity_types:
                    sensitive_entities.append({
                        'name': entity.name,
                        'type': entity_type,
                        'salience': entity.salience
                    })
            
            # If sensitive entities are found, flag as privacy risk
            if sensitive_entities:
                categories[ContentCategory.PRIVACY_RISK] = {
                    'severity': SeverityLevel.MEDIUM,
                    'confidence': 75.0,
                    'details': {
                        'sensitive_entities': sensitive_entities
                    }
                }
            
            # Check for toxic content using custom detection
            toxic_content = self._detect_toxic_content(text)
            
            if toxic_content:
                # Add toxic content categories
                for category, data in toxic_content.items():
                    if category not in categories or self._severity_value(data['severity']) > self._severity_value(categories[category]['severity']):
                        categories[category] = data
            
            # Determine if the text is appropriate
            is_appropriate = len(categories) == 0
            
            return FilterResult(
                is_appropriate=is_appropriate,
                categories=categories,
                service_specific_data={
                    'google_sentiment': {
                        'score': sentiment.score,
                        'magnitude': sentiment.magnitude
                    },
                    'google_entities': [
                        {
                            'name': entity.name,
                            'type': language_v1.Entity.Type(entity.type_).name,
                            'salience': entity.salience
                        }
                        for entity in entity_response.entities[:10]  # Limit to top 10 entities
                    ]
                }
            )
            
        except GoogleAPIError as e:
            logger.error(f"Google Cloud Natural Language error: {str(e)}")
            
            return FilterResult(
                is_appropriate=True,  # Default to allowing content on error
                categories={},
                error=f"Google Cloud Natural Language error: {str(e)}"
            )
            
        except Exception as e:
            logger.error(f"Error filtering text with Google Cloud Natural Language: {str(e)}")
            
            return FilterResult(
                is_appropriate=True,  # Default to allowing content on error
                categories={},
                error=f"Error filtering text: {str(e)}"
            )
    
    def _detect_toxic_content(self, text: str) -> Dict[str, Dict[str, Any]]:
        """
        Detect potentially toxic content in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict[str, Dict[str, Any]]: Detected toxic content categories
        """
        # This is a simplified implementation
        # In a real-world scenario, you might use Google's Perspective API
        # or a more sophisticated approach
        
        toxic_categories = {}
        
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
            ],
            ContentCategory.DRUGS: [
                'cocaine', 'heroin', 'meth', 'illegal drugs', 'drug dealing',
                'buy drugs', 'sell drugs'
            ]
        }
        
        # Check text for toxic phrases
        text_lower = text.lower()
        for category, indicators in toxic_indicators.items():
            # Count matches for this category
            matches = 0
            matched_phrases = []
            
            for indicator in indicators:
                if indicator in text_lower:
                    matches += 1
                    matched_phrases.append(indicator)
            
            # If matches found, add to toxic categories
            if matches > 0:
                # Determine severity based on number of matches
                if matches >= 3:
                    severity = SeverityLevel.HIGH
                    confidence = 90.0
                elif matches >= 2:
                    severity = SeverityLevel.MEDIUM
                    confidence = 75.0
                else:
                    severity = SeverityLevel.LOW
                    confidence = 60.0
                
                toxic_categories[category] = {
                    'severity': severity,
                    'confidence': confidence,
                    'details': {
                        'matched_phrases': matched_phrases,
                        'match_count': matches
                    }
                }
        
        return toxic_categories
    
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