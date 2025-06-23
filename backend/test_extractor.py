#!/usr/bin/env python3
"""
Test script for the Base Content Extraction Service
"""

import asyncio
import logging
from typing import Dict, List, Any

from services.base_extractor import BaseContentExtractor, ContentExtractionError
from services.rate_limiter import RateLimiter, platform_rate_limiter
from services.browser_manager import BrowserManager
from db.models import PlatformType, ContentType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestExtractor(BaseContentExtractor):
    """Test implementation of BaseContentExtractor"""
    
    def get_platform_domains(self) -> List[str]:
        return ["example.com", "httpbin.org"]
        
    async def extract_content(self, url: str) -> Dict[str, Any]:
        """Test implementation that extracts basic page info"""
        if not self._validate_url(url):
            raise ContentExtractionError(f"Invalid URL for platform: {url}")
            
        try:
            # Make request to get page content
            response = await self._make_request(url, use_browser=False)
            
            if hasattr(response, 'text'):
                html_content = response.text
            else:
                html_content = str(response)
                
            soup = self._parse_html(html_content)
            
            # Extract basic information
            title = self._extract_text_content(soup, ['title', 'h1', 'h2'])
            content = self._extract_text_content(soup, ['p', 'div', 'span'])
            
            return {
                'title': title or 'No title found',
                'content': content or 'No content found',
                'author': 'test_author',
                'author_id': 'test_author_id',
                'publish_date': None,
                'engagement_metrics': self._extract_engagement_metrics(soup),
                'media_urls': [],
                'content_type': self._detect_content_type(soup, url),
                'url': url
            }
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            raise ContentExtractionError(f"Failed to extract content: {str(e)}")
            
    async def extract_bulk_content(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Test implementation for bulk extraction"""
        results = []
        for url in urls:
            try:
                content = await self.extract_content(url)
                results.append(content)
            except Exception as e:
                logger.error(f"Failed to extract content from {url}: {str(e)}")
                results.append({
                    'url': url,
                    'error': str(e),
                    'title': None,
                    'content': None
                })
        return results


async def test_rate_limiter():
    """Test the rate limiter functionality"""
    print("\n=== Testing Rate Limiter ===")
    
    # Test basic rate limiter
    limiter = RateLimiter(delay=0.5, burst_limit=3, window_size=5)
    
    start_time = asyncio.get_event_loop().time()
    
    for i in range(5):
        await limiter.wait()
        current_time = asyncio.get_event_loop().time()
        print(f"Request {i+1} at {current_time - start_time:.2f}s")
        
    print("Rate limiter stats:", limiter.get_stats())
    
    # Test platform rate limiter
    print("\nTesting platform rate limiter...")
    await platform_rate_limiter.wait_for_platform('youtube')
    await platform_rate_limiter.wait_for_platform('instagram')
    
    print("Platform stats:", platform_rate_limiter.get_all_stats())


async def test_browser_manager():
    """Test the browser manager functionality"""
    print("\n=== Testing Browser Manager ===")
    
    try:
        browser = BrowserManager(headless=True)
        print("Browser info:", browser.get_browser_info())
        
        # Test getting page source
        page_source = await browser.get_page_source("https://httpbin.org/html")
        print(f"Page source length: {len(page_source)}")
        print("First 200 chars:", page_source[:200])
        
        browser.quit()
        print("Browser manager test completed successfully")
        
    except Exception as e:
        print(f"Browser manager test failed: {str(e)}")
        print("This is expected if Chrome/Firefox drivers are not installed")


async def test_base_extractor():
    """Test the base content extractor"""
    print("\n=== Testing Base Content Extractor ===")
    
    extractor = TestExtractor(
        platform=PlatformType.YOUTUBE,
        rate_limit_delay=0.5,
        use_browser=False  # Use requests for this test
    )
    
    try:
        # Test connection
        print("Testing connection...")
        can_connect = await extractor.test_connection()
        print(f"Connection test result: {can_connect}")
        
        # Test single URL extraction
        print("\nTesting single URL extraction...")
        test_url = "https://httpbin.org/html"
        
        with extractor:
            content = await extractor.extract_content(test_url)
            print("Extracted content:")
            for key, value in content.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"  {key}: {value[:100]}...")
                else:
                    print(f"  {key}: {value}")
                    
        # Test bulk extraction
        print("\nTesting bulk extraction...")
        test_urls = [
            "https://httpbin.org/html",
            "https://httpbin.org/json"
        ]
        
        with extractor:
            bulk_results = await extractor.extract_bulk_content(test_urls)
            print(f"Bulk extraction completed. Results: {len(bulk_results)} items")
            
        print("Extractor info:", extractor.get_extractor_info())
        
    except Exception as e:
        print(f"Base extractor test failed: {str(e)}")


async def main():
    """Run all tests"""
    print("Starting Base Content Extraction Service Tests")
    print("=" * 50)
    
    # Test individual components
    await test_rate_limiter()
    await test_browser_manager()
    await test_base_extractor()
    
    print("\n" + "=" * 50)
    print("All tests completed!")


if __name__ == "__main__":
    asyncio.run(main()) 