"""
Tests for the storage service that integrates downloaders with database and file system.
"""

import asyncio
import json
import pytest
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.models import Base, Post, MediaFile, PlatformType, ContentType
from db.storage import StorageService, store_content, store_download
from core.config import settings


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def test_db():
    """Create test database"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def storage_service(temp_dir):
    """Create storage service with temporary directory"""
    return StorageService(base_storage_path=temp_dir)


@pytest.fixture
def sample_threads_content():
    """Sample Threads content data"""
    return {
        'url': 'https://www.threads.net/@testuser/post/ABC123',
        'platform': 'threads',
        'content_type': 'text',
        'username': 'testuser',
        'post_id': 'ABC123',
        'text': 'This is a test post with some content',
        'links': [{'url': 'https://example.com', 'text': 'Example'}],
        'mentions': ['@anotheruser'],
        'hashtags': ['#test'],
        'metadata': {'engagement': ['10 likes']},
        'extracted_at': '2024-01-01T12:00:00Z',
        'success': True,
        'error': None
    }


@pytest.fixture
def sample_youtube_content():
    """Sample YouTube content data"""
    return {
        'url': 'https://www.youtube.com/watch?v=test123',
        'platform': 'youtube',
        'content_type': 'video',
        'title': 'Test Video Title',
        'description': 'Test video description',
        'text': 'Video transcript here',
        'author': 'Test Channel',
        'duration': 120,
        'upload_date': '2024-01-01',
        'view_count': 1000,
        'like_count': 100,
        'thumbnail': 'https://img.youtube.com/vi/test123/maxresdefault.jpg',
        'extracted_at': '2024-01-01T12:00:00Z',
        'success': True,
        'error': None
    }


@pytest.fixture
def sample_download_result(temp_dir):
    """Sample download result with files"""
    # Create temporary files
    test_file = Path(temp_dir) / "test_download.json"
    test_file.write_text('{"test": "data"}')
    
    return {
        'url': 'https://www.threads.net/@testuser/post/ABC123',
        'platform': 'threads',
        'content_type': 'text',
        'username': 'testuser',
        'post_id': 'ABC123',
        'text': 'Downloaded content',
        'success': True,
        'downloaded': True,
        'file_path': str(test_file),
        'file_size': test_file.stat().st_size,
        'download_timestamp': '2024-01-01T12:00:00Z'
    }


class TestStorageService:
    """Test cases for StorageService"""
    
    def test_init_creates_directories(self, temp_dir):
        """Test that initialization creates required directories"""
        storage = StorageService(base_storage_path=temp_dir)
        
        base_path = Path(temp_dir)
        assert base_path.exists()
        
        # Check platform directories
        for platform in PlatformType:
            platform_dir = base_path / platform.value
            assert platform_dir.exists()
            
            # Check subdirectories
            for subdir in ['videos', 'images', 'text', 'metadata']:
                assert (platform_dir / subdir).exists()
    
    @pytest.mark.asyncio
    async def test_store_extracted_content_success(self, storage_service, test_db, sample_threads_content):
        """Test successful storage of extracted content"""
        # Store content
        post = await storage_service.store_extracted_content(sample_threads_content, test_db)
        
        # Verify post was created
        assert post is not None
        assert post.url == sample_threads_content['url']
        assert post.platform == PlatformType.THREADS
        assert post.content_type == ContentType.TEXT
        assert post.content_text == sample_threads_content['text']
        assert post.author == sample_threads_content['username']
        assert post.hashtags == sample_threads_content['hashtags']
        assert post.mentions == sample_threads_content['mentions']
        
        # Verify in database
        stored_post = test_db.query(Post).filter(Post.url == sample_threads_content['url']).first()
        assert stored_post is not None
        assert stored_post.id == post.id
    
    @pytest.mark.asyncio
    async def test_store_extracted_content_failed_extraction(self, storage_service, test_db):
        """Test handling of failed extraction"""
        failed_content = {
            'url': 'https://example.com/failed',
            'platform': 'threads',
            'success': False,
            'error': 'Extraction failed'
        }
        
        post = await storage_service.store_extracted_content(failed_content, test_db)
        assert post is None
    
    @pytest.mark.asyncio
    async def test_store_extracted_content_duplicate_url(self, storage_service, test_db, sample_threads_content):
        """Test handling of duplicate URLs"""
        # Store first time
        post1 = await storage_service.store_extracted_content(sample_threads_content, test_db)
        assert post1 is not None
        
        # Try to store again
        post2 = await storage_service.store_extracted_content(sample_threads_content, test_db)
        assert post2 is not None
        assert post2.id == post1.id  # Should return existing post
    
    @pytest.mark.asyncio
    async def test_store_youtube_content(self, storage_service, test_db, sample_youtube_content):
        """Test storing YouTube content with different fields"""
        post = await storage_service.store_extracted_content(sample_youtube_content, test_db)
        
        assert post is not None
        assert post.platform == PlatformType.YOUTUBE
        assert post.content_type == ContentType.VIDEO
        assert post.title == sample_youtube_content['title']
        assert post.description == sample_youtube_content['description']
        assert post.duration == sample_youtube_content['duration']
        assert post.author == sample_youtube_content['author']
    
    @pytest.mark.asyncio
    async def test_store_downloaded_content(self, storage_service, test_db, sample_download_result):
        """Test storing downloaded content with files"""
        post = await storage_service.store_downloaded_content(sample_download_result, test_db)
        
        assert post is not None
        assert post.url == sample_download_result['url']
        
        # Check that files were organized
        media_files = test_db.query(MediaFile).filter(MediaFile.post_id == post.id).all()
        assert len(media_files) == 1
        
        media_file = media_files[0]
        assert 'threads' in media_file.filename
        assert media_file.file_type == 'metadata'
        assert Path(media_file.file_path).exists()
    
    def test_get_platform_storage_path(self, storage_service):
        """Test getting platform storage paths"""
        path = storage_service.get_platform_storage_path(PlatformType.YOUTUBE, 'videos')
        
        assert 'youtube' in str(path)
        assert 'videos' in str(path)
        assert path.exists()
    
    def test_extract_title_from_title_field(self, storage_service):
        """Test title extraction from title field"""
        content = {'title': 'Test Title'}
        title = storage_service._extract_title(content)
        assert title == 'Test Title'
    
    def test_extract_title_from_text(self, storage_service):
        """Test title extraction from text content"""
        content = {'text': 'This is a long text that should be truncated for the title field because it is too long and exceeds the limit'}
        title = storage_service._extract_title(content)
        assert len(title) <= 103  # 100 chars + '...'
        assert title.endswith('...')
    
    def test_extract_title_fallback(self, storage_service):
        """Test title extraction fallback to URL"""
        content = {'url': 'https://example.com/post/123'}
        title = storage_service._extract_title(content)
        assert 'example.com' in title
    
    def test_parse_publish_date_iso_format(self, storage_service):
        """Test parsing ISO format dates"""
        content = {'publish_date': '2024-01-01T12:00:00Z'}
        date = storage_service._parse_publish_date(content)
        assert date is not None
        assert date.year == 2024
    
    def test_parse_publish_date_simple_format(self, storage_service):
        """Test parsing simple date format"""
        content = {'upload_date': '2024-01-01'}
        date = storage_service._parse_publish_date(content)
        assert date is not None
        assert date.year == 2024
    
    def test_parse_publish_date_invalid(self, storage_service):
        """Test handling invalid date formats"""
        content = {'publish_date': 'invalid-date'}
        date = storage_service._parse_publish_date(content)
        assert date is None
    
    def test_detect_file_type(self, storage_service):
        """Test file type detection"""
        assert storage_service._detect_file_type('video.mp4') == 'video'
        assert storage_service._detect_file_type('image.jpg') == 'image'
        assert storage_service._detect_file_type('text.txt') == 'text'
        assert storage_service._detect_file_type('unknown.xyz') == 'unknown'
    
    def test_map_file_type_to_storage(self, storage_service):
        """Test file type to storage directory mapping"""
        assert storage_service._map_file_type_to_storage('video') == 'videos'
        assert storage_service._map_file_type_to_storage('thumbnail') == 'images'
        assert storage_service._map_file_type_to_storage('subtitles') == 'text'
        assert storage_service._map_file_type_to_storage('metadata') == 'metadata'
        assert storage_service._map_file_type_to_storage('unknown') == 'metadata'
    
    def test_get_mime_type(self, storage_service):
        """Test MIME type detection"""
        assert storage_service._get_mime_type('.mp4') == 'video/mp4'
        assert storage_service._get_mime_type('jpg') == 'image/jpeg'
        assert storage_service._get_mime_type('.json') == 'application/json'
        assert storage_service._get_mime_type('.unknown') == 'application/octet-stream'


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    @pytest.mark.asyncio
    async def test_store_content_function(self, sample_threads_content, test_db):
        """Test the store_content convenience function"""
        with patch('db.storage.get_database') as mock_get_db:
            mock_get_db.return_value.__next__ = Mock(return_value=test_db)
            
            post = await store_content(sample_threads_content, test_db)
            assert post is not None
            assert post.url == sample_threads_content['url']
    
    @pytest.mark.asyncio
    async def test_store_download_function(self, sample_download_result, test_db):
        """Test the store_download convenience function"""
        with patch('db.storage.get_database') as mock_get_db:
            mock_get_db.return_value.__next__ = Mock(return_value=test_db)
            
            post = await store_download(sample_download_result, test_db)
            assert post is not None
            assert post.url == sample_download_result['url']


class TestIntegrationWithDownloaders:
    """Integration tests with actual downloader output formats"""
    
    @pytest.mark.asyncio
    async def test_integration_with_threads_downloader_output(self, storage_service, test_db):
        """Test integration with real Threads downloader output format"""
        # Simulate real Threads downloader output
        threads_output = {
            'url': 'https://www.threads.net/@testuser/post/ABC123',
            'platform': 'threads',
            'content_type': 'text',
            'username': 'testuser',
            'post_id': 'ABC123',
            'text': 'Real Threads post content',
            'links': [
                {'url': 'https://help.instagram.com/terms/threads', 'text': 'Terms'},
                {'url': 'https://help.instagram.com/privacy/threads', 'text': 'Privacy'}
            ],
            'mentions': ['@threads', '@instagram'],
            'hashtags': [],
            'metadata': {'engagement': ['5 replies', '12 likes']},
            'extracted_at': '2024-01-01T12:00:00+00:00',
            'success': True,
            'error': None
        }
        
        post = await storage_service.store_extracted_content(threads_output, test_db)
        
        assert post is not None
        assert post.platform == PlatformType.THREADS
        assert post.content_text == 'Real Threads post content'
        assert len(post.mentions) == 2
        assert '@threads' in post.mentions
    
    @pytest.mark.asyncio
    async def test_integration_with_youtube_downloader_output(self, storage_service, test_db):
        """Test integration with real YouTube downloader output format"""
        # Simulate real YouTube downloader output  
        youtube_output = {
            'url': 'https://www.youtube.com/watch?v=test123',
            'platform': 'youtube',
            'content_type': 'video',
            'title': 'Test Video: How to do something',
            'description': 'This is a test video description',
            'view_count': 1000,
            'like_count': 50,
            'duration': 180,
            'upload_date': '2024-01-01',
            'author': 'Test Channel',
            'thumbnail': 'https://img.youtube.com/vi/test123/maxresdefault.jpg',
            'extracted_at': '2024-01-01T12:00:00+00:00',
            'success': True,
            'error': None
        }
        
        post = await storage_service.store_extracted_content(youtube_output, test_db)
        
        assert post is not None
        assert post.platform == PlatformType.YOUTUBE
        assert post.content_type == ContentType.VIDEO
        assert post.title == 'Test Video: How to do something'
        assert post.duration == 180
        assert post.engagement_metrics == {}  # No engagement metrics in this format


if __name__ == '__main__':
    pytest.main([__file__]) 