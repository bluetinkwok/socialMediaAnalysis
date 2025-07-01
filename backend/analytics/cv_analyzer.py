"""
Computer Vision Analyzer for Social Media Content

This module provides computer vision analysis capabilities for social media content,
integrating with the analytics engine to provide insights based on visual content.
"""

import logging
from typing import Dict, List, Any, Optional, Union
import os
import json
from pathlib import Path
import numpy as np
from ..services.cv_analyzer import CVService

# Configure logging
logger = logging.getLogger(__name__)

class CVAnalyzer:
    """
    Computer Vision analyzer for social media content.
    
    Analyzes visual content (images and videos) in social media posts to extract
    insights and metrics that can be used by the analytics engine.
    """
    
    def __init__(self):
        """Initialize the CV analyzer with the CV service."""
        logger.info("Initializing Computer Vision Analyzer")
        self.cv_service = CVService()
        
        # Mapping of content types to analysis functions
        self.analysis_functions = {
            'image': self._analyze_image_content,
            'video': self._analyze_video_content,
            'mixed': self._analyze_mixed_content
        }
        
    def analyze_content(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the visual content of a social media post.
        
        Args:
            post_data: Post data containing content URLs and metadata
            
        Returns:
            Dictionary with visual analysis results
        """
        try:
            # Determine content type
            content_type = self._determine_content_type(post_data)
            
            # Call appropriate analysis function based on content type
            if content_type in self.analysis_functions:
                return self.analysis_functions[content_type](post_data)
            else:
                logger.warning(f"Unsupported content type: {content_type}")
                return {}
        except Exception as e:
            logger.error(f"Error analyzing content: {str(e)}")
            return {}
            
    def _determine_content_type(self, post_data: Dict[str, Any]) -> str:
        """
        Determine the type of visual content in a post.
        
        Args:
            post_data: Post data containing content URLs and metadata
            
        Returns:
            Content type: 'image', 'video', 'mixed', or 'none'
        """
        has_images = False
        has_videos = False
        
        # Check for images
        if 'images' in post_data and post_data['images']:
            has_images = True
            
        # Check for videos
        if 'videos' in post_data and post_data['videos']:
            has_videos = True
            
        # Determine content type
        if has_images and has_videos:
            return 'mixed'
        elif has_images:
            return 'image'
        elif has_videos:
            return 'video'
        else:
            return 'none'
            
    def _analyze_image_content(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze image content in a post.
        
        Args:
            post_data: Post data containing image URLs and metadata
            
        Returns:
            Dictionary with image analysis results
        """
        results = {
            'content_type': 'image',
            'images_analyzed': 0,
            'image_analysis': []
        }
        
        # Process each image
        if 'images' in post_data and post_data['images']:
            for img_idx, img_url in enumerate(post_data['images']):
                try:
                    # In a real implementation, we would download the image first
                    # For this implementation, we'll assume the image is already downloaded
                    # and the URL is actually a local path
                    if os.path.exists(img_url):
                        img_analysis = self.cv_service.analyze_image(img_url)
                        results['image_analysis'].append(img_analysis)
                        results['images_analyzed'] += 1
                except Exception as e:
                    logger.error(f"Error analyzing image {img_url}: {str(e)}")
                    
        # Calculate aggregate metrics
        if results['images_analyzed'] > 0:
            results['aggregate_metrics'] = self._calculate_image_aggregate_metrics(results['image_analysis'])
            
        return results
        
    def _analyze_video_content(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze video content in a post.
        
        Args:
            post_data: Post data containing video URLs and metadata
            
        Returns:
            Dictionary with video analysis results
        """
        results = {
            'content_type': 'video',
            'videos_analyzed': 0,
            'video_analysis': []
        }
        
        # Process each video
        if 'videos' in post_data and post_data['videos']:
            for vid_idx, vid_url in enumerate(post_data['videos']):
                try:
                    # In a real implementation, we would download the video first
                    # For this implementation, we'll assume the video is already downloaded
                    # and the URL is actually a local path
                    if os.path.exists(vid_url):
                        vid_analysis = self.cv_service.analyze_video(vid_url)
                        results['video_analysis'].append(vid_analysis)
                        results['videos_analyzed'] += 1
                except Exception as e:
                    logger.error(f"Error analyzing video {vid_url}: {str(e)}")
                    
        # Calculate aggregate metrics
        if results['videos_analyzed'] > 0:
            results['aggregate_metrics'] = self._calculate_video_aggregate_metrics(results['video_analysis'])
            
        return results
        
    def _analyze_mixed_content(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze mixed content (images and videos) in a post.
        
        Args:
            post_data: Post data containing image and video URLs and metadata
            
        Returns:
            Dictionary with mixed content analysis results
        """
        # Analyze images
        image_results = self._analyze_image_content(post_data)
        
        # Analyze videos
        video_results = self._analyze_video_content(post_data)
        
        # Combine results
        results = {
            'content_type': 'mixed',
            'images_analyzed': image_results['images_analyzed'],
            'videos_analyzed': video_results['videos_analyzed'],
            'image_analysis': image_results['image_analysis'],
            'video_analysis': video_results['video_analysis']
        }
        
        # Calculate combined metrics
        if image_results['images_analyzed'] > 0 or video_results['videos_analyzed'] > 0:
            results['aggregate_metrics'] = self._calculate_mixed_aggregate_metrics(
                image_results.get('aggregate_metrics', {}),
                video_results.get('aggregate_metrics', {})
            )
            
        return results
        
    def _calculate_image_aggregate_metrics(self, image_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate aggregate metrics from multiple image analyses.
        
        Args:
            image_analyses: List of image analysis results
            
        Returns:
            Dictionary with aggregate metrics
        """
        if not image_analyses:
            return {}
            
        # Initialize metrics
        metrics = {
            'avg_brightness': 0,
            'color_diversity': 0,
            'face_count': 0,
            'object_count': 0,
            'dominant_scenes': {},
            'has_people': False
        }
        
        # Calculate metrics
        for img_analysis in image_analyses:
            # Brightness
            if 'colors' in img_analysis and 'brightness' in img_analysis['colors']:
                metrics['avg_brightness'] += img_analysis['colors']['brightness']
                
            # Face count
            if 'faces' in img_analysis:
                metrics['face_count'] += len(img_analysis['faces'])
                if len(img_analysis['faces']) > 0:
                    metrics['has_people'] = True
                    
            # Object count
            if 'objects' in img_analysis:
                metrics['object_count'] += len(img_analysis['objects'])
                
            # Scene categories
            if 'scene' in img_analysis:
                for scene, confidence in img_analysis['scene'].items():
                    if scene != 'error':
                        metrics['dominant_scenes'][scene] = metrics['dominant_scenes'].get(scene, 0) + confidence
                        
        # Average brightness
        metrics['avg_brightness'] /= len(image_analyses)
        
        # Sort and limit dominant scenes
        metrics['dominant_scenes'] = dict(
            sorted(metrics['dominant_scenes'].items(), key=lambda x: x[1], reverse=True)[:5]
        )
        
        # Calculate visual appeal score (simplified)
        metrics['visual_appeal_score'] = self._calculate_visual_appeal_score(image_analyses)
        
        return metrics
        
    def _calculate_video_aggregate_metrics(self, video_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate aggregate metrics from multiple video analyses.
        
        Args:
            video_analyses: List of video analysis results
            
        Returns:
            Dictionary with aggregate metrics
        """
        if not video_analyses:
            return {}
            
        # Initialize metrics
        metrics = {
            'total_duration': 0,
            'avg_fps': 0,
            'scene_changes': 0,
            'face_appearances': 0,
            'dominant_scenes': {},
            'has_people': False
        }
        
        # Calculate metrics
        for vid_analysis in video_analyses:
            # Duration
            if 'metadata' in vid_analysis and 'duration' in vid_analysis['metadata']:
                metrics['total_duration'] += vid_analysis['metadata']['duration']
                
            # FPS
            if 'metadata' in vid_analysis and 'fps' in vid_analysis['metadata']:
                metrics['avg_fps'] += vid_analysis['metadata']['fps']
                
            # Scene changes and faces
            if 'keyframes' in vid_analysis:
                # Count scene changes
                scene_changes = sum(1 for kf in vid_analysis['keyframes'] if kf.get('scene_change', False))
                metrics['scene_changes'] += scene_changes
                
                # Count faces
                for kf in vid_analysis['keyframes']:
                    if 'faces' in kf and len(kf['faces']) > 0:
                        metrics['face_appearances'] += len(kf['faces'])
                        metrics['has_people'] = True
                        
                # Scene categories
                for kf in vid_analysis['keyframes']:
                    if 'scene' in kf:
                        for scene, confidence in kf['scene'].items():
                            if scene != 'error':
                                metrics['dominant_scenes'][scene] = metrics['dominant_scenes'].get(scene, 0) + confidence
                                
        # Average FPS
        if len(video_analyses) > 0:
            metrics['avg_fps'] /= len(video_analyses)
            
        # Sort and limit dominant scenes
        metrics['dominant_scenes'] = dict(
            sorted(metrics['dominant_scenes'].items(), key=lambda x: x[1], reverse=True)[:5]
        )
        
        # Calculate engagement potential score (simplified)
        metrics['engagement_potential_score'] = self._calculate_video_engagement_score(video_analyses)
        
        return metrics
        
    def _calculate_mixed_aggregate_metrics(
        self, 
        image_metrics: Dict[str, Any], 
        video_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate aggregate metrics from both image and video analyses.
        
        Args:
            image_metrics: Aggregate image metrics
            video_metrics: Aggregate video metrics
            
        Returns:
            Dictionary with combined metrics
        """
        # Initialize combined metrics
        metrics = {}
        
        # Combine face and people detection
        metrics['has_people'] = image_metrics.get('has_people', False) or video_metrics.get('has_people', False)
        metrics['face_count'] = image_metrics.get('face_count', 0) + video_metrics.get('face_appearances', 0)
        
        # Combine scene categories
        metrics['dominant_scenes'] = {}
        
        # Add image scenes
        for scene, confidence in image_metrics.get('dominant_scenes', {}).items():
            metrics['dominant_scenes'][scene] = confidence
            
        # Add video scenes
        for scene, confidence in video_metrics.get('dominant_scenes', {}).items():
            metrics['dominant_scenes'][scene] = metrics['dominant_scenes'].get(scene, 0) + confidence
            
        # Sort and limit dominant scenes
        metrics['dominant_scenes'] = dict(
            sorted(metrics['dominant_scenes'].items(), key=lambda x: x[1], reverse=True)[:5]
        )
        
        # Calculate combined content quality score
        image_score = image_metrics.get('visual_appeal_score', 0)
        video_score = video_metrics.get('engagement_potential_score', 0)
        
        # Weight based on content amount
        if image_score and video_score:
            metrics['content_quality_score'] = (image_score + video_score) / 2
        elif image_score:
            metrics['content_quality_score'] = image_score
        elif video_score:
            metrics['content_quality_score'] = video_score
        else:
            metrics['content_quality_score'] = 0
            
        return metrics
        
    def _calculate_visual_appeal_score(self, image_analyses: List[Dict[str, Any]]) -> float:
        """
        Calculate a visual appeal score for images.
        
        Args:
            image_analyses: List of image analysis results
            
        Returns:
            Visual appeal score (0-10)
        """
        if not image_analyses:
            return 0
            
        total_score = 0
        
        for img_analysis in image_analyses:
            img_score = 5.0  # Start with neutral score
            
            # Adjust based on color diversity
            if 'colors' in img_analysis and 'dominant_colors' in img_analysis['colors']:
                color_count = len(img_analysis['colors']['dominant_colors'])
                # More colors generally better, up to a point
                img_score += min(color_count / 2, 1.5)
                
            # Adjust based on brightness (prefer medium brightness)
            if 'colors' in img_analysis and 'brightness' in img_analysis['colors']:
                brightness = img_analysis['colors']['brightness']
                # Optimal brightness around 120-140 (on 0-255 scale)
                brightness_score = 1.0 - abs(brightness - 130) / 130
                img_score += brightness_score
                
            # Adjust based on faces (presence of faces often increases engagement)
            if 'faces' in img_analysis:
                face_count = len(img_analysis['faces'])
                if face_count > 0:
                    img_score += min(face_count * 0.5, 1.5)
                    
            # Adjust based on image quality (placeholder)
            # In a real implementation, we would assess sharpness, noise, etc.
            img_score += 0.5
            
            # Cap score at 10
            img_score = min(img_score, 10.0)
            
            total_score += img_score
            
        # Return average score
        return total_score / len(image_analyses)
        
    def _calculate_video_engagement_score(self, video_analyses: List[Dict[str, Any]]) -> float:
        """
        Calculate an engagement potential score for videos.
        
        Args:
            video_analyses: List of video analysis results
            
        Returns:
            Engagement potential score (0-10)
        """
        if not video_analyses:
            return 0
            
        total_score = 0
        
        for vid_analysis in video_analyses:
            vid_score = 5.0  # Start with neutral score
            
            # Adjust based on duration (prefer medium length videos)
            if 'metadata' in vid_analysis and 'duration' in vid_analysis['metadata']:
                duration = vid_analysis['metadata']['duration']
                # Optimal duration around 30-90 seconds
                if duration < 15:
                    vid_score -= 1.0  # Too short
                elif 15 <= duration <= 120:
                    vid_score += 1.5  # Good length
                else:
                    vid_score -= (duration - 120) / 120  # Longer videos lose points
                    
            # Adjust based on scene changes (more dynamic content)
            if 'keyframes' in vid_analysis:
                scene_changes = sum(1 for kf in vid_analysis['keyframes'] if kf.get('scene_change', False))
                keyframe_count = len(vid_analysis['keyframes'])
                
                if keyframe_count > 0:
                    change_rate = scene_changes / keyframe_count
                    # Prefer videos with moderate scene change rate
                    if 0.1 <= change_rate <= 0.4:
                        vid_score += 1.5
                    elif change_rate > 0.4:
                        vid_score += 0.5  # Too many changes can be distracting
                        
            # Adjust based on faces (presence of faces often increases engagement)
            face_count = 0
            if 'keyframes' in vid_analysis:
                for kf in vid_analysis['keyframes']:
                    if 'faces' in kf:
                        face_count += len(kf['faces'])
                        
            if face_count > 0:
                vid_score += min(1.5, face_count * 0.2)
                
            # Adjust based on video quality (placeholder)
            # In a real implementation, we would assess resolution, bitrate, etc.
            vid_score += 0.5
            
            # Cap score at 10
            vid_score = min(vid_score, 10.0)
            
            total_score += vid_score
            
        # Return average score
        return total_score / len(video_analyses)
        
    def extract_content_features(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract visual features from post content for use in analytics.
        
        Args:
            post_data: Post data containing content URLs and metadata
            
        Returns:
            Dictionary with extracted features
        """
        # Analyze content
        analysis_results = self.analyze_content(post_data)
        
        # Extract relevant features
        features = {
            'content_type': analysis_results.get('content_type', 'none'),
            'has_visual_content': analysis_results.get('content_type', 'none') != 'none',
            'has_people': False,
            'visual_quality_score': 0
        }
        
        # Add metrics based on content type
        if 'aggregate_metrics' in analysis_results:
            metrics = analysis_results['aggregate_metrics']
            features['has_people'] = metrics.get('has_people', False)
            
            # Add quality score based on content type
            if features['content_type'] == 'image':
                features['visual_quality_score'] = metrics.get('visual_appeal_score', 0)
            elif features['content_type'] == 'video':
                features['visual_quality_score'] = metrics.get('engagement_potential_score', 0)
            elif features['content_type'] == 'mixed':
                features['visual_quality_score'] = metrics.get('content_quality_score', 0)
                
            # Add dominant scene if available
            if 'dominant_scenes' in metrics and metrics['dominant_scenes']:
                top_scene = max(metrics['dominant_scenes'].items(), key=lambda x: x[1])[0]
                features['dominant_scene'] = top_scene
                
        return features
        
    def calculate_content_quality_score(self, post_data: Dict[str, Any]) -> float:
        """
        Calculate a quality score for the visual content of a post.
        
        Args:
            post_data: Post data containing content URLs and metadata
            
        Returns:
            Quality score (0-10)
        """
        # Extract features
        features = self.extract_content_features(post_data)
        
        # If no visual content, return 0
        if not features['has_visual_content']:
            return 0
            
        # Return visual quality score
        return features['visual_quality_score']
        
    def identify_visual_patterns(self, post_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify visual patterns in the post content.
        
        Args:
            post_data: Post data containing content URLs and metadata
            
        Returns:
            List of identified patterns
        """
        # Extract features
        features = self.extract_content_features(post_data)
        
        # Initialize patterns
        patterns = []
        
        # If no visual content, return empty list
        if not features['has_visual_content']:
            return patterns
            
        # Check for people
        if features.get('has_people', False):
            patterns.append({
                'pattern_type': 'visual',
                'pattern_name': 'people_present',
                'confidence': 0.9,
                'description': 'Content contains people/faces'
            })
            
        # Check for high quality content
        quality_score = features.get('visual_quality_score', 0)
        if quality_score >= 7.5:
            patterns.append({
                'pattern_type': 'visual',
                'pattern_name': 'high_quality_visuals',
                'confidence': quality_score / 10,
                'description': 'Content has high visual quality'
            })
            
        # Check for specific scene types
        if 'dominant_scene' in features:
            scene = features['dominant_scene']
            patterns.append({
                'pattern_type': 'visual',
                'pattern_name': f'scene_{scene.lower().replace(" ", "_")}',
                'confidence': 0.8,
                'description': f'Content features {scene} scene'
            })
            
        return patterns
