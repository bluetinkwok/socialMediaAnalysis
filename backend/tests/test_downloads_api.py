"""
Tests for download API endpoints
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from db.database import get_database
from db.models import Base, Post, MediaFile
from db.schemas import PlatformType

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_downloads.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_database():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_database] = override_get_database

@pytest.fixture(scope="function")
def setup_test_db():
    """Create test database tables"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)

class TestDownloadEndpoints:
    """Test cases for download API endpoints"""
    
    def test_single_download_success(self, client, setup_test_db):
        """Test successful single URL download"""
        
        # Mock URL validation
        with patch('api.v1.downloads.url_validator.validate_url_format') as mock_validator:
            mock_validator.return_value = {
                'is_valid': True,
                'validation_details': {
                    'platform': {
                        'platform': 'threads',
                        'is_supported': True
                    }
                }
            }
            
            # Mock downloader
            with patch('api.v1.downloads.ThreadsDownloader') as mock_downloader_class:
                mock_downloader = AsyncMock()
                mock_downloader.__aenter__.return_value = mock_downloader
                mock_downloader.__aexit__.return_value = None
                mock_downloader.extract_content.return_value = {
                    'success': True,
                    'platform': 'threads',
                    'url': 'https://www.threads.net/@test/post/123',
                    'text': 'Test content',
                    'username': 'test_user',
                    'content_type': 'text'
                }
                mock_downloader_class.return_value = mock_downloader
                
                # Mock storage
                with patch('api.v1.downloads.store_content') as mock_store:
                    mock_post = MagicMock()
                    mock_post.id = 1
                    mock_store.return_value = mock_post
                    
                    response = client.post("/api/v1/downloads/single", json={
                        "url": "https://www.threads.net/@test/post/123",
                        "download_files": False
                    })
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["data"]["platform"] == "threads"
                    assert data["data"]["post_id"] == 1
    
    def test_single_download_invalid_url(self, client, setup_test_db):
        """Test single download with invalid URL"""
        
        with patch('api.v1.downloads.url_validator.validate_url_format') as mock_validator:
            mock_validator.return_value = {
                'is_valid': False,
                'error': 'Invalid URL format'
            }
            
            response = client.post("/api/v1/downloads/single", json={
                "url": "invalid-url",
                "download_files": False
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "Invalid URL" in data["error"]
    
    def test_single_download_unsupported_platform(self, client, setup_test_db):
        """Test single download with unsupported platform"""
        
        with patch('api.v1.downloads.url_validator.validate_url_format') as mock_validator:
            mock_validator.return_value = {
                'is_valid': True,
                'validation_details': {
                    'platform': {
                        'platform': 'unsupported',
                        'is_supported': False
                    }
                }
            }
            
            response = client.post("/api/v1/downloads/single", json={
                "url": "https://unsupported.com/post/123",
                "download_files": False
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "Unsupported platform" in data["error"]
    
    def test_single_download_extraction_failure(self, client, setup_test_db):
        """Test single download when content extraction fails"""
        
        with patch('api.v1.downloads.url_validator.validate_url_format') as mock_validator:
            mock_validator.return_value = {
                'is_valid': True,
                'validation_details': {
                    'platform': {
                        'platform': 'threads',
                        'is_supported': True
                    }
                }
            }
            
            # Patch the PLATFORM_DOWNLOADERS dictionary directly
            with patch('api.v1.downloads.PLATFORM_DOWNLOADERS') as mock_downloaders:
                mock_downloader = AsyncMock()
                mock_downloader.__aenter__.return_value = mock_downloader
                mock_downloader.__aexit__.return_value = None
                mock_downloader.extract_content.return_value = {
                    'success': False,
                    'error': 'Content not found'
                }
                
                mock_downloader_class = MagicMock(return_value=mock_downloader)
                mock_downloaders.get.return_value = mock_downloader_class
                
                response = client.post("/api/v1/downloads/single", json={
                    "url": "https://www.threads.net/@test/post/123",
                    "download_files": False
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is False
                assert "Content not found" in data["error"]
    
    def test_single_download_empty_url(self, client, setup_test_db):
        """Test single download with empty URL"""
        
        response = client.post("/api/v1/downloads/single", json={
            "url": "",
            "download_files": False
        })
        
        assert response.status_code == 400
        assert "URL cannot be empty" in response.json()["detail"]
    
    def test_batch_download_success(self, client, setup_test_db):
        """Test successful batch URL download"""
        
        urls = [
            "https://www.threads.net/@test1/post/123",
            "https://www.threads.net/@test2/post/456"
        ]
        
        with patch('api.v1.downloads.url_validator.validate_url_format') as mock_validator:
            mock_validator.return_value = {
                'is_valid': True,
                'validation_details': {
                    'platform': {
                        'platform': 'threads',
                        'is_supported': True
                    }
                }
            }
            
            with patch('api.v1.downloads.ThreadsDownloader') as mock_downloader_class:
                mock_downloader = AsyncMock()
                mock_downloader.__aenter__.return_value = mock_downloader
                mock_downloader.__aexit__.return_value = None
                mock_downloader.extract_content.return_value = {
                    'success': True,
                    'platform': 'threads',
                    'text': 'Test content',
                    'username': 'test_user',
                    'content_type': 'text'
                }
                mock_downloader_class.return_value = mock_downloader
                
                with patch('api.v1.downloads.store_content') as mock_store:
                    mock_post = MagicMock()
                    mock_post.id = 1
                    mock_store.return_value = mock_post
                    
                    with patch('asyncio.sleep'):  # Skip delays in tests
                        response = client.post("/api/v1/downloads/batch", json={
                            "urls": urls,
                            "download_files": False
                        })
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["data"]["summary"]["total_urls"] == 2
                    assert data["data"]["summary"]["successful"] == 2
                    assert data["data"]["summary"]["failed"] == 0
                    assert data["data"]["summary"]["success_rate"] == 1.0
    
    def test_batch_download_mixed_results(self, client, setup_test_db):
        """Test batch download with mixed success/failure results"""
        
        urls = [
            "https://www.threads.net/@test1/post/123",  # Success
            "https://invalid-url.com/post/456"          # Failure
        ]
        
        def mock_validator_side_effect(url):
            if "threads.net" in url:
                return {
                    'is_valid': True,
                    'validation_details': {
                        'platform': {
                            'platform': 'threads',
                            'is_supported': True
                        }
                    }
                }
            else:
                return {'is_valid': False, 'error': 'Invalid URL'}
        
        with patch('api.v1.downloads.url_validator.validate_url_format', side_effect=mock_validator_side_effect):
            with patch('api.v1.downloads.ThreadsDownloader') as mock_downloader_class:
                mock_downloader = AsyncMock()
                mock_downloader.__aenter__.return_value = mock_downloader
                mock_downloader.__aexit__.return_value = None
                mock_downloader.extract_content.return_value = {
                    'success': True,
                    'platform': 'threads',
                    'text': 'Test content',
                    'username': 'test_user',
                    'content_type': 'text'
                }
                mock_downloader_class.return_value = mock_downloader
                
                with patch('api.v1.downloads.store_content') as mock_store:
                    mock_post = MagicMock()
                    mock_post.id = 1
                    mock_store.return_value = mock_post
                    
                    with patch('asyncio.sleep'):  # Skip delays in tests
                        response = client.post("/api/v1/downloads/batch", json={
                            "urls": urls,
                            "download_files": False
                        })
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True  # At least one success
                    assert data["data"]["summary"]["total_urls"] == 2
                    assert data["data"]["summary"]["successful"] == 1
                    assert data["data"]["summary"]["failed"] == 1
                    assert data["data"]["summary"]["success_rate"] == 0.5
    
    def test_batch_download_empty_urls(self, client, setup_test_db):
        """Test batch download with empty URLs list"""
        
        response = client.post("/api/v1/downloads/batch", json={
            "urls": [],
            "download_files": False
        })
        
        assert response.status_code == 422  # Pydantic validation error
        assert "ensure this value has at least 1 items" in response.text or "min_length" in response.text
    
    def test_batch_download_too_many_urls(self, client, setup_test_db):
        """Test batch download with too many URLs"""
        
        urls = [f"https://www.threads.net/@test/post/{i}" for i in range(51)]
        
        response = client.post("/api/v1/downloads/batch", json={
            "urls": urls,
            "download_files": False
        })
        
        assert response.status_code == 422  # Pydantic validation error
        assert "ensure this value has at most 50 items" in response.text or "max_length" in response.text
    
    def test_batch_download_duplicate_urls(self, client, setup_test_db):
        """Test batch download with duplicate URLs (should be deduplicated)"""
        
        urls = [
            "https://www.threads.net/@test/post/123",
            "https://www.threads.net/@test/post/123",  # Duplicate
            "https://www.threads.net/@test/post/456"
        ]
        
        with patch('api.v1.downloads.url_validator.validate_url_format') as mock_validator:
            mock_validator.return_value = {
                'is_valid': True,
                'validation_details': {
                    'platform': {
                        'platform': 'threads',
                        'is_supported': True
                    }
                }
            }
            
            with patch('api.v1.downloads.ThreadsDownloader') as mock_downloader_class:
                mock_downloader = AsyncMock()
                mock_downloader.__aenter__.return_value = mock_downloader
                mock_downloader.__aexit__.return_value = None
                mock_downloader.extract_content.return_value = {
                    'success': True,
                    'platform': 'threads',
                    'text': 'Test content',
                    'username': 'test_user',
                    'content_type': 'text'
                }
                mock_downloader_class.return_value = mock_downloader
                
                with patch('api.v1.downloads.store_content') as mock_store:
                    mock_post = MagicMock()
                    mock_post.id = 1
                    mock_store.return_value = mock_post
                    
                    with patch('asyncio.sleep'):  # Skip delays in tests
                        response = client.post("/api/v1/downloads/batch", json={
                            "urls": urls,
                            "download_files": False
                        })
                    
                    assert response.status_code == 200
                    data = response.json()
                    # Should only process 2 unique URLs
                    assert data["data"]["summary"]["total_urls"] == 2
    
    def test_get_supported_platforms(self, client, setup_test_db):
        """Test getting supported platforms information"""
        
        with patch('api.v1.downloads.ThreadsDownloader') as mock_threads:
            mock_downloader = MagicMock()
            mock_downloader.get_platform_domains.return_value = ['threads.net', 'threads.com']
            mock_threads.return_value = mock_downloader
            
            response = client.get("/api/v1/downloads/platforms")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            
            platforms = data["data"]["platforms"]
            assert len(platforms) == 4  # YouTube, Instagram, Threads, RedNote
            
            # Check that Threads platform info is correct
            threads_platform = next(p for p in platforms if p["platform"] == "threads")
            assert threads_platform["is_available"] is True
            assert "threads.net" in threads_platform["supported_domains"]
    
    def test_download_with_files_supported(self, client, setup_test_db):
        """Test download with files when downloader supports it"""
        
        with patch('api.v1.downloads.url_validator.validate_url_format') as mock_validator:
            mock_validator.return_value = {
                'is_valid': True,
                'validation_details': {
                    'platform': {
                        'platform': 'threads',
                        'is_supported': True
                    }
                }
            }
            
            # Create a custom mock class that has download_content
            class MockDownloaderWithDownload:
                def __init__(self):
                    self.download_content = AsyncMock(return_value={
                        'success': True,
                        'platform': 'threads',
                        'url': 'https://www.threads.net/@test/post/123',
                        'text': 'Test content',
                        'username': 'test_user',
                        'content_type': 'text',
                        'downloaded': True
                    })
                
                async def __aenter__(self):
                    return self
                    
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    return None
                    
                async def extract_content(self, url):
                    return {
                        'success': True,
                        'platform': 'threads',
                        'url': url,
                        'text': 'Test content',
                        'username': 'test_user',
                        'content_type': 'text'
                    }
            
            # Patch the PLATFORM_DOWNLOADERS dictionary directly
            with patch('api.v1.downloads.PLATFORM_DOWNLOADERS') as mock_downloaders:
                mock_downloader_instance = MockDownloaderWithDownload()
                mock_downloader_class = MagicMock(return_value=mock_downloader_instance)
                mock_downloaders.get.return_value = mock_downloader_class
                
                with patch('api.v1.downloads.store_content') as mock_store:
                    mock_post = MagicMock()
                    mock_post.id = 1
                    mock_store.return_value = mock_post
                    
                    response = client.post("/api/v1/downloads/single", json={
                        "url": "https://www.threads.net/@test/post/123",
                        "download_files": True
                    })
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    # Should use download_content method
                    mock_downloader_instance.download_content.assert_called_once_with("https://www.threads.net/@test/post/123")
    
    def test_download_with_files_unsupported(self, client, setup_test_db):
        """Test download with files when downloader doesn't support it"""
        
        with patch('api.v1.downloads.url_validator.validate_url_format') as mock_validator:
            mock_validator.return_value = {
                'is_valid': True,
                'validation_details': {
                    'platform': {
                        'platform': 'threads',
                        'is_supported': True
                    }
                }
            }
            
            # Create a custom mock class that doesn't have download_content
            class MockDownloaderWithoutDownload:
                async def __aenter__(self):
                    return self
                    
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    return None
                    
                async def extract_content(self, url):
                    return {
                        'success': True,
                        'platform': 'threads',
                        'url': url,
                        'text': 'Test content',
                        'username': 'test_user',
                        'content_type': 'text'
                    }
            
            # Patch the PLATFORM_DOWNLOADERS dictionary directly
            with patch('api.v1.downloads.PLATFORM_DOWNLOADERS') as mock_downloaders:
                mock_downloader_class = MagicMock(return_value=MockDownloaderWithoutDownload())
                mock_downloaders.get.return_value = mock_downloader_class
                
                with patch('api.v1.downloads.store_content') as mock_store:
                    mock_post = MagicMock()
                    mock_post.id = 1
                    mock_store.return_value = mock_post
                    
                    response = client.post("/api/v1/downloads/single", json={
                        "url": "https://www.threads.net/@test/post/123",
                        "download_files": True
                    })
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    # Should have warning about unsupported file download
                    assert data["data"]["result"]["warning"] is not None
                    assert "not supported" in data["data"]["result"]["warning"]


if __name__ == "__main__":
    pytest.main([__file__]) 