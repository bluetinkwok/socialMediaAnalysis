"""
Content Filter

This module provides AI-based content filtering to detect inappropriate content
in images, text, and other file types.
"""

import os
import logging
import mimetypes
from typing import Dict, Any, List, Tuple, Optional, Union, Type
from pathlib import Path
import importlib
import asyncio
from enum import Enum

from core.config import get_settings
from security.content_filter_adapters.base_adapter import ContentFilterAdapter
from security.content_filter_adapters.local_adapter import LocalContentFilterAdapter
from security.content_filter_adapters.aws_adapter import AWSContentFilterAdapter
from security.content_filter_adapters.azure_adapter import AzureContentFilterAdapter

# Configure logging
logger = logging.getLogger(__name__)
settings = get_settings()

class ContentCategory(Enum):
    """Categories of inappropriate content"""
    ADULT = "adult"
    VIOLENCE = "violence"
    HATE_SPEECH = "hate_speech"
    SELF_HARM = "self_harm"
    DRUGS = "drugs"
    SPAM = "spam"

class SeverityLevel(Enum):
    """Severity levels for content filtering"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ContentFilter:
    """
    Filters uploaded content for inappropriate material.
    
    This class provides functionality to:
    - Detect inappropriate content in images, text, documents, and videos
    - Classify content into categories (adult, violence, hate speech, etc.)
    - Assign severity levels to detected inappropriate content
    - Use pluggable adapters for different content filtering services
    """
    
    # Content categories
    CATEGORIES = {
        "adult": "Adult or sexual content",
        "violence": "Violent or graphic content",
        "hate_speech": "Hate speech or discriminatory content",
        "self_harm": "Self-harm or suicide content",
        "drugs": "Drug-related content",
        "spam": "Spam, scams, or misleading content"
    }
    
    # Severity levels
    SEVERITY_LEVELS = {
        "low": 1,
        "medium": 2,
        "high": 3
    }
    
    def __init__(self):
        """Initialize the content filter"""
        self.initialized = False
        self.settings = get_settings()
        self.adapter = None
        self.adapter_name = None
        self.available_adapters = {
            "local": LocalContentFilterAdapter,
            "aws": AWSContentFilterAdapter,
            "azure": AzureContentFilterAdapter
        }
    
    async def initialize(self) -> bool:
        """
        Initialize the content filter with the configured adapter.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            logger.info("Initializing content filter...")
            
            # Get adapter configuration from settings
            adapter_name = self.settings.content_filter_adapter
            adapter_config = getattr(self.settings, f"content_filter_{adapter_name}_config", {})
            
            # Initialize the adapter
            if adapter_name in self.available_adapters:
                adapter_class = self.available_adapters[adapter_name]
                self.adapter = adapter_class()
                adapter_initialized = await self.adapter.initialize(adapter_config)
                
                if adapter_initialized:
                    self.adapter_name = adapter_name
                    self.initialized = True
                    logger.info(f"Content filter initialized with {adapter_name} adapter")
                else:
                    logger.error(f"Failed to initialize {adapter_name} adapter")
            else:
                logger.error(f"Unknown adapter: {adapter_name}")
            
            return self.initialized
            
        except Exception as e:
            logger.error(f"Error initializing content filter: {str(e)}")
            self.initialized = False
            return False
    
    async def filter_file(self, file_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Filter a file for inappropriate content.
        
        Args:
            file_path: Path to the file to filter
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_appropriate, filter_results)
        """
        if not self.initialized:
            logger.warning("Content filter not initialized")
            return True, {"warning": "Content filter not initialized"}
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False, {"error": "File not found"}
            
            # Get file mime type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = "application/octet-stream"
            
            # Initialize results
            results = {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "mime_type": mime_type,
                "appropriate": True,
                "categories": {},
                "overall_severity": "none",
                "adapter": self.adapter_name
            }
            
            # Filter based on file type
            if mime_type.startswith("image/"):
                is_appropriate, filter_results = await self.filter_image(file_path)
            elif mime_type.startswith("text/") or mime_type in ["application/json", "application/xml"]:
                is_appropriate, filter_results = await self.filter_text(file_path)
            elif mime_type.startswith("video/"):
                is_appropriate, filter_results = await self.filter_video(file_path)
            elif mime_type in ["application/pdf", "application/msword", 
                               "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               "application/vnd.ms-excel", 
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
                is_appropriate, filter_results = await self.filter_document(file_path)
            else:
                logger.warning(f"Unsupported mime type for content filtering: {mime_type}")
                return True, {
                    "warning": f"Unsupported mime type for content filtering: {mime_type}",
                    "file_path": file_path,
                    "file_name": os.path.basename(file_path),
                    "mime_type": mime_type,
                    "appropriate": True,
                    "adapter": self.adapter_name
                }
            
            # Merge results
            results.update(filter_results)
            results["appropriate"] = is_appropriate
            
            return is_appropriate, results
            
        except Exception as e:
            logger.error(f"Error filtering file: {str(e)}")
            return False, {"error": f"Error filtering file: {str(e)}"}
    
    async def filter_image(self, image_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Filter an image for inappropriate content.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_appropriate, filter_results)
        """
        if not self.initialized:
            logger.warning("Content filter not initialized")
            return True, {"warning": "Content filter not initialized"}
        
        try:
            # Call adapter to filter image
            filter_results = await self.adapter.filter_image(image_path)
            
            # Determine if image is appropriate
            is_appropriate = self._is_content_appropriate(filter_results)
            
            return is_appropriate, filter_results
            
        except Exception as e:
            logger.error(f"Error filtering image: {str(e)}")
            return False, {"error": f"Error filtering image: {str(e)}"}
    
    async def filter_text(self, text_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Filter text content for inappropriate content.
        
        Args:
            text_path: Path to the text file
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_appropriate, filter_results)
        """
        if not self.initialized:
            logger.warning("Content filter not initialized")
            return True, {"warning": "Content filter not initialized"}
        
        try:
            # Read text file
            with open(text_path, 'r', encoding='utf-8', errors='replace') as f:
                text_content = f.read()
            
            # Call adapter to filter text
            filter_results = await self.adapter.filter_text(text_content)
            
            # Determine if text is appropriate
            is_appropriate = self._is_content_appropriate(filter_results)
            
            return is_appropriate, filter_results
            
        except Exception as e:
            logger.error(f"Error filtering text: {str(e)}")
            return False, {"error": f"Error filtering text: {str(e)}"}
    
    async def filter_document(self, document_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Filter a document for inappropriate content.
        
        Args:
            document_path: Path to the document file
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_appropriate, filter_results)
        """
        if not self.initialized:
            logger.warning("Content filter not initialized")
            return True, {"warning": "Content filter not initialized"}
        
        try:
            # Extract text from document
            # This would typically use a library like textract or pdfminer
            # For now, we'll use the adapter's document filtering if available
            if hasattr(self.adapter, 'filter_document'):
                filter_results = await self.adapter.filter_document(document_path)
            else:
                # Fallback to basic text extraction
                import textract
                text_content = textract.process(document_path).decode('utf-8', errors='replace')
                filter_results = await self.adapter.filter_text(text_content)
                filter_results["extraction_method"] = "textract"
            
            # Determine if document is appropriate
            is_appropriate = self._is_content_appropriate(filter_results)
            
            return is_appropriate, filter_results
            
        except ImportError:
            logger.warning("Document filtering requires textract library")
            return True, {"warning": "Document filtering requires textract library"}
        except Exception as e:
            logger.error(f"Error filtering document: {str(e)}")
            return False, {"error": f"Error filtering document: {str(e)}"}
    
    async def filter_video(self, video_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Filter a video for inappropriate content.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_appropriate, filter_results)
        """
        if not self.initialized:
            logger.warning("Content filter not initialized")
            return True, {"warning": "Content filter not initialized"}
        
        try:
            # Call adapter to filter video if available
            if hasattr(self.adapter, 'filter_video'):
                filter_results = await self.adapter.filter_video(video_path)
                
                # Determine if video is appropriate
                is_appropriate = self._is_content_appropriate(filter_results)
                
                return is_appropriate, filter_results
            else:
                logger.warning(f"Video filtering not supported by {self.adapter_name} adapter")
                return True, {"warning": f"Video filtering not supported by {self.adapter_name} adapter"}
            
        except Exception as e:
            logger.error(f"Error filtering video: {str(e)}")
            return False, {"error": f"Error filtering video: {str(e)}"}
    
    def _is_content_appropriate(self, filter_results: Dict[str, Any]) -> bool:
        """
        Determine if content is appropriate based on filter results.
        
        Args:
            filter_results: Results from content filtering
            
        Returns:
            bool: True if content is appropriate, False otherwise
        """
        # Check for high severity flags
        if filter_results.get("overall_severity") == "high":
            return False
        
        # Check for medium severity in sensitive categories
        if filter_results.get("overall_severity") == "medium":
            sensitive_categories = ["adult", "violence", "hate_speech", "self_harm"]
            categories = filter_results.get("categories", {})
            
            for category in sensitive_categories:
                if category in categories and categories[category].get("severity") == "medium":
                    return False
        
        return True
    
    def register_adapter(self, name: str, adapter_class: Type[ContentFilterAdapter]) -> bool:
        """
        Register a new content filter adapter.
        
        Args:
            name: Name of the adapter
            adapter_class: Adapter class
            
        Returns:
            bool: True if registration was successful, False otherwise
        """
        try:
            if not issubclass(adapter_class, ContentFilterAdapter):
                logger.error(f"Adapter class must inherit from ContentFilterAdapter")
                return False
            
            self.available_adapters[name] = adapter_class
            logger.info(f"Registered content filter adapter: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering adapter: {str(e)}")
            return False

# Create a global instance of the content filter
content_filter = ContentFilter() 