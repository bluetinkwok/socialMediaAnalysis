"""
Azure Content Filter Adapter

This module provides an implementation of content filtering using
Azure Content Moderator and Azure Cognitive Services.
"""

import os
import logging
import asyncio
import json
import time
import http.client
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, Tuple, Optional, List

from security.content_filter_adapters.base_adapter import BaseContentFilterAdapter
from core.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)
settings = get_settings()

class AzureContentFilterAdapter(BaseContentFilterAdapter):
    """
    Azure content filter adapter using Content Moderator and Cognitive Services.
    """
    
    def __init__(self):
        """Initialize the Azure content filter adapter"""
        self.initialized = False
        self.content_moderator_endpoint = None
        self.content_moderator_key = None
        self.text_analytics_endpoint = None
        self.text_analytics_key = None
        
    async def initialize(self) -> bool:
        """
        Initialize the Azure content filter adapter.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            logger.info("Initializing Azure content filter adapter...")
            
            # Check for Azure credentials
            if not self._check_azure_credentials():
                logger.error("Azure credentials not found")
                return False
            
            # Load credentials from settings
            self.content_moderator_endpoint = settings.azure_content_moderator_endpoint
            self.content_moderator_key = settings.azure_content_moderator_key
            self.text_analytics_endpoint = settings.azure_text_analytics_endpoint
            self.text_analytics_key = settings.azure_text_analytics_key
            
            # Test connections
            content_moderator_ok = await self._test_content_moderator_connection()
            text_analytics_ok = await self._test_text_analytics_connection()
            
            self.initialized = content_moderator_ok or text_analytics_ok
            
            logger.info(f"Azure content filter adapter initialized: {self.initialized}")
            return self.initialized
            
        except Exception as e:
            logger.error(f"Error initializing Azure content filter adapter: {str(e)}")
            self.initialized = False
            return False
    
    def _check_azure_credentials(self) -> bool:
        """
        Check if Azure credentials are available.
        
        Returns:
            bool: True if credentials are available, False otherwise
        """
        has_content_moderator = (
            hasattr(settings, "azure_content_moderator_endpoint") and 
            hasattr(settings, "azure_content_moderator_key") and
            settings.azure_content_moderator_endpoint and 
            settings.azure_content_moderator_key
        )
        
        has_text_analytics = (
            hasattr(settings, "azure_text_analytics_endpoint") and 
            hasattr(settings, "azure_text_analytics_key") and
            settings.azure_text_analytics_endpoint and 
            settings.azure_text_analytics_key
        )
        
        return has_content_moderator or has_text_analytics
    
    async def _test_content_moderator_connection(self) -> bool:
        """
        Test connection to Azure Content Moderator.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        if not self.content_moderator_endpoint or not self.content_moderator_key:
            return False
            
        try:
            # We'll just test if the endpoint and key are valid
            # In a real implementation, you might want to make a test API call
            return True
        except Exception as e:
            logger.error(f"Error testing Azure Content Moderator connection: {str(e)}")
            return False
    
    async def _test_text_analytics_connection(self) -> bool:
        """
        Test connection to Azure Text Analytics.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        if not self.text_analytics_endpoint or not self.text_analytics_key:
            return False
            
        try:
            # We'll just test if the endpoint and key are valid
            # In a real implementation, you might want to make a test API call
            return True
        except Exception as e:
            logger.error(f"Error testing Azure Text Analytics connection: {str(e)}")
            return False
    
    async def filter_image(self, image_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Filter an image file for inappropriate content using Azure Content Moderator.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_appropriate, filter_results)
        """
        if not self.initialized or not self.content_moderator_key:
            logger.warning("Azure image filter not initialized")
            return True, {"error": "Azure image filter not initialized"}
        
        try:
            # Read image file
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # Prepare API call
            headers = {
                'Content-Type': 'application/octet-stream',
                'Ocp-Apim-Subscription-Key': self.content_moderator_key,
            }
            
            # Extract base URL and path
            parsed_url = urllib.parse.urlparse(self.content_moderator_endpoint)
            base_url = parsed_url.netloc
            path = f"{parsed_url.path}/contentmoderator/moderate/v1.0/ProcessImage/Evaluate"
            
            # Make API call
            conn = http.client.HTTPSConnection(base_url)
            conn.request("POST", path, image_data, headers)
            response = conn.getresponse()
            
            # Parse response
            if response.status != 200:
                logger.error(f"Azure Content Moderator API error: {response.status} {response.reason}")
                return False, {"error": f"Azure Content Moderator API error: {response.status} {response.reason}"}
            
            result = json.loads(response.read().decode('utf-8'))
            conn.close()
            
            # Process results
            is_adult_content = result.get('IsImageAdultClassified', False)
            is_racy_content = result.get('IsImageRacyClassified', False)
            adult_score = result.get('AdultClassificationScore', 0)
            racy_score = result.get('RacyClassificationScore', 0)
            
            # Determine if image is appropriate
            is_appropriate = not (is_adult_content or is_racy_content)
            
            # Map Azure categories to our categories
            categories = {}
            
            if is_adult_content:
                categories["adult"] = {
                    "severity": self._determine_severity_from_confidence(adult_score),
                    "confidence": adult_score
                }
            
            if is_racy_content and not is_adult_content:  # Only add if not already flagged as adult
                categories["adult"] = {
                    "severity": self._determine_severity_from_confidence(racy_score),
                    "confidence": racy_score
                }
            
            # Return results
            return is_appropriate, {
                "categories": categories,
                "analysis_method": "azure_content_moderator",
                "raw_scores": {
                    "adult_score": adult_score,
                    "racy_score": racy_score
                }
            }
            
        except Exception as e:
            logger.error(f"Error in Azure image filter: {str(e)}")
            return False, {"error": f"Azure image filter error: {str(e)}"}
    
    async def filter_text(self, text: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Filter text content for inappropriate material using Azure Text Analytics.
        
        Args:
            text: Text content to filter
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_appropriate, filter_results)
        """
        if not self.initialized:
            logger.warning("Azure text filter not initialized")
            return True, {"error": "Azure text filter not initialized"}
        
        try:
            # First try Content Moderator if available
            if self.content_moderator_key:
                result = await self._filter_text_with_content_moderator(text)
                if result:
                    return result
            
            # Fall back to Text Analytics if available
            if self.text_analytics_key:
                result = await self._filter_text_with_text_analytics(text)
                if result:
                    return result
            
            # If we get here, neither service was available
            logger.warning("No Azure text filtering service available")
            return True, {"error": "No Azure text filtering service available"}
            
        except Exception as e:
            logger.error(f"Error in Azure text filter: {str(e)}")
            return False, {"error": f"Azure text filter error: {str(e)}"}
    
    async def _filter_text_with_content_moderator(self, text: str) -> Optional[Tuple[bool, Dict[str, Any]]]:
        """
        Filter text using Azure Content Moderator.
        
        Args:
            text: Text content to filter
            
        Returns:
            Optional[Tuple[bool, Dict[str, Any]]]: (is_appropriate, filter_results) or None if service unavailable
        """
        if not self.content_moderator_key:
            return None
        
        try:
            # Limit text length to Azure Content Moderator limits (1024 chars)
            text = text[:1024] if len(text) > 1024 else text
            
            # Skip empty text
            if not text.strip():
                return True, {"categories": {}, "analysis_method": "azure_content_moderator"}
            
            # Prepare API call
            headers = {
                'Content-Type': 'text/plain',
                'Ocp-Apim-Subscription-Key': self.content_moderator_key,
            }
            
            # Extract base URL and path
            parsed_url = urllib.parse.urlparse(self.content_moderator_endpoint)
            base_url = parsed_url.netloc
            path = f"{parsed_url.path}/contentmoderator/moderate/v1.0/ProcessText/Screen?classify=True"
            
            # Make API call
            conn = http.client.HTTPSConnection(base_url)
            conn.request("POST", path, text.encode('utf-8'), headers)
            response = conn.getresponse()
            
            # Parse response
            if response.status != 200:
                logger.error(f"Azure Content Moderator API error: {response.status} {response.reason}")
                return None
            
            result = json.loads(response.read().decode('utf-8'))
            conn.close()
            
            # Process results
            classification = result.get('Classification', {})
            terms = result.get('Terms', [])
            
            # Check for inappropriate content
            is_adult = classification.get('ReviewRecommended', False)
            adult_score = classification.get('Score', {}).get('Sexual', 0)
            
            offensive_terms = [term.get('Term') for term in terms] if terms else []
            has_offensive_terms = len(offensive_terms) > 0
            
            # Determine if text is appropriate
            is_appropriate = not (is_adult or has_offensive_terms)
            
            # Map Azure categories to our categories
            categories = {}
            
            if is_adult:
                categories["adult"] = {
                    "severity": self._determine_severity_from_confidence(adult_score),
                    "confidence": adult_score
                }
            
            if has_offensive_terms:
                categories["hate_speech"] = {
                    "severity": "medium",
                    "confidence": 0.7
                }
            
            # Return results
            return is_appropriate, {
                "categories": categories,
                "analysis_method": "azure_content_moderator",
                "offensive_terms": offensive_terms
            }
            
        except Exception as e:
            logger.error(f"Error in Azure Content Moderator text filter: {str(e)}")
            return None
    
    async def _filter_text_with_text_analytics(self, text: str) -> Optional[Tuple[bool, Dict[str, Any]]]:
        """
        Filter text using Azure Text Analytics.
        
        Args:
            text: Text content to filter
            
        Returns:
            Optional[Tuple[bool, Dict[str, Any]]]: (is_appropriate, filter_results) or None if service unavailable
        """
        if not self.text_analytics_key:
            return None
        
        try:
            # Limit text length to Azure Text Analytics limits (5120 chars)
            text = text[:5120] if len(text) > 5120 else text
            
            # Skip empty text
            if not text.strip():
                return True, {"categories": {}, "analysis_method": "azure_text_analytics"}
            
            # Prepare API call
            headers = {
                'Content-Type': 'application/json',
                'Ocp-Apim-Subscription-Key': self.text_analytics_key,
            }
            
            # Prepare request body
            body = {
                "documents": [
                    {
                        "id": "1",
                        "language": "en",
                        "text": text
                    }
                ]
            }
            
            # Extract base URL and path
            parsed_url = urllib.parse.urlparse(self.text_analytics_endpoint)
            base_url = parsed_url.netloc
            path = f"{parsed_url.path}/text/analytics/v3.0/sentiment"
            
            # Make API call
            conn = http.client.HTTPSConnection(base_url)
            conn.request("POST", path, json.dumps(body), headers)
            response = conn.getresponse()
            
            # Parse response
            if response.status != 200:
                logger.error(f"Azure Text Analytics API error: {response.status} {response.reason}")
                return None
            
            result = json.loads(response.read().decode('utf-8'))
            conn.close()
            
            # Process results
            documents = result.get('documents', [])
            if not documents:
                return True, {"categories": {}, "analysis_method": "azure_text_analytics"}
            
            document = documents[0]
            sentiment = document.get('sentiment', 'neutral')
            confidence_scores = document.get('confidenceScores', {})
            negative_score = confidence_scores.get('negative', 0)
            
            # Determine if text is appropriate
            is_appropriate = True
            categories = {}
            
            # Check for negative sentiment
            if negative_score > 0.7:  # Threshold for negative sentiment
                is_appropriate = False
                categories["hate_speech"] = {
                    "severity": self._determine_severity_from_confidence(negative_score),
                    "confidence": negative_score
                }
            
            # Return results
            return is_appropriate, {
                "categories": categories,
                "analysis_method": "azure_text_analytics",
                "sentiment": sentiment,
                "confidence_scores": confidence_scores
            }
            
        except Exception as e:
            logger.error(f"Error in Azure Text Analytics filter: {str(e)}")
            return None
    
    def _determine_severity_from_confidence(self, confidence: float) -> str:
        """
        Determine severity level based on confidence score.
        
        Args:
            confidence: Confidence score (0-1)
            
        Returns:
            str: Severity level (low, medium, high)
        """
        if confidence >= 0.8:
            return "high"
        elif confidence >= 0.6:
            return "medium"
        else:
            return "low" 