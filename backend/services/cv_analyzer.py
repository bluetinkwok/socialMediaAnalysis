"""
Computer Vision Analyzer Service

This module provides computer vision capabilities for analyzing images and videos,
including object detection, scene recognition, face detection, and color analysis.
"""

import os
import cv2
import numpy as np
from PIL import Image
import tensorflow as tf
from transformers import AutoFeatureExtractor, AutoModelForImageClassification
import logging
import tempfile
import json
from typing import Dict, List, Tuple, Optional, Any, Union
import matplotlib.pyplot as plt
from pathlib import Path
import torch
from torchvision import transforms

# Configure logging
logger = logging.getLogger(__name__)

class CVService:
    """
    Service for computer vision analysis of images and videos.
    
    Provides functionality for:
    - Object detection
    - Scene recognition
    - Face detection
    - Color analysis
    - Keyframe extraction from videos
    """
    
    def __init__(self):
        """Initialize the Computer Vision service with necessary models."""
        logger.info("Initializing Computer Vision Service")
        
        self.models_loaded = False
        self.face_cascade = None
        self.scene_model = None
        self.scene_extractor = None
        self.object_detection_model = None
        
        # Initialize models lazily when first needed
        
    def _load_models(self):
        """Load all CV models if not already loaded."""
        if self.models_loaded:
            return
            
        logger.info("Loading Computer Vision models")
        
        # Load face detection model
        try:
            face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(face_cascade_path)
            logger.info("Face detection model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading face detection model: {str(e)}")
            
        # Load scene recognition model
        try:
            model_name = "microsoft/resnet-50"  # A good general-purpose image classifier
            self.scene_extractor = AutoFeatureExtractor.from_pretrained(model_name)
            self.scene_model = AutoModelForImageClassification.from_pretrained(model_name)
            logger.info("Scene recognition model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading scene recognition model: {str(e)}")
            
        # Mark models as loaded
        self.models_loaded = True
        
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Load and preprocess an image for analysis.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Preprocessed image as numpy array
        """
        try:
            # Read the image using OpenCV
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not read image at {image_path}")
                
            # Convert from BGR to RGB (OpenCV loads as BGR, but most models expect RGB)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            return img_rgb
        except Exception as e:
            logger.error(f"Error preprocessing image {image_path}: {str(e)}")
            raise
            
    def detect_objects(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Detect objects in an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List of detected objects with class, confidence, and bounding box
        """
        self._load_models()
        
        try:
            # For now, implement a simple object detection using color-based segmentation
            # In a production environment, you would use a proper object detection model
            img = self.preprocess_image(image_path)
            
            # Simple object detection placeholder
            # In reality, you would use a model like YOLO, Faster R-CNN, or SSD
            height, width = img.shape[:2]
            
            # Placeholder detection results
            # In a real implementation, these would come from the model
            objects = [
                {
                    "class": "placeholder_object",
                    "confidence": 0.85,
                    "bbox": [width // 4, height // 4, width // 2, height // 2]  # [x, y, w, h]
                }
            ]
            
            return objects
        except Exception as e:
            logger.error(f"Error detecting objects in {image_path}: {str(e)}")
            return []
            
    def recognize_scene(self, image_path: str) -> Dict[str, float]:
        """
        Recognize the scene or content of an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary of scene categories and their confidence scores
        """
        self._load_models()
        
        if not self.scene_model or not self.scene_extractor:
            logger.error("Scene recognition model not loaded")
            return {"error": 1.0}
            
        try:
            # Load image with PIL (transformers expects PIL images)
            image = Image.open(image_path)
            
            # Prepare image for the model
            inputs = self.scene_extractor(image, return_tensors="pt")
            
            # Get model predictions
            with torch.no_grad():
                outputs = self.scene_model(**inputs)
                
            # Get predicted class probabilities
            probs = outputs.logits.softmax(dim=1)[0]
            
            # Get top 5 predictions
            top5_prob, top5_indices = torch.topk(probs, 5)
            
            # Convert to dictionary
            results = {}
            for i, (score, idx) in enumerate(zip(top5_prob, top5_indices)):
                label = self.scene_model.config.id2label[idx.item()]
                results[label] = score.item()
                
            return results
        except Exception as e:
            logger.error(f"Error recognizing scene in {image_path}: {str(e)}")
            return {"error": 1.0}
            
    def detect_faces(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Detect faces in an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List of detected faces with bounding boxes and confidence scores
        """
        self._load_models()
        
        if not self.face_cascade:
            logger.error("Face detection model not loaded")
            return []
            
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not read image at {image_path}")
                
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            # Process results
            results = []
            for (x, y, w, h) in faces:
                results.append({
                    "bbox": [int(x), int(y), int(w), int(h)],
                    "confidence": 0.9  # Placeholder, Haar cascades don't provide confidence
                })
                
            return results
        except Exception as e:
            logger.error(f"Error detecting faces in {image_path}: {str(e)}")
            return []
            
    def analyze_colors(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze the color distribution of an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with color analysis results
        """
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not read image at {image_path}")
                
            # Convert to RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Reshape the image to be a list of pixels
            pixels = img_rgb.reshape((-1, 3))
            
            # Calculate color statistics
            mean_color = pixels.mean(axis=0).tolist()
            std_color = pixels.std(axis=0).tolist()
            
            # Calculate dominant colors using K-means clustering
            pixels = np.float32(pixels)
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, 0.1)
            k = 5  # Number of dominant colors
            _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
            
            # Count occurrences of each cluster
            counts = np.bincount(labels.flatten())
            
            # Sort clusters by count (most frequent first)
            sorted_indices = np.argsort(counts)[::-1]
            sorted_centers = centers[sorted_indices].astype(int).tolist()
            sorted_percentages = (counts[sorted_indices] / len(labels) * 100).tolist()
            
            # Prepare dominant colors
            dominant_colors = []
            for i in range(min(k, len(sorted_centers))):
                dominant_colors.append({
                    "rgb": sorted_centers[i],
                    "percentage": sorted_percentages[i]
                })
                
            # Calculate brightness
            brightness = np.mean(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
            
            return {
                "mean_color": mean_color,
                "std_color": std_color,
                "dominant_colors": dominant_colors,
                "brightness": brightness,
                "is_grayscale": self._is_grayscale(img_rgb)
            }
        except Exception as e:
            logger.error(f"Error analyzing colors in {image_path}: {str(e)}")
            return {"error": str(e)}
            
    def _is_grayscale(self, img_rgb: np.ndarray) -> bool:
        """
        Check if an image is grayscale.
        
        Args:
            img_rgb: RGB image as numpy array
            
        Returns:
            True if the image is grayscale, False otherwise
        """
        # Check if all channels are approximately equal
        r, g, b = cv2.split(img_rgb)
        r_g_diff = cv2.absdiff(r, g)
        r_b_diff = cv2.absdiff(r, b)
        g_b_diff = cv2.absdiff(g, b)
        
        # If the differences are all below a threshold, consider it grayscale
        threshold = 15
        return (
            np.mean(r_g_diff) < threshold and
            np.mean(r_b_diff) < threshold and
            np.mean(g_b_diff) < threshold
        )
        
    def extract_keyframes(self, video_path: str, max_frames: int = 10) -> List[Dict[str, Any]]:
        """
        Extract key frames from a video file.
        
        Args:
            video_path: Path to the video file
            max_frames: Maximum number of frames to extract
            
        Returns:
            List of dictionaries containing frame data and timestamps
        """
        try:
            # Open the video file
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Could not open video at {video_path}")
                
            # Get video properties
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = frame_count / fps if fps > 0 else 0
            
            # Calculate frame interval for keyframe extraction
            if frame_count <= max_frames:
                interval = 1
            else:
                interval = frame_count // max_frames
                
            keyframes = []
            prev_frame = None
            frame_idx = 0
            
            # Create temporary directory for saving frames
            with tempfile.TemporaryDirectory() as temp_dir:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    # Process only frames at the calculated interval
                    if frame_idx % interval == 0:
                        # Calculate timestamp
                        timestamp = frame_idx / fps if fps > 0 else 0
                        
                        # Save frame to temp file
                        frame_path = os.path.join(temp_dir, f"frame_{frame_idx}.jpg")
                        cv2.imwrite(frame_path, frame)
                        
                        # Add frame info to results
                        keyframes.append({
                            "frame_idx": frame_idx,
                            "timestamp": timestamp,
                            "timestamp_str": self._format_timestamp(timestamp),
                            "path": frame_path,
                            "scene_change": self._is_scene_change(prev_frame, frame) if prev_frame is not None else False
                        })
                        
                        prev_frame = frame.copy()
                        
                    frame_idx += 1
                    
                # Release the video capture object
                cap.release()
                
                # Further analyze each keyframe
                for kf in keyframes:
                    # Add scene recognition
                    kf["scene"] = self.recognize_scene(kf["path"])
                    
                    # Add face detection
                    kf["faces"] = self.detect_faces(kf["path"])
                    
                    # Add color analysis
                    kf["colors"] = self.analyze_colors(kf["path"])
                    
                return keyframes
        except Exception as e:
            logger.error(f"Error extracting keyframes from {video_path}: {str(e)}")
            return []
            
    def _format_timestamp(self, seconds: float) -> str:
        """
        Format a timestamp in seconds to HH:MM:SS format.
        
        Args:
            seconds: Timestamp in seconds
            
        Returns:
            Formatted timestamp string
        """
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
        
    def _is_scene_change(self, prev_frame: np.ndarray, curr_frame: np.ndarray, threshold: float = 30.0) -> bool:
        """
        Detect if there is a scene change between two consecutive frames.
        
        Args:
            prev_frame: Previous frame
            curr_frame: Current frame
            threshold: Difference threshold for scene change detection
            
        Returns:
            True if scene change detected, False otherwise
        """
        # Convert frames to grayscale
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate absolute difference
        frame_diff = cv2.absdiff(prev_gray, curr_gray)
        
        # Calculate mean difference
        mean_diff = np.mean(frame_diff)
        
        # Return True if difference is above threshold
        return mean_diff > threshold
        
    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with all analysis results
        """
        try:
            results = {
                "path": image_path,
                "filename": os.path.basename(image_path),
                "file_size": os.path.getsize(image_path)
            }
            
            # Get image dimensions
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not read image at {image_path}")
                
            results["dimensions"] = {
                "width": img.shape[1],
                "height": img.shape[0],
                "channels": img.shape[2] if len(img.shape) > 2 else 1
            }
            
            # Perform various analyses
            results["objects"] = self.detect_objects(image_path)
            results["scene"] = self.recognize_scene(image_path)
            results["faces"] = self.detect_faces(image_path)
            results["colors"] = self.analyze_colors(image_path)
            
            return results
        except Exception as e:
            logger.error(f"Error analyzing image {image_path}: {str(e)}")
            return {"error": str(e)}
            
    def analyze_video(self, video_path: str, extract_frames: bool = True) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a video.
        
        Args:
            video_path: Path to the video file
            extract_frames: Whether to extract and analyze keyframes
            
        Returns:
            Dictionary with all analysis results
        """
        try:
            # Open the video file
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Could not open video at {video_path}")
                
            # Get video properties
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            # Release the video capture object
            cap.release()
            
            results = {
                "path": video_path,
                "filename": os.path.basename(video_path),
                "file_size": os.path.getsize(video_path),
                "metadata": {
                    "duration": duration,
                    "duration_str": self._format_timestamp(duration),
                    "fps": fps,
                    "frame_count": frame_count,
                    "dimensions": {
                        "width": width,
                        "height": height
                    }
                }
            }
            
            # Extract and analyze keyframes if requested
            if extract_frames:
                results["keyframes"] = self.extract_keyframes(video_path)
                
                # Analyze scene distribution
                scene_counts = {}
                for kf in results["keyframes"]:
                    if "scene" in kf:
                        top_scene = max(kf["scene"].items(), key=lambda x: x[1])[0]
                        scene_counts[top_scene] = scene_counts.get(top_scene, 0) + 1
                        
                results["scene_distribution"] = scene_counts
                
                # Count faces
                total_faces = sum(len(kf.get("faces", [])) for kf in results["keyframes"])
                results["total_faces"] = total_faces
                
            return results
        except Exception as e:
            logger.error(f"Error analyzing video {video_path}: {str(e)}")
            return {"error": str(e)}
            
    def detect_content_moderation_issues(self, image_path: str) -> Dict[str, Any]:
        """
        Detect potential content moderation issues in an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with moderation results
        """
        # This is a placeholder implementation
        # In a production environment, you would use specialized models for content moderation
        try:
            # For demonstration purposes, return a placeholder result
            return {
                "has_issues": False,
                "confidence": 0.95,
                "categories": {
                    "adult": 0.01,
                    "violence": 0.02,
                    "hate_symbols": 0.01
                }
            }
        except Exception as e:
            logger.error(f"Error in content moderation for {image_path}: {str(e)}")
            return {"error": str(e)}
