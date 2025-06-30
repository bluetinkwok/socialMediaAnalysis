"""
Local Content Filter Adapter

This module provides a local implementation of content filtering using
open-source libraries and models.
"""

import os
import logging
import re
import json
import asyncio
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
import tempfile
import numpy as np
from PIL import Image

from security.content_filter_adapters.base_adapter import ContentFilterAdapter

# Configure logging
logger = logging.getLogger(__name__)

class LocalContentFilterAdapter(ContentFilterAdapter):
    """
    Local content filter adapter using open-source libraries and basic heuristics.
    
    This adapter provides basic content filtering capabilities without requiring
    external API services. It uses:
    - Basic text pattern matching for text content
    - Image analysis using PIL and numpy for images
    - Configurable word lists and thresholds
    """
    
    def __init__(self):
        """Initialize the local content filter adapter"""
        self.initialized = False
        self.word_lists = {}
        self.config = {}
        
    async def initialize(self, config: Dict[str, Any] = None) -> bool:
        """
        Initialize the local content filter adapter.
        
        Args:
            config: Configuration parameters for the adapter
            
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            logger.info("Initializing local content filter adapter")
            
            # Set default configuration
            self.config = {
                "word_lists_dir": os.path.join(os.path.dirname(__file__), "word_lists"),
                "adult_threshold": 0.6,
                "violence_threshold": 0.6,
                "hate_speech_threshold": 0.5,
                "drugs_threshold": 0.7,
                "self_harm_threshold": 0.7,
                "spam_threshold": 0.8,
                "image_skin_tone_threshold": 0.5,
                "image_red_threshold": 0.4
            }
            
            # Override defaults with provided config
            if config:
                self.config.update(config)
            
            # Load word lists
            await self._load_word_lists()
            
            self.initialized = True
            logger.info("Local content filter adapter initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing local content filter adapter: {str(e)}")
            return False
    
    async def _load_word_lists(self) -> None:
        """Load word lists for text filtering"""
        try:
            word_lists_dir = self.config["word_lists_dir"]
            
            # Create directory if it doesn't exist
            os.makedirs(word_lists_dir, exist_ok=True)
            
            # Define default word lists
            default_lists = {
                "adult": ["xxx", "porn", "sex", "nude", "naked", "adult", "explicit"],
                "violence": ["kill", "murder", "blood", "gore", "death", "violent", "weapon"],
                "hate_speech": ["hate", "racist", "slur", "nazi", "discrimination"],
                "self_harm": ["suicide", "self-harm", "cutting", "kill myself"],
                "drugs": ["cocaine", "heroin", "meth", "drug", "weed", "marijuana"],
                "spam": ["buy now", "click here", "free money", "winner", "viagra", "enlargement"]
            }
            
            # Load word lists from files or use defaults
            for category, default_words in default_lists.items():
                file_path = os.path.join(word_lists_dir, f"{category}.txt")
                
                # Create file with default words if it doesn't exist
                if not os.path.exists(file_path):
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write("\n".join(default_words))
                    self.word_lists[category] = default_words
                    logger.info(f"Created default word list for {category}")
                else:
                    # Load words from file
                    with open(file_path, "r", encoding="utf-8") as f:
                        words = [line.strip().lower() for line in f if line.strip()]
                    self.word_lists[category] = words
                    logger.info(f"Loaded {len(words)} words for {category}")
            
        except Exception as e:
            logger.error(f"Error loading word lists: {str(e)}")
            raise
    
    async def filter_image(self, image_path: str) -> Dict[str, Any]:
        """
        Filter an image for inappropriate content using basic heuristics.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dict[str, Any]: Filtering results
        """
        try:
            # Check if file exists
            if not os.path.exists(image_path):
                return {
                    "categories": {},
                    "overall_severity": "none",
                    "error": f"Image file not found: {image_path}"
                }
            
            # Load image
            img = Image.open(image_path)
            
            # Convert to RGB if needed
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # Get image data as numpy array
            img_data = np.array(img)
            
            # Calculate metrics
            metrics = self._calculate_image_metrics(img_data)
            
            # Analyze metrics to determine categories and severity
            categories = {}
            
            # Check for potential adult content based on skin tone percentage
            skin_tone_percentage = metrics["skin_tone_percentage"]
            if skin_tone_percentage > self.config["image_skin_tone_threshold"]:
                severity = "low"
                if skin_tone_percentage > 0.7:
                    severity = "medium"
                if skin_tone_percentage > 0.85:
                    severity = "high"
                
                categories["adult"] = {
                    "severity": severity,
                    "confidence": skin_tone_percentage,
                    "details": f"Detected {skin_tone_percentage:.2f} skin tone percentage"
                }
            
            # Check for potential violence based on red percentage
            red_percentage = metrics["red_percentage"]
            if red_percentage > self.config["image_red_threshold"]:
                severity = "low"
                if red_percentage > 0.6:
                    severity = "medium"
                if red_percentage > 0.8:
                    severity = "high"
                
                categories["violence"] = {
                    "severity": severity,
                    "confidence": red_percentage,
                    "details": f"Detected {red_percentage:.2f} red percentage"
                }
            
            # Determine overall severity
            overall_severity = self._determine_highest_severity(categories)
            
            # Return results
            return {
                "categories": categories,
                "overall_severity": overall_severity,
                "metrics": metrics,
                "dimensions": {
                    "width": img.width,
                    "height": img.height
                }
            }
            
        except Exception as e:
            logger.error(f"Error filtering image: {str(e)}")
            return {
                "categories": {},
                "overall_severity": "none",
                "error": f"Error filtering image: {str(e)}"
            }
    
    def _calculate_image_metrics(self, img_data: np.ndarray) -> Dict[str, float]:
        """
        Calculate metrics from image data for content filtering.
        
        Args:
            img_data: Image data as numpy array
            
        Returns:
            Dict[str, float]: Image metrics
        """
        # Get image dimensions
        height, width, _ = img_data.shape
        total_pixels = height * width
        
        # Calculate skin tone percentage (very basic approximation)
        # This is a very simplified approach and will have many false positives
        r, g, b = img_data[:,:,0], img_data[:,:,1], img_data[:,:,2]
        
        # Basic skin tone detection (this is a very simplified approach)
        skin_mask = (r > 60) & (g > 40) & (b > 20) & \
                   (r > g) & (r > b) & \
                   (r - g > 15) & \
                   (r - b > 15)
        
        skin_tone_percentage = np.sum(skin_mask) / total_pixels
        
        # Calculate red percentage (for violence detection)
        red_mask = (r > 150) & (r > g * 1.5) & (r > b * 1.5)
        red_percentage = np.sum(red_mask) / total_pixels
        
        # Calculate brightness
        brightness = np.mean(img_data) / 255
        
        # Calculate contrast
        contrast = np.std(img_data) / 255
        
        return {
            "skin_tone_percentage": float(skin_tone_percentage),
            "red_percentage": float(red_percentage),
            "brightness": float(brightness),
            "contrast": float(contrast)
        }
    
    async def filter_text(self, text: str) -> Dict[str, Any]:
        """
        Filter text for inappropriate content using word lists and pattern matching.
        
        Args:
            text: Text content to filter
            
        Returns:
            Dict[str, Any]: Filtering results
        """
        try:
            if not text:
                return {
                    "categories": {},
                    "overall_severity": "none",
                    "details": "Empty text"
                }
            
            # Convert to lowercase for case-insensitive matching
            text_lower = text.lower()
            
            # Initialize results
            categories = {}
            
            # Check each category
            for category, words in self.word_lists.items():
                # Count matches for each word
                matches = []
                for word in words:
                    # Use word boundary to match whole words
                    pattern = r'\b' + re.escape(word) + r'\b'
                    found = re.findall(pattern, text_lower)
                    if found:
                        matches.extend(found)
                
                # Calculate match ratio (matches per 1000 characters)
                match_ratio = len(matches) / max(1, len(text) / 1000)
                
                # Get threshold for this category
                threshold = self.config.get(f"{category}_threshold", 0.5)
                
                # Determine severity based on match ratio
                if match_ratio > 0:
                    severity = "low"
                    confidence = match_ratio / 10  # Normalize to 0-1 range
                    
                    if match_ratio > threshold * 2:
                        severity = "high"
                        confidence = min(0.95, confidence * 1.5)
                    elif match_ratio > threshold:
                        severity = "medium"
                        confidence = min(0.9, confidence * 1.2)
                    
                    categories[category] = {
                        "severity": severity,
                        "confidence": confidence,
                        "match_count": len(matches),
                        "matches": matches[:10]  # Limit to first 10 matches
                    }
            
            # Determine overall severity
            overall_severity = self._determine_highest_severity(categories)
            
            # Return results
            return {
                "categories": categories,
                "overall_severity": overall_severity,
                "text_length": len(text)
            }
            
        except Exception as e:
            logger.error(f"Error filtering text: {str(e)}")
            return {
                "categories": {},
                "overall_severity": "none",
                "error": f"Error filtering text: {str(e)}"
            }

    def _determine_highest_severity(self, categories: Dict[str, Dict[str, Any]]) -> str:
        """
        Determine the highest severity from a set of categories.
        
        Args:
            categories: Dictionary of categories and their severities
            
        Returns:
            str: The highest severity
        """
        severities = [category["severity"] for category in categories.values()]
        return max(set(severities), key=severities.count) 