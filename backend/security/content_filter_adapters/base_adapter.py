"""
Base Content Filter Adapter

This module defines the base interface for content filter adapters.
All content filter implementations should inherit from this base class.
"""

import abc
import logging
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass

# Configure logging
logger = logging.getLogger(__name__)

class ContentCategory:
    """Standard content categories for filtering"""
    ADULT = "adult"
    VIOLENCE = "violence"
    HATE_SPEECH = "hate_speech"
    SELF_HARM = "self_harm"
    DRUGS = "drugs"
    SPAM = "spam"
    POTENTIALLY_HARMFUL = "potentially_harmful"
    PRIVACY_RISK = "privacy_risk"

class SeverityLevel:
    """Standard severity levels for filtered content"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class FilterResult:
    """
    Standard result format for content filtering operations
    
    Attributes:
        is_appropriate: Whether the content is appropriate (passes filter)
        categories: Dictionary of detected categories with details
        error: Optional error message if filtering failed
        service_specific_data: Optional service-specific data
    """
    is_appropriate: bool
    categories: Dict[str, Dict[str, Any]]
    error: Optional[str] = None
    service_specific_data: Optional[Dict[str, Any]] = None

class ContentFilterAdapter(abc.ABC):
    """
    Base class for content filter adapters
    
    This abstract class defines the interface that all content filter
    adapters must implement.
    """
    
    @abc.abstractmethod
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the adapter
        
        Args:
            config: Configuration options for the adapter
        """
        pass
    
    @abc.abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the adapter with necessary setup
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def filter_image(self, image_path: str) -> FilterResult:
        """
        Filter an image for inappropriate content
        
        Args:
            image_path: Path to the image file
            
        Returns:
            FilterResult: Results of the content filtering
        """
        pass
    
    @abc.abstractmethod
    def filter_text(self, text: str) -> FilterResult:
        """
        Filter text for inappropriate content
        
        Args:
            text: Text to filter
            
        Returns:
            FilterResult: Results of the content filtering
        """
        pass
    
    def filter_document(self, document_path: str) -> FilterResult:
        """
        Filter a document for inappropriate content
        
        Default implementation extracts text and uses filter_text.
        Adapters can override this for specialized document filtering.
        
        Args:
            document_path: Path to the document file
            
        Returns:
            FilterResult: Results of the content filtering
        """
        # Default implementation - extract text and use filter_text
        try:
            # This is a simple implementation that would need to be expanded
            # to properly handle different document types
            with open(document_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            
            return self.filter_text(text)
        except Exception as e:
            return FilterResult(
                is_appropriate=True,  # Default to allowing content on error
                categories={},
                error=f"Error filtering document: {str(e)}"
            )
    
    def filter_video(self, video_path: str, frame_interval: int = 5) -> FilterResult:
        """
        Filter a video for inappropriate content
        
        Default implementation returns an error.
        Adapters should override this for video filtering.
        
        Args:
            video_path: Path to the video file
            frame_interval: Interval between frames to check (in seconds)
            
        Returns:
            FilterResult: Results of the content filtering
        """
        # Default implementation - return an error
        return FilterResult(
            is_appropriate=True,  # Default to allowing content
            categories={},
            error="Video filtering not implemented in this adapter"
        )
    
    def _standardize_results(self, raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize filtering results to match the expected format.
        
        Args:
            raw_results: Raw results from the adapter-specific implementation
            
        Returns:
            Dict[str, Any]: Standardized results
        """
        # Initialize standardized results
        standardized = {
            "categories": {},
            "overall_severity": "none"
        }
        
        # Copy raw results to details field
        standardized["details"] = raw_results
        
        # Extract categories and severity if available
        if "categories" in raw_results:
            standardized["categories"] = raw_results["categories"]
        
        if "overall_severity" in raw_results:
            standardized["overall_severity"] = raw_results["overall_severity"]
        else:
            # Determine overall severity from categories
            highest_severity = self._determine_highest_severity(standardized["categories"])
            standardized["overall_severity"] = highest_severity
        
        return standardized
    
    def _determine_highest_severity(self, categories: Dict[str, Dict[str, Any]]) -> str:
        """
        Determine the highest severity level from a set of categories.
        
        Args:
            categories: Dictionary of categories with severity levels
            
        Returns:
            str: Highest severity level ("none", "low", "medium", "high")
        """
        severity_values = {
            "none": 0,
            "low": 1,
            "medium": 2,
            "high": 3
        }
        
        highest = "none"
        
        for category, data in categories.items():
            severity = data.get("severity", "none")
            if severity_values.get(severity, 0) > severity_values.get(highest, 0):
                highest = severity
        
        return highest 