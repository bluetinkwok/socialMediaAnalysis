"""
Unit tests for RedNote Content Downloader

Tests the RedNote downloader functionality including URL validation,
content extraction, and media downloading with mocked HTTP requests.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path
from datetime import datetime

from services.rednote_downloader import RedNoteDownloader, rednote_downloader
from db.models import PlatformType, ContentType


class TestRedNoteDownloader:
    """Test cases for RedNote downloader functionality."""
    
    @pytest.fixture
    def downloader(self):
        """Create a RedNote downloader instance for testing."""
        return RedNoteDownloader()
    
    def test_validate_url_valid_urls(self, downloader):
        """Test URL validation with valid RedNote URLs."""
        valid_urls = [
            "https://www.xiaohongshu.com/explore/123abc456def",
            "https://xiaohongshu.com/discovery/item/789ghi012jkl",
            "https://xhslink.com/abc123",
            "https://www.xiaohongshu.com/user/profile/user123"
        ]
        
        for url in valid_urls:
            assert downloader.validate_url(url), f"URL should be valid: {url}"
    
    def test_validate_url_invalid_urls(self, downloader):
        """Test URL validation with invalid URLs."""
        invalid_urls = [
            "https://instagram.com/post/123",
            "https://youtube.com/watch?v=123",
            "https://example.com/post/123",
            "not_a_url",
            "",
            "https://xiaohongshu.com/invalid/path"
        ]
        
        for url in invalid_urls:
            assert not downloader.validate_url(url), f"URL should be invalid: {url}"
    
    @pytest.mark.asyncio
    async def test_extract_content_invalid_url(self, downloader):
        """Test content extraction with invalid URL."""
        invalid_url = "https://invalid-site.com/post/123"
        
        with pytest.raises(ValueError, match="Invalid RedNote URL"):
            await downloader.extract_content(invalid_url)
    
    @pytest.mark.asyncio
    @patch('services.rednote_downloader.RedNoteDownloader._extract_with_browser')
    async def test_extract_content_success(self, mock_extract, downloader):
        """Test successful content extraction."""
        # Mock the browser extraction
        mock_content = {
            'url': 'https://www.xiaohongshu.com/explore/123abc',
            'platform': PlatformType.REDNOTE,
            'title': 'Test RedNote Post',
            'description': 'This is a test post description',
            'media_urls': ['https://example.com/image1.jpg'],
            'author': 'test_user',
            'content_type': ContentType.MIXED
        }
        mock_extract.return_value = mock_content
        
        url = "https://www.xiaohongshu.com/explore/123abc"
        result = await downloader.extract_content(url)
        
        assert result == mock_content
        mock_extract.assert_called_once_with(url)
    
    @pytest.mark.asyncio
    @patch('services.rednote_downloader.RedNoteDownloader._extract_with_browser')
    async def test_extract_content_failure(self, mock_extract, downloader):
        """Test content extraction failure."""
        # Mock browser extraction to return None (failure)
        mock_extract.return_value = None
        
        url = "https://www.xiaohongshu.com/explore/123abc"
        
        with pytest.raises(Exception, match="Failed to extract content"):
            await downloader.extract_content(url)
    
    @pytest.mark.asyncio
    async def test_extract_with_browser_success(self, downloader):
        """Test browser-based content extraction."""
        # Mock browser manager and driver directly on the instance
        mock_driver = Mock()
        downloader.browser_manager.get_driver = AsyncMock(return_value=mock_driver)
        downloader.browser_manager.quit = Mock()

        # Mock WebDriverWait and elements
        with patch('services.rednote_downloader.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.return_value = True

            # Mock element extraction methods
            downloader._extract_title = Mock(return_value="Test Title")
            downloader._extract_description = Mock(return_value="Test Description")
            downloader._extract_media_urls = Mock(return_value=["https://example.com/image.jpg"])
            downloader._extract_author = Mock(return_value="test_author")

            url = "https://www.xiaohongshu.com/explore/123abc"
            result = await downloader._extract_with_browser(url)

            assert result is not None
            assert result['url'] == url
            assert result['platform'] == PlatformType.REDNOTE
            assert result['title'] == "Test Title"
            assert result['description'] == "Test Description"
            assert result['media_urls'] == ["https://example.com/image.jpg"]
            assert result['author'] == "test_author"

            # Verify cleanup was called
            downloader.browser_manager.quit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_with_browser_exception(self, downloader):
        """Test browser extraction with exception."""
        # Mock browser manager to raise exception on the instance
        downloader.browser_manager.get_driver = AsyncMock(side_effect=Exception("Browser error"))
        
        url = "https://www.xiaohongshu.com/explore/123abc"
        result = await downloader._extract_with_browser(url)
        
        # Should return fallback data structure instead of None
        assert result is not None
        assert result['url'] == url
        assert result['platform'] == PlatformType.REDNOTE
        assert result['title'] == 'RedNote Post'
        assert result['description'] == '3 秒后将自动返回首页'
        assert result['media_urls'] == []
    
    def test_extract_title(self, downloader):
        """Test title extraction from driver."""
        # Mock driver with title element
        mock_driver = Mock()
        mock_element = Mock()
        mock_element.text.strip.return_value = "Test Post Title"
        mock_driver.find_element.return_value = mock_element
        
        result = downloader._extract_title(mock_driver)
        
        assert result == "Test Post Title"
    
    def test_extract_title_no_element(self, downloader):
        """Test title extraction when no title element found."""
        # Mock driver that raises NoSuchElementException
        mock_driver = Mock()
        from selenium.common.exceptions import NoSuchElementException
        mock_driver.find_element.side_effect = NoSuchElementException()
        
        result = downloader._extract_title(mock_driver)
        
        assert result == "RedNote Post"  # Default title
    
    def test_extract_description(self, downloader):
        """Test description extraction from driver."""
        # Mock driver with description element
        mock_driver = Mock()
        mock_element = Mock()
        mock_element.text.strip.return_value = "This is a test description"
        mock_driver.find_element.return_value = mock_element
        
        result = downloader._extract_description(mock_driver)
        
        assert result == "This is a test description"
    
    def test_extract_media_urls(self, downloader):
        """Test media URL extraction from driver."""
        # Mock driver with image and video elements
        mock_driver = Mock()
        
        # Mock image elements
        mock_img1 = Mock()
        mock_img1.get_attribute.return_value = "https://example.com/image1.jpg"
        mock_img2 = Mock()
        mock_img2.get_attribute.return_value = "https://example.com/image2.jpg"
        
        # Mock video element
        mock_video = Mock()
        mock_video.get_attribute.return_value = "https://example.com/video1.mp4"
        
        mock_driver.find_elements.side_effect = [
            [mock_img1, mock_img2],  # Images
            [mock_video]  # Videos
        ]
        
        result = downloader._extract_media_urls(mock_driver)
        
        expected_urls = [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
            "https://example.com/video1.mp4"
        ]
        assert result == expected_urls
    
    def test_extract_author(self, downloader):
        """Test author extraction from driver."""
        # Mock driver with author element
        mock_driver = Mock()
        mock_element = Mock()
        mock_element.text.strip.return_value = "test_author"
        mock_driver.find_element.return_value = mock_element
        
        result = downloader._extract_author(mock_driver)
        
        assert result == "test_author"
    
    @pytest.mark.asyncio
    @patch('services.rednote_downloader.RedNoteDownloader._make_request')
    async def test_download_media_files_success(self, mock_request, downloader):
        """Test successful media file downloading."""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake_image_data"
        mock_request.return_value = mock_response
        
        # Create temporary download directory
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            download_dir = Path(temp_dir)
            media_urls = ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]
            
            # Mock rate limiter
            downloader.rate_limiter.wait = AsyncMock()
            
            results = await downloader.download_media_files(media_urls, download_dir)
            
            assert len(results) == 2
            for result in results:
                assert result['download_status'] == 'success'
                assert result['file_size'] == len(b"fake_image_data")
                assert Path(result['local_path']).exists()
    
    @pytest.mark.asyncio
    @patch('services.rednote_downloader.RedNoteDownloader._make_request')
    async def test_download_media_files_failure(self, mock_request, downloader):
        """Test media file downloading with HTTP failure."""
        # Mock failed HTTP response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        # Create temporary download directory
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            download_dir = Path(temp_dir)
            media_urls = ["https://example.com/nonexistent.jpg"]
            
            # Mock rate limiter
            downloader.rate_limiter.wait = AsyncMock()
            
            results = await downloader.download_media_files(media_urls, download_dir)
            
            assert len(results) == 1
            assert results[0]['download_status'] == 'failed'
            assert results[0]['local_path'] is None
    
    @pytest.mark.asyncio
    @patch('services.rednote_downloader.RedNoteDownloader._make_request')
    async def test_download_media_files_exception(self, mock_request, downloader):
        """Test media file downloading with exception."""
        # Mock request to raise exception
        mock_request.side_effect = Exception("Network error")
        
        # Create temporary download directory
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            download_dir = Path(temp_dir)
            media_urls = ["https://example.com/image.jpg"]
            
            # Mock rate limiter
            downloader.rate_limiter.wait = AsyncMock()
            
            results = await downloader.download_media_files(media_urls, download_dir)
            
            assert len(results) == 1
            assert results[0]['download_status'] == 'failed'
            assert 'error' in results[0]
    
    def test_global_instance(self):
        """Test that global instance is created correctly."""
        assert rednote_downloader is not None
        assert isinstance(rednote_downloader, RedNoteDownloader)
        assert rednote_downloader.platform == PlatformType.REDNOTE


class TestRedNoteDownloaderIntegration:
    """Integration tests for RedNote downloader."""
    
    @pytest.mark.asyncio
    async def test_full_extraction_workflow(self):
        """Test the complete extraction workflow with mocked components."""
        downloader = RedNoteDownloader()
        
        # Mock all external dependencies
        with patch.multiple(
            downloader,
            validate_url=Mock(return_value=True),
            _extract_with_browser=AsyncMock(return_value={
                'url': 'https://www.xiaohongshu.com/explore/123',
                'platform': PlatformType.REDNOTE,
                'title': 'Integration Test Post',
                'description': 'Test description',
                'media_urls': ['https://example.com/test.jpg'],
                'author': 'test_user',
                'content_type': ContentType.MIXED
            })
        ):
            url = "https://www.xiaohongshu.com/explore/123"
            result = await downloader.extract_content(url)
            
            assert result['title'] == 'Integration Test Post'
            assert result['platform'] == PlatformType.REDNOTE
            assert len(result['media_urls']) == 1
    
    @pytest.mark.asyncio
    async def test_rate_limiting_behavior(self):
        """Test that rate limiting is properly applied."""
        downloader = RedNoteDownloader()
        
        # Mock rate limiter to track calls
        mock_rate_limiter = Mock()
        mock_rate_limiter.wait = AsyncMock()
        downloader.rate_limiter = mock_rate_limiter
        
        # Mock other dependencies
        with patch.multiple(
            downloader,
            validate_url=Mock(return_value=True),
            _extract_with_browser=AsyncMock(return_value={'test': 'data'})
        ):
            await downloader.extract_content("https://www.xiaohongshu.com/explore/123")
            
            # Verify rate limiter was called
            mock_rate_limiter.wait.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__]) 