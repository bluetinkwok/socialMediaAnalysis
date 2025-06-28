"""
Test script for success patterns API endpoints
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from db.database import SessionLocal
from db.models import Post, AnalyticsData, PlatformType, ContentType
from analytics.pattern_recognizer import PatternRecognizer

client = TestClient(app)


def create_test_data():
    """Create test data for API tests"""
    db = SessionLocal()
    
    try:
        # Create test post
        post = Post(
            platform=PlatformType.YOUTUBE,
            content_type=ContentType.VIDEO,
            url="https://example.com/test_video",
            title="Test Video",
            description="Test video for API testing",
            author="test_user",
            publish_date=datetime.now() - timedelta(days=1),
            hashtags=["test", "video", "api"],
            engagement_metrics={
                'views': 5000,
                'likes': 500,
                'comments': 100,
                'shares': 50
            }
        )
        
        db.add(post)
        db.commit()
        db.refresh(post)
        
        # Create analytics data with success patterns
        analytics = AnalyticsData(
            post_id=post.id,
            performance_score=85.0,
            engagement_rate=10.0,
            virality_score=75.0,
            trend_score=65.0,
            success_patterns={
                "successful_video": {
                    "detected": True,
                    "confidence": 0.85,
                    "metrics": {
                        "performance_score": 85.0,
                        "platform_avg": 65.0
                    }
                },
                "rapid_growth": {
                    "detected": True,
                    "confidence": 0.78,
                    "metrics": {
                        "engagement_velocity": 2.5,
                        "platform_avg_velocity": 0.8
                    }
                }
            }
        )
        
        db.add(analytics)
        db.commit()
        
        return post.id
        
    except Exception as e:
        db.rollback()
        print(f"Error creating test data: {e}")
        return None
    finally:
        db.close()


def test_get_all_patterns():
    """Test GET /api/v1/success-patterns/"""
    response = client.get("/api/v1/success-patterns/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "patterns" in data
    assert "count" in data
    assert "filters" in data


def test_get_post_patterns():
    """Test GET /api/v1/success-patterns/post/{post_id}"""
    # Create test data and get post ID
    post_id = create_test_data()
    if not post_id:
        pytest.skip("Failed to create test data")
    
    response = client.get(f"/api/v1/success-patterns/post/{post_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "patterns" in data
    assert "count" in data
    assert data["post_id"] == post_id
    
    # Check that we have the expected patterns
    patterns = data["patterns"]
    pattern_names = [p["name"] for p in patterns]
    assert "successful_video" in pattern_names
    assert "rapid_growth" in pattern_names


def test_get_top_patterns():
    """Test GET /api/v1/success-patterns/top"""
    response = client.get("/api/v1/success-patterns/top")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "patterns" in data
    assert "count" in data
    assert "filters" in data


def test_get_patterns_by_platform():
    """Test GET /api/v1/success-patterns/by-platform"""
    response = client.get("/api/v1/success-patterns/by-platform")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "patterns_by_platform" in data
    assert "platforms_count" in data
    assert "filters" in data


def test_get_patterns_by_content_type():
    """Test GET /api/v1/success-patterns/by-content-type"""
    response = client.get("/api/v1/success-patterns/by-content-type")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "patterns_by_content_type" in data
    assert "content_types_count" in data
    assert "filters" in data


def test_filter_by_platform():
    """Test filtering patterns by platform"""
    response = client.get("/api/v1/success-patterns/?platform=youtube")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    
    # Check that all patterns are for YouTube
    for pattern in data["patterns"]:
        assert pattern["platform"] == "youtube"


def test_filter_by_content_type():
    """Test filtering patterns by content type"""
    response = client.get("/api/v1/success-patterns/?content_type=video")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    
    # Check that all patterns are for video content
    for pattern in data["patterns"]:
        assert pattern["content_type"] == "video"


def test_filter_by_time_range():
    """Test filtering patterns by time range"""
    response = client.get("/api/v1/success-patterns/?days=7")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["filters"]["days"] == 7 