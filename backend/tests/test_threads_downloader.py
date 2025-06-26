"""
Unit tests for Threads Content Downloader
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from pathlib import Path

from services.threads_downloader import ThreadsDownloader, extract_threads_content, download_threads_content
from services.base_extractor import ContentExtractionError
from db.models import PlatformType, ContentType


class TestThreadsDownloader:
    """Test suite for ThreadsDownloader class"""
    
    @pytest.fixture
    def downloader(self):
        """Create a ThreadsDownloader instance for testing"""
        return ThreadsDownloader(rate_limit_delay=0.1, timeout=5)
        
    @pytest.fixture
    def mock_browser_response(self):
        """Mock HTML response from Threads"""
        return """
        <html>
            <body>
                <div data-testid="post">
                    <div data-testid="post-text">
                        This is a test post with @username mention and #hashtag.
                        Check out this link: https://example.com
                    </div>
                    <time>2024-01-15T10:30:00Z</time>
                    <span class="author">testuser</span>
                    <div class="engagement">
                        <span class="count">42 likes</span>
                        <span class="count">5 replies</span>
                    </div>
                    <a href="https://example.com">External Link</a>
                    <a href="/@username">@username</a>
                    <a href="/hashtag/test">#hashtag</a>
                </div>
            </body>
        </html>
        """
        
    def test_init(self, downloader):
        """Test ThreadsDownloader initialization"""
        assert downloader.platform == PlatformType.THREADS
        assert downloader.rate_limiter.delay == 0.1
        assert downloader.timeout == 5
        assert downloader.browser_manager is not None
        
        # Check selectors are properly configured
        assert 'post_container' in downloader.selectors
        assert 'post_text' in downloader.selectors
        assert 'post_links' in downloader.selectors
        
        # Check URL patterns
        assert 'post' in downloader.url_patterns
        assert 'profile' in downloader.url_patterns
        
    def test_get_platform_domains(self, downloader):
        """Test platform domains"""
        domains = downloader.get_platform_domains()
        assert 'threads.net' in domains
        assert 'www.threads.net' in domains
        
    def test_validate_threads_url_post(self, downloader):
        """Test URL validation for post URLs"""
        url = "https://www.threads.net/@testuser/post/12345"
        result = downloader._validate_threads_url(url)
        
        assert result['url_type'] == 'post'
        assert result['username'] == 'testuser'
        assert result['post_id'] == '12345'
        assert result['original_url'] == url
        
    def test_validate_threads_url_profile(self, downloader):
        """Test URL validation for profile URLs"""
        url = "https://www.threads.net/@testuser"
        result = downloader._validate_threads_url(url)
        
        assert result['url_type'] == 'profile'
        assert result['username'] == 'testuser'
        assert result['post_id'] is None
        
    def test_validate_threads_url_invalid(self, downloader):
        """Test URL validation for invalid URLs"""
        invalid_urls = [
            "https://instagram.com/p/12345",
            "https://threads.net/invalid",
            "not-a-url",
            "",
            "https://example.com"
        ]
        
        for url in invalid_urls:
            with pytest.raises(ContentExtractionError):
                downloader._validate_threads_url(url)
                
    def test_extract_post_text(self, downloader, mock_browser_response):
        """Test post text extraction"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(mock_browser_response, 'html.parser')
        
        text = downloader._extract_post_text(soup)
        
        assert "This is a test post" in text
        assert "@username" in text
        assert "#hashtag" in text
        assert "https://example.com" in text
        
    def test_extract_links(self, downloader, mock_browser_response):
        """Test link extraction"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(mock_browser_response, 'html.parser')
        
        links = downloader._extract_links(soup, "https://www.threads.net")
        
        assert len(links) >= 1
        assert any(link['url'] == 'https://example.com' for link in links)
        
        # Check link structure
        for link in links:
            assert 'url' in link
            assert 'text' in link
            assert 'title' in link
            
    def test_extract_mentions(self, downloader, mock_browser_response):
        """Test mention extraction"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(mock_browser_response, 'html.parser')
        
        mentions = downloader._extract_mentions(soup)
        
        assert 'username' in mentions
        
    def test_extract_hashtags(self, downloader, mock_browser_response):
        """Test hashtag extraction"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(mock_browser_response, 'html.parser')
        
        hashtags = downloader._extract_hashtags(soup)
        
        assert 'hashtag' in hashtags or 'test' in hashtags
        
    def test_extract_metadata(self, downloader, mock_browser_response):
        """Test metadata extraction"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(mock_browser_response, 'html.parser')
        
        metadata = downloader._extract_metadata(soup)
        
        # Check for timestamp
        if 'timestamp' in metadata:
            assert metadata['timestamp'] is not None
            
        # Check for author
        if 'author' in metadata:
            assert metadata['author'] is not None
            
        # Check for engagement
        if 'engagement' in metadata:
            assert isinstance(metadata['engagement'], list)
            
    @pytest.mark.asyncio
    async def test_extract_content_success(self, downloader, mock_browser_response):
        """Test successful content extraction"""
        url = "https://www.threads.net/@testuser/post/12345"
        
        with patch.object(downloader, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_browser_response
            
            result = await downloader.extract_content(url)
            
            assert result['success'] is True
            assert result['url'] == url
            assert result['platform'] == PlatformType.THREADS.value
            assert result['content_type'] == ContentType.TEXT.value
            assert result['username'] == 'testuser'
            assert result['post_id'] == '12345'
            assert result['text'] is not None
            assert isinstance(result['links'], list)
            assert isinstance(result['mentions'], list)
            assert isinstance(result['hashtags'], list)
            assert isinstance(result['metadata'], dict)
            assert result['error'] is None
            
    @pytest.mark.asyncio
    async def test_extract_content_profile_url_error(self, downloader):
        """Test content extraction with profile URL (should fail)"""
        url = "https://www.threads.net/@testuser"
        
        result = await downloader.extract_content(url)
        
        assert result['success'] is False
        assert "Only post URLs are supported" in result['error']
        
    @pytest.mark.asyncio
    async def test_extract_content_request_failure(self, downloader):
        """Test content extraction with request failure"""
        url = "https://www.threads.net/@testuser/post/12345"
        
        with patch.object(downloader, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = ContentExtractionError("Network error")
            
            result = await downloader.extract_content(url)
            
            assert result['success'] is False
            assert "Network error" in result['error']
            
    @pytest.mark.asyncio
    async def test_extract_bulk_content(self, downloader, mock_browser_response):
        """Test bulk content extraction"""
        urls = [
            "https://www.threads.net/@user1/post/123",
            "https://www.threads.net/@user2/post/456"
        ]
        
        with patch.object(downloader, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_browser_response
            
            results = await downloader.extract_bulk_content(urls)
            
            assert len(results) == 2
            for result in results:
                assert 'url' in result
                assert 'success' in result
                
    @pytest.mark.asyncio
    async def test_download_content_success(self, downloader, mock_browser_response, tmp_path):
        """Test successful content download"""
        url = "https://www.threads.net/@testuser/post/12345"
        output_dir = str(tmp_path)
        
        with patch.object(downloader, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_browser_response
            
            result = await downloader.download_content(url, output_dir)
            
            assert result['success'] is True
            assert result['downloaded'] is True
            assert 'file_path' in result
            assert 'file_size' in result
            assert 'download_timestamp' in result
            
            # Check file was created
            file_path = Path(result['file_path'])
            assert file_path.exists()
            
            # Check file content
            with open(file_path, 'r', encoding='utf-8') as f:
                saved_content = json.load(f)
                assert saved_content['url'] == url
                assert saved_content['username'] == 'testuser'
                
    @pytest.mark.asyncio
    async def test_download_content_extraction_failure(self, downloader, tmp_path):
        """Test content download when extraction fails"""
        url = "https://www.threads.net/@testuser/post/12345"
        output_dir = str(tmp_path)
        
        with patch.object(downloader, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = ContentExtractionError("Extraction failed")
            
            result = await downloader.download_content(url, output_dir)
            
            assert result['success'] is False
            assert result['downloaded'] is False
            assert "Extraction failed" in result['error']
            
    def test_url_patterns_post(self, downloader):
        """Test URL pattern matching for posts"""
        test_urls = [
            "https://www.threads.net/@username/post/ABC123",
            "https://threads.net/@user.name/post/xyz789",
            "http://www.threads.net/@test_user/post/123abc"
        ]
        
        for url in test_urls:
            match = downloader.url_patterns['post'].match(url)
            assert match is not None
            assert len(match.groups()) == 2  # username and post_id
            
    def test_url_patterns_profile(self, downloader):
        """Test URL pattern matching for profiles"""
        test_urls = [
            "https://www.threads.net/@username",
            "https://threads.net/@user.name/",
            "http://www.threads.net/@test_user"
        ]
        
        for url in test_urls:
            match = downloader.url_patterns['profile'].match(url)
            assert match is not None
            assert len(match.groups()) == 1  # username only
            
    def test_selectors_structure(self, downloader):
        """Test that all required selectors are present"""
        required_selectors = [
            'post_container', 'post_text', 'post_links',
            'mentions', 'hashtags', 'engagement',
            'timestamp', 'author'
        ]
        
        for selector_type in required_selectors:
            assert selector_type in downloader.selectors
            assert isinstance(downloader.selectors[selector_type], list)
            assert len(downloader.selectors[selector_type]) > 0
            
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_browser_response):
        """Test ThreadsDownloader as context manager"""
        url = "https://www.threads.net/@testuser/post/12345"
        
        async with ThreadsDownloader(rate_limit_delay=0.1) as downloader:
            with patch.object(downloader, '_make_request', new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_browser_response
                
                result = await downloader.extract_content(url)
                assert result['success'] is True
                
    def test_extract_post_text_empty_content(self, downloader):
        """Test post text extraction with empty content"""
        from bs4 import BeautifulSoup
        empty_html = "<html><body></body></html>"
        soup = BeautifulSoup(empty_html, 'html.parser')
        
        text = downloader._extract_post_text(soup)
        assert text == ""
        
    def test_extract_links_no_links(self, downloader):
        """Test link extraction with no links"""
        from bs4 import BeautifulSoup
        no_links_html = "<html><body><div>No links here</div></body></html>"
        soup = BeautifulSoup(no_links_html, 'html.parser')
        
        links = downloader._extract_links(soup, "https://www.threads.net")
        assert links == []
        
    def test_extract_mentions_no_mentions(self, downloader):
        """Test mention extraction with no mentions"""
        from bs4 import BeautifulSoup
        no_mentions_html = "<html><body><div>No mentions here</div></body></html>"
        soup = BeautifulSoup(no_mentions_html, 'html.parser')
        
        mentions = downloader._extract_mentions(soup)
        assert mentions == []
        
    def test_extract_hashtags_no_hashtags(self, downloader):
        """Test hashtag extraction with no hashtags"""
        from bs4 import BeautifulSoup
        no_hashtags_html = "<html><body><div>No hashtags here</div></body></html>"
        soup = BeautifulSoup(no_hashtags_html, 'html.parser')
        
        hashtags = downloader._extract_hashtags(soup)
        assert hashtags == []


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    @pytest.mark.asyncio
    async def test_extract_threads_content(self):
        """Test extract_threads_content convenience function"""
        url = "https://www.threads.net/@testuser/post/12345"
        mock_response = "<html><body><div data-testid='post'>Test post</div></body></html>"
        
        with patch('services.threads_downloader.ThreadsDownloader') as MockDownloader:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.extract_content.return_value = {'success': True, 'text': 'Test post'}
            MockDownloader.return_value = mock_instance
            
            result = await extract_threads_content(url)
            
            assert result['success'] is True
            assert result['text'] == 'Test post'
            
    @pytest.mark.asyncio
    async def test_download_threads_content(self):
        """Test download_threads_content convenience function"""
        url = "https://www.threads.net/@testuser/post/12345"
        output_dir = "test_downloads"
        
        with patch('services.threads_downloader.ThreadsDownloader') as MockDownloader:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.download_content.return_value = {
                'success': True, 
                'downloaded': True,
                'file_path': 'test_downloads/threads_testuser_12345.json'
            }
            MockDownloader.return_value = mock_instance
            
            result = await download_threads_content(url, output_dir)
            
            assert result['success'] is True
            assert result['downloaded'] is True
            assert 'file_path' in result


if __name__ == "__main__":
    pytest.main([__file__]) 