"""
Base Content Extractor - Core web scraping functionality for social media platforms
"""

import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse, urljoin
from datetime import datetime, timedelta

import aiohttp
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import TimeoutException, WebDriverException

from .browser_manager import BrowserManager
from .rate_limiter import RateLimiter
from db.models import PlatformType, ContentType

logger = logging.getLogger(__name__)


class ContentExtractionError(Exception):
    """Custom exception for content extraction errors"""
    pass


class BaseContentExtractor(ABC):
    """
    Abstract base class for content extraction from social media platforms.
    Provides common functionality for web scraping with anti-detection measures.
    """
    
    def __init__(
        self,
        platform: PlatformType,
        rate_limit_delay: float = 2.0,
        max_retries: int = 3,
        timeout: int = 30,
        use_browser: bool = True
    ):
        self.platform = platform
        self.rate_limiter = RateLimiter(delay=rate_limit_delay)
        self.browser_manager = BrowserManager() if use_browser else None
        self.max_retries = max_retries
        self.timeout = timeout
        self.session = None
        
        # User agents for rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ]
        
    def __enter__(self):
        self._initialize_session()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup()
        
    def _initialize_session(self):
        """Initialize HTTP session with headers and configuration"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def _cleanup(self):
        """Clean up resources"""
        if self.session:
            self.session.close()
        if self.browser_manager:
            self.browser_manager.quit()
            
    def _get_random_delay(self, base_delay: float = None) -> float:
        """Get a random delay to avoid detection"""
        if base_delay is None:
            base_delay = self.rate_limiter.delay
        return base_delay + random.uniform(0.5, 2.0)
        
    async def _make_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict] = None,
        data: Optional[Dict] = None,
        use_browser: bool = False
    ) -> Union[requests.Response, str]:
        """
        Make HTTP request with rate limiting and retry logic
        """
        await self.rate_limiter.wait()
        
        for attempt in range(self.max_retries):
            try:
                if use_browser and self.browser_manager:
                    return await self._browser_request(url)
                else:
                    return await self._session_request(url, method, headers, data)
                    
            except Exception as e:
                logger.warning(f"Request attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt < self.max_retries - 1:
                    delay = self._get_random_delay(2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    raise ContentExtractionError(f"Failed to fetch {url} after {self.max_retries} attempts: {str(e)}")
                    
    async def _session_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> requests.Response:
        """Make request using requests session"""
        if not self.session:
            self._initialize_session()
            
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
            
        # Rotate user agent occasionally
        if random.random() < 0.3:
            request_headers['User-Agent'] = random.choice(self.user_agents)
            
        response = self.session.request(
            method=method,
            url=url,
            headers=request_headers,
            data=data,
            timeout=self.timeout,
            allow_redirects=True
        )
        response.raise_for_status()
        return response
        
    async def _browser_request(self, url: str) -> str:
        """Make request using browser automation"""
        if not self.browser_manager:
            raise ContentExtractionError("Browser manager not initialized")
            
        driver = await self.browser_manager.get_driver()
        
        try:
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Random scroll to simulate human behavior
            if random.random() < 0.5:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
                await asyncio.sleep(random.uniform(1, 3))
                
            return driver.page_source
            
        except TimeoutException:
            raise ContentExtractionError(f"Page load timeout for {url}")
        except WebDriverException as e:
            raise ContentExtractionError(f"Browser error for {url}: {str(e)}")
            
    def _parse_html(self, html_content: str) -> BeautifulSoup:
        """Parse HTML content using BeautifulSoup"""
        return BeautifulSoup(html_content, 'html.parser')
        
    def _extract_text_content(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
        """Extract text content using CSS selectors"""
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return None
        
    def _extract_all_text_content(self, soup: BeautifulSoup, selectors: List[str]) -> List[str]:
        """Extract all text content using CSS selectors"""
        results = []
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text:
                    results.append(text)
        return results
        
    def _extract_attribute(self, soup: BeautifulSoup, selector: str, attribute: str) -> Optional[str]:
        """Extract attribute value using CSS selector"""
        element = soup.select_one(selector)
        if element:
            return element.get(attribute)
        return None
        
    def _extract_all_attributes(self, soup: BeautifulSoup, selector: str, attribute: str) -> List[str]:
        """Extract all attribute values using CSS selector"""
        elements = soup.select(selector)
        return [elem.get(attribute) for elem in elements if elem.get(attribute)]
        
    def _clean_url(self, url: str, base_url: str = None) -> str:
        """Clean and normalize URL"""
        if not url:
            return ""
            
        # Handle relative URLs
        if base_url and not url.startswith(('http://', 'https://')):
            url = urljoin(base_url, url)
            
        # Remove tracking parameters
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
    def _extract_engagement_metrics(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract engagement metrics (likes, comments, shares, views)"""
        metrics = {
            'likes': 0,
            'comments': 0,
            'shares': 0,
            'views': 0
        }
        
        # This is platform-specific and should be overridden in subclasses
        return metrics
        
    def _detect_content_type(self, soup: BeautifulSoup, url: str) -> ContentType:
        """Detect content type based on HTML content and URL"""
        # Check for video indicators
        if soup.find('video') or 'video' in url.lower():
            return ContentType.VIDEO
            
        # Check for image indicators
        if soup.find('img') or 'photo' in url.lower() or 'image' in url.lower():
            return ContentType.IMAGE
            
        # Default to text
        return ContentType.TEXT
        
    def _validate_url(self, url: str) -> bool:
        """Validate if URL belongs to the platform"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower() in self.get_platform_domains()
        except Exception:
            return False
            
    @abstractmethod
    def get_platform_domains(self) -> List[str]:
        """Return list of valid domains for this platform"""
        pass
        
    @abstractmethod
    async def extract_content(self, url: str) -> Dict[str, Any]:
        """
        Extract content from a given URL.
        Must be implemented by platform-specific extractors.
        
        Returns:
            Dict containing extracted content with keys:
            - title: str
            - content: str
            - author: str
            - author_id: str
            - publish_date: datetime
            - engagement_metrics: dict
            - media_urls: list
            - content_type: ContentType
        """
        pass
        
    @abstractmethod
    async def extract_bulk_content(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Extract content from multiple URLs.
        Must be implemented by platform-specific extractors.
        """
        pass
        
    async def test_connection(self) -> bool:
        """Test if the extractor can connect to the platform"""
        try:
            domains = self.get_platform_domains()
            if not domains:
                return False
                
            test_url = f"https://{domains[0]}"
            response = await self._make_request(test_url)
            return True
        except Exception as e:
            logger.error(f"Connection test failed for {self.platform.value}: {str(e)}")
            return False
            
    def get_extractor_info(self) -> Dict[str, Any]:
        """Get information about this extractor"""
        return {
            'platform': self.platform.value,
            'rate_limit_delay': self.rate_limiter.delay,
            'max_retries': self.max_retries,
            'timeout': self.timeout,
            'uses_browser': self.browser_manager is not None,
            'supported_domains': self.get_platform_domains()
        } 