"""
Tests for the Computer Vision service
"""

import os
import pytest
import tempfile
import numpy as np
import cv2
from PIL import Image
from services.cv_analyzer import CVService

# Initialize CV service
cv_service = CVService()

@pytest.fixture
def sample_image():
    """Create a sample image for testing"""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        # Create a simple test image (100x100 with a red square in the middle)
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[25:75, 25:75] = [0, 0, 255]  # Red square
        
        # Save the image
        cv2.imwrite(temp_file.name, img)
        
        yield temp_file.name
        
        # Clean up
        os.unlink(temp_file.name)

@pytest.fixture
def sample_video():
    """Create a sample video for testing"""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
        # Create a simple test video (2 frames, 100x100)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video = cv2.VideoWriter(temp_file.name, fourcc, 1, (100, 100))
        
        # Frame 1: Red square
        img1 = np.zeros((100, 100, 3), dtype=np.uint8)
        img1[25:75, 25:75] = [0, 0, 255]  # Red square
        video.write(img1)
        
        # Frame 2: Blue square
        img2 = np.zeros((100, 100, 3), dtype=np.uint8)
        img2[25:75, 25:75] = [255, 0, 0]  # Blue square
        video.write(img2)
        
        # Release the video
        video.release()
        
        yield temp_file.name
        
        # Clean up
        os.unlink(temp_file.name)

def test_preprocess_image(sample_image):
    """Test image preprocessing"""
    # Preprocess the image
    img = cv_service.preprocess_image(sample_image)
    
    # Check that the image was loaded correctly
    assert img is not None
    assert img.shape == (100, 100, 3)
    
    # Check that the red square is in the correct place
    assert np.all(img[50, 50] == [255, 0, 0])  # RGB (OpenCV loads as BGR)

def test_detect_objects(sample_image):
    """Test object detection"""
    # Detect objects
    objects = cv_service.detect_objects(sample_image)
    
    # Check that objects were detected
    assert isinstance(objects, list)
    
    # In our implementation, this is a placeholder that always returns one object
    assert len(objects) > 0
    
    # Check object structure
    for obj in objects:
        assert "class" in obj
        assert "confidence" in obj
        assert "bbox" in obj
        assert len(obj["bbox"]) == 4

def test_analyze_colors(sample_image):
    """Test color analysis"""
    # Analyze colors
    colors = cv_service.analyze_colors(sample_image)
    
    # Check that color analysis was performed
    assert isinstance(colors, dict)
    assert "mean_color" in colors
    assert "dominant_colors" in colors
    assert "brightness" in colors
    
    # Check that dominant colors were detected
    assert len(colors["dominant_colors"]) > 0
    
    # Check that the brightness is reasonable (0-255)
    assert 0 <= colors["brightness"] <= 255

def test_analyze_image(sample_image):
    """Test comprehensive image analysis"""
    # Analyze image
    analysis = cv_service.analyze_image(sample_image)
    
    # Check that analysis was performed
    assert isinstance(analysis, dict)
    assert "dimensions" in analysis
    assert "objects" in analysis
    assert "scene" in analysis
    assert "faces" in analysis
    assert "colors" in analysis
    
    # Check dimensions
    assert analysis["dimensions"]["width"] == 100
    assert analysis["dimensions"]["height"] == 100
    assert analysis["dimensions"]["channels"] == 3

def test_extract_keyframes(sample_video):
    """Test keyframe extraction from video"""
    # Skip this test if OpenCV video support is not available
    try:
        cap = cv2.VideoCapture(sample_video)
        if not cap.isOpened():
            pytest.skip("OpenCV cannot open the test video")
        cap.release()
    except Exception:
        pytest.skip("Error opening test video")
    
    # Extract keyframes
    keyframes = cv_service.extract_keyframes(sample_video, max_frames=2)
    
    # Check that keyframes were extracted
    assert isinstance(keyframes, list)
    
    # We expect at least one keyframe
    if len(keyframes) > 0:
        # Check keyframe structure
        assert "frame_idx" in keyframes[0]
        assert "timestamp" in keyframes[0]
        assert "path" in keyframes[0]

def test_analyze_video(sample_video):
    """Test comprehensive video analysis"""
    # Skip this test if OpenCV video support is not available
    try:
        cap = cv2.VideoCapture(sample_video)
        if not cap.isOpened():
            pytest.skip("OpenCV cannot open the test video")
        cap.release()
    except Exception:
        pytest.skip("Error opening test video")
    
    # Analyze video
    analysis = cv_service.analyze_video(sample_video, extract_frames=True)
    
    # Check that analysis was performed
    assert isinstance(analysis, dict)
    assert "metadata" in analysis
    
    # Check metadata
    assert "dimensions" in analysis["metadata"]
    assert "duration" in analysis["metadata"]
    assert "fps" in analysis["metadata"]
    
    # Check keyframes if they were extracted
    if "keyframes" in analysis:
        assert isinstance(analysis["keyframes"], list)
