"""
Tests for the Computer Vision analyzer
"""

import pytest
from unittest.mock import MagicMock, patch
from analytics.cv_analyzer import CVAnalyzer

@pytest.fixture
def cv_analyzer():
    """Create a CV analyzer instance for testing"""
    return CVAnalyzer()

@pytest.fixture
def mock_post_data():
    """Create mock post data for testing"""
    return {
        'images': ['/path/to/image1.jpg', '/path/to/image2.jpg'],
        'videos': ['/path/to/video1.mp4']
    }

@pytest.fixture
def mock_image_analysis():
    """Create mock image analysis results"""
    return {
        'path': '/path/to/image1.jpg',
        'filename': 'image1.jpg',
        'dimensions': {'width': 800, 'height': 600, 'channels': 3},
        'objects': [{'class': 'person', 'confidence': 0.95, 'bbox': [100, 100, 200, 300]}],
        'scene': {'outdoor': 0.8, 'nature': 0.7},
        'faces': [{'bbox': [200, 150, 100, 100], 'confidence': 0.9}],
        'colors': {
            'mean_color': [120, 130, 140],
            'dominant_colors': [{'rgb': [200, 200, 200], 'percentage': 60}],
            'brightness': 150,
            'is_grayscale': False
        }
    }

@pytest.fixture
def mock_video_analysis():
    """Create mock video analysis results"""
    return {
        'path': '/path/to/video1.mp4',
        'filename': 'video1.mp4',
        'metadata': {
            'duration': 30.5,
            'fps': 30,
            'frame_count': 915,
            'dimensions': {'width': 1280, 'height': 720}
        },
        'keyframes': [
            {
                'frame_idx': 0,
                'timestamp': 0.0,
                'timestamp_str': '00:00:00',
                'scene_change': False,
                'scene': {'indoor': 0.9, 'room': 0.8},
                'faces': [{'bbox': [300, 200, 100, 100], 'confidence': 0.85}],
                'colors': {'brightness': 120, 'is_grayscale': False}
            }
        ]
    }

def test_determine_content_type(cv_analyzer, mock_post_data):
    """Test content type determination"""
    # Test mixed content
    content_type = cv_analyzer._determine_content_type(mock_post_data)
    assert content_type == 'mixed'
    
    # Test image-only content
    image_only = {'images': mock_post_data['images'], 'videos': []}
    content_type = cv_analyzer._determine_content_type(image_only)
    assert content_type == 'image'
    
    # Test video-only content
    video_only = {'images': [], 'videos': mock_post_data['videos']}
    content_type = cv_analyzer._determine_content_type(video_only)
    assert content_type == 'video'
    
    # Test no content
    no_content = {'images': [], 'videos': []}
    content_type = cv_analyzer._determine_content_type(no_content)
    assert content_type == 'none'

@patch('analytics.cv_analyzer.CVAnalyzer._analyze_image_content')
@patch('analytics.cv_analyzer.CVAnalyzer._analyze_video_content')
@patch('analytics.cv_analyzer.CVAnalyzer._analyze_mixed_content')
def test_analyze_content(mock_mixed, mock_video, mock_image, cv_analyzer):
    """Test content analysis routing"""
    # Setup mocks
    mock_image.return_value = {'content_type': 'image'}
    mock_video.return_value = {'content_type': 'video'}
    mock_mixed.return_value = {'content_type': 'mixed'}
    
    # Test image content
    image_data = {'images': ['/path/to/image.jpg'], 'videos': []}
    result = cv_analyzer.analyze_content(image_data)
    assert result['content_type'] == 'image'
    mock_image.assert_called_once_with(image_data)
    
    # Reset mocks
    mock_image.reset_mock()
    mock_video.reset_mock()
    mock_mixed.reset_mock()
    
    # Test video content
    video_data = {'images': [], 'videos': ['/path/to/video.mp4']}
    result = cv_analyzer.analyze_content(video_data)
    assert result['content_type'] == 'video'
    mock_video.assert_called_once_with(video_data)
    
    # Reset mocks
    mock_image.reset_mock()
    mock_video.reset_mock()
    mock_mixed.reset_mock()
    
    # Test mixed content
    mixed_data = {'images': ['/path/to/image.jpg'], 'videos': ['/path/to/video.mp4']}
    result = cv_analyzer.analyze_content(mixed_data)
    assert result['content_type'] == 'mixed'
    mock_mixed.assert_called_once_with(mixed_data)

@patch('os.path.exists')
@patch('analytics.cv_analyzer.CVAnalyzer._calculate_image_aggregate_metrics')
def test_analyze_image_content(mock_metrics, mock_exists, cv_analyzer, mock_post_data, mock_image_analysis):
    """Test image content analysis"""
    # Setup mocks
    mock_exists.return_value = True
    mock_metrics.return_value = {'visual_appeal_score': 8.5}
    cv_analyzer.cv_service = MagicMock()
    cv_analyzer.cv_service.analyze_image.return_value = mock_image_analysis
    
    # Test image analysis
    image_data = {'images': ['/path/to/image.jpg'], 'videos': []}
    result = cv_analyzer._analyze_image_content(image_data)
    
    # Verify results
    assert result['content_type'] == 'image'
    assert result['images_analyzed'] == 1
    assert len(result['image_analysis']) == 1
    assert 'aggregate_metrics' in result
    assert result['aggregate_metrics']['visual_appeal_score'] == 8.5
    
    # Verify mocks were called correctly
    cv_analyzer.cv_service.analyze_image.assert_called_once_with('/path/to/image.jpg')
    mock_metrics.assert_called_once()

@patch('os.path.exists')
@patch('analytics.cv_analyzer.CVAnalyzer._calculate_video_aggregate_metrics')
def test_analyze_video_content(mock_metrics, mock_exists, cv_analyzer, mock_post_data, mock_video_analysis):
    """Test video content analysis"""
    # Setup mocks
    mock_exists.return_value = True
    mock_metrics.return_value = {'engagement_potential_score': 7.5}
    cv_analyzer.cv_service = MagicMock()
    cv_analyzer.cv_service.analyze_video.return_value = mock_video_analysis
    
    # Test video analysis
    video_data = {'images': [], 'videos': ['/path/to/video.mp4']}
    result = cv_analyzer._analyze_video_content(video_data)
    
    # Verify results
    assert result['content_type'] == 'video'
    assert result['videos_analyzed'] == 1
    assert len(result['video_analysis']) == 1
    assert 'aggregate_metrics' in result
    assert result['aggregate_metrics']['engagement_potential_score'] == 7.5
    
    # Verify mocks were called correctly
    cv_analyzer.cv_service.analyze_video.assert_called_once_with('/path/to/video.mp4')
    mock_metrics.assert_called_once()

def test_extract_content_features(cv_analyzer):
    """Test content feature extraction"""
    # Setup
    cv_analyzer.analyze_content = MagicMock()
    cv_analyzer.analyze_content.return_value = {
        'content_type': 'image',
        'aggregate_metrics': {
            'has_people': True,
            'visual_appeal_score': 8.5,
            'dominant_scenes': {'outdoor': 0.8, 'nature': 0.7}
        }
    }
    
    # Test feature extraction
    post_data = {'images': ['/path/to/image.jpg']}
    features = cv_analyzer.extract_content_features(post_data)
    
    # Verify results
    assert features['content_type'] == 'image'
    assert features['has_visual_content'] is True
    assert features['has_people'] is True
    assert features['visual_quality_score'] == 8.5
    assert features['dominant_scene'] == 'outdoor'

def test_calculate_content_quality_score(cv_analyzer):
    """Test content quality score calculation"""
    # Setup
    cv_analyzer.extract_content_features = MagicMock()
    
    # Test with visual content
    cv_analyzer.extract_content_features.return_value = {
        'has_visual_content': True,
        'visual_quality_score': 8.5
    }
    score = cv_analyzer.calculate_content_quality_score({})
    assert score == 8.5
    
    # Test without visual content
    cv_analyzer.extract_content_features.return_value = {
        'has_visual_content': False,
        'visual_quality_score': 0
    }
    score = cv_analyzer.calculate_content_quality_score({})
    assert score == 0

def test_identify_visual_patterns(cv_analyzer):
    """Test visual pattern identification"""
    # Setup
    cv_analyzer.extract_content_features = MagicMock()
    
    # Test with people and high quality
    cv_analyzer.extract_content_features.return_value = {
        'has_visual_content': True,
        'has_people': True,
        'visual_quality_score': 8.5,
        'dominant_scene': 'outdoor'
    }
    patterns = cv_analyzer.identify_visual_patterns({})
    
    # Verify patterns
    assert len(patterns) == 3
    assert any(p['pattern_name'] == 'people_present' for p in patterns)
    assert any(p['pattern_name'] == 'high_quality_visuals' for p in patterns)
    assert any(p['pattern_name'] == 'scene_outdoor' for p in patterns)
    
    # Test without visual content
    cv_analyzer.extract_content_features.return_value = {
        'has_visual_content': False
    }
    patterns = cv_analyzer.identify_visual_patterns({})
    assert len(patterns) == 0
