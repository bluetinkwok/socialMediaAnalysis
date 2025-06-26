"""
Test suite for Instagram Content Downloader
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path
from datetime import datetime

from services.instagram_downloader import InstagramDownloader, create_instagram_downloader


class TestInstagramDownloader:
    """Test Instagram downloader functionality"""
    
    @pytest.fixture
    def downloader(self):
        """Create Instagram downloader instance for testing"""
        return InstagramDownloader(download_dir="test_downloads", rate_limit=0.1)
    
    def test_initialization(self, downloader):
        """Test Instagram downloader initialization"""
        assert downloader.download_dir == "test_downloads"
        assert downloader.rate_limiter is not None
        assert downloader.scraper is None
        assert 'instagram.com' in downloader.SUPPORTED_DOMAINS
    
    def test_initialization_without_instaloader(self):
        """Test initialization when instaloader is not available"""
        with patch('services.instagram_downloader.instaloader', None):
            downloader = InstagramDownloader()
            assert downloader.loader is None
    
    def test_validate_url_valid_post(self, downloader):
        """Test URL validation for valid Instagram post URLs"""
        valid_urls = [
            "https://www.instagram.com/p/ABC123/",
            "https://instagram.com/p/DEF456",
            "https://m.instagram.com/p/GHI789/",
            "http://www.instagram.com/p/JKL012"
        ]
        
        for url in valid_urls:
            assert downloader.validate_url(url) == True
    
    def test_validate_url_valid_reel(self, downloader):
        """Test URL validation for valid Instagram reel URLs"""
        valid_urls = [
            "https://www.instagram.com/reel/ABC123/",
            "https://instagram.com/reel/DEF456",
            "https://m.instagram.com/reel/GHI789/"
        ]
        
        for url in valid_urls:
            assert downloader.validate_url(url) == True
    
    def test_validate_url_valid_tv(self, downloader):
        """Test URL validation for valid Instagram TV URLs"""
        valid_urls = [
            "https://www.instagram.com/tv/ABC123/",
            "https://instagram.com/tv/DEF456"
        ]
        
        for url in valid_urls:
            assert downloader.validate_url(url) == True
    
    def test_validate_url_valid_profile(self, downloader):
        """Test URL validation for valid Instagram profile URLs"""
        valid_urls = [
            "https://www.instagram.com/testuser/",
            "https://instagram.com/testuser",
            "https://www.instagram.com/test.user",
            "https://www.instagram.com/test_user"
        ]
        
        for url in valid_urls:
            assert downloader.validate_url(url) == True
    
    def test_validate_url_invalid(self, downloader):
        """Test URL validation for invalid URLs"""
        invalid_urls = [
            "https://youtube.com/watch?v=123",
            "https://facebook.com/post/123",
            "https://twitter.com/user/status/123",
            "not_a_url",
            "https://instagram.com/invalid/path/structure",
            "https://www.instagram.com/"  # Root URL without content
        ]
        
        for url in invalid_urls:
            assert downloader.validate_url(url) == False
    
    def test_extract_shortcode_from_url(self, downloader):
        """Test shortcode extraction from various URL formats"""
        test_cases = [
            ("https://www.instagram.com/p/ABC123/", "ABC123"),
            ("https://instagram.com/reel/DEF456", "DEF456"),
            ("https://www.instagram.com/tv/GHI789/", "GHI789"),
            ("https://www.instagram.com/testuser/", None),
            ("invalid_url", None)
        ]
        
        for url, expected in test_cases:
            result = downloader._extract_shortcode_from_url(url)
            assert result == expected
    
    def test_get_download_directory(self, downloader):
        """Test download directory generation"""
        url = "https://www.instagram.com/p/ABC123/"
        result = downloader._get_download_directory(url)
        
        today = datetime.now().strftime("%Y-%m-%d")
        expected = Path("test_downloads") / "instagram" / today / "ABC123"
        
        assert result == expected
    
    @pytest.mark.asyncio
    async def test_extract_content_with_instaloader(self, downloader):
        """Test content extraction using instaloader"""
        url = "https://www.instagram.com/p/ABC123/"
        
        # Mock instaloader components
        mock_post = Mock()
        mock_post.caption = "Test caption"
        mock_post.owner_username = "testuser"
        mock_post.date_utc = datetime(2024, 1, 1)
        mock_post.likes = 100
        mock_post.comments = 10
        mock_post.is_video = False
        mock_post.video_view_count = None
        mock_post.video_duration = None
        mock_post.url = "https://example.com/image.jpg"
        mock_post.video_url = None
        mock_post.caption_hashtags = ["test", "instagram"]
        mock_post.caption_mentions = ["@testuser"]
        mock_post.location = None
        
        with patch('services.instagram_downloader.instaloader') as mock_instaloader:
            mock_instaloader.Post.from_shortcode.return_value = mock_post
            downloader.loader = Mock()
            downloader.loader.context = Mock()
            
            result = await downloader.extract_content(url)
            
            assert result['url'] == url
            assert result['shortcode'] == "ABC123"
            assert result['title'] == "Test caption"
            assert result['author'] == "testuser"
            assert result['like_count'] == 100
            assert result['is_video'] == False
    
    @pytest.mark.asyncio
    async def test_extract_content_with_scraping_fallback(self, downloader):
        """Test content extraction using scraping fallback"""
        url = "https://www.instagram.com/p/ABC123/"
        
        # Set loader to None to trigger scraping
        downloader.loader = None
        
        # Mock scraper
        mock_scraper = AsyncMock()
        mock_scraper.navigate_to = AsyncMock()
        mock_scraper.get_text = AsyncMock()
        mock_scraper.get_text.side_effect = [
            "Test Title",  # og:title
            "Test Description",  # og:description
            "https://example.com/image.jpg"  # og:image
        ]
        
        with patch('services.instagram_downloader.create_stealth_scraper', return_value=mock_scraper):
            result = await downloader.extract_content(url)
            
            assert result['url'] == url
            assert result['shortcode'] == "ABC123"
            assert result['title'] == "Test Title"
            assert result['description'] == "Test Description"
            assert result['extraction_method'] == 'scraping'
    
    @pytest.mark.asyncio
    async def test_extract_content_invalid_url(self, downloader):
        """Test content extraction with invalid URL"""
        url = "https://youtube.com/watch?v=123"
        
        with pytest.raises(ValueError, match="Invalid Instagram URL"):
            await downloader.extract_content(url)
    
    @pytest.mark.asyncio
    async def test_download_content_with_instaloader(self, downloader):
        """Test content download using instaloader"""
        url = "https://www.instagram.com/p/ABC123/"
        
        # Mock content extraction
        mock_content_info = {
            'url': url,
            'shortcode': 'ABC123',
            'title': 'Test content',
            'author': 'testuser'
        }
        
        # Mock post and loader
        mock_post = Mock()
        mock_loader = Mock()
        mock_loader.dirname_pattern = "{target}"
        mock_loader.download_post = Mock()
        
        downloader.loader = mock_loader
        
        with patch.object(downloader, 'extract_content', return_value=mock_content_info), \
             patch('services.instagram_downloader.instaloader') as mock_instaloader, \
             patch('pathlib.Path.mkdir'), \
             patch('builtins.open', create=True) as mock_open, \
             patch('json.dump'):
            
            mock_instaloader.Post.from_shortcode.return_value = mock_post
            
            result = await downloader.download_content(url)
            
            assert result['download_status'] == 'success'
            assert 'download_path' in result
            mock_loader.download_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_download_content_with_scraping_fallback(self, downloader):
        """Test content download using scraping fallback"""
        url = "https://www.instagram.com/p/ABC123/"
        
        # Mock content extraction
        mock_content_info = {
            'url': url,
            'shortcode': 'ABC123',
            'title': 'Test content'
        }
        
        # Set loader to None to trigger scraping fallback
        downloader.loader = None
        
        with patch.object(downloader, 'extract_content', return_value=mock_content_info), \
             patch('pathlib.Path.mkdir'), \
             patch('builtins.open', create=True), \
             patch('json.dump'):
            
            result = await downloader.download_content(url)
            
            assert result['download_status'] == 'metadata_only'
            assert 'note' in result
    
    @pytest.mark.asyncio
    async def test_extract_bulk_content(self, downloader):
        """Test bulk content extraction"""
        urls = [
            "https://www.instagram.com/p/ABC123/",
            "https://www.instagram.com/p/DEF456/",
            "https://invalid.com/url"
        ]
        
        # Mock successful extraction for first two URLs
        mock_results = [
            {'url': urls[0], 'title': 'Test 1'},
            {'url': urls[1], 'title': 'Test 2'}
        ]
        
        extract_calls = []
        async def mock_extract(url):
            if url in urls[:2]:
                return mock_results[urls.index(url)]
            else:
                raise ValueError("Invalid URL")
        
        with patch.object(downloader, 'extract_content', side_effect=mock_extract):
            results = await downloader.extract_bulk_content(urls)
            
            assert len(results) == 3
            assert results[0]['title'] == 'Test 1'
            assert results[1]['title'] == 'Test 2'
            assert results[2]['error'] is not None
            assert results[2]['status'] == 'failed'
    
    @pytest.mark.asyncio
    async def test_cleanup(self, downloader):
        """Test cleanup functionality"""
        # Mock scraper
        mock_scraper = AsyncMock()
        mock_scraper.cleanup = AsyncMock()
        downloader.scraper = mock_scraper
        
        await downloader.cleanup()
        
        mock_scraper.cleanup.assert_called_once()
        assert downloader.scraper is None
    
    def test_create_instagram_downloader_function(self):
        """Test utility function for creating downloader"""
        downloader = create_instagram_downloader(download_dir="custom_dir", rate_limit=5.0)
        
        assert isinstance(downloader, InstagramDownloader)
        assert downloader.download_dir == "custom_dir"


class TestInstagramDownloaderIntegration:
    """Integration tests for Instagram downloader"""
    
    @pytest.mark.asyncio
    async def test_real_url_validation(self):
        """Test validation with real Instagram URLs (no network calls)"""
        downloader = InstagramDownloader()
        
        # These should validate without making network calls
        real_urls = [
            "https://www.instagram.com/p/CwHhPMZOabc/",  # Example post format
            "https://www.instagram.com/reel/CxYzABC123/",  # Example reel format
            "https://www.instagram.com/natgeo/"  # Example profile
        ]
        
        for url in real_urls:
            assert downloader.validate_url(url) == True
    
    @pytest.mark.asyncio
    async def test_error_handling_with_invalid_shortcode(self):
        """Test error handling with invalid shortcode"""
        downloader = InstagramDownloader()
        url = "https://www.instagram.com/p/INVALID_SHORTCODE/"
        
        if downloader.loader:
            # Mock instaloader to raise exception
            with patch('services.instagram_downloader.instaloader.Post.from_shortcode', 
                      side_effect=Exception("Invalid shortcode")):
                
                with pytest.raises(Exception):
                    await downloader.extract_content(url)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 