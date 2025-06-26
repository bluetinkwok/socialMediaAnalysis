"""
Threads Content Downloader - Extract text content and links from Threads posts
"""

import asyncio
import logging
import re
import time
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

from .base_extractor import BaseContentExtractor, ContentExtractionError
from db.models import PlatformType, ContentType

logger = logging.getLogger(__name__)


class ThreadsDownloader(BaseContentExtractor):
    """
    Threads content downloader for extracting text posts, mentions, hashtags, and links.
    Handles dynamic content loading and anti-detection measures.
    """
    
    def __init__(self, rate_limit_delay: float = 3.0, **kwargs):
        # Threads requires browser for dynamic content
        super().__init__(
            platform=PlatformType.THREADS,
            rate_limit_delay=rate_limit_delay,
            use_browser=True,
            **kwargs
        )
        
        # Threads-specific selectors (may need updates as platform evolves)
        self.selectors = {
            'post_container': [
                'div[data-testid="post"]',
                'article[role="article"]',
                'div[class*="post"]',
                'div[class*="thread"]'
            ],
            'post_text': [
                'div[data-testid="post-text"]',
                'div[class*="text-content"]',
                'div[class*="post-body"]',
                'span[class*="text"]',
                'p[class*="text"]'
            ],
            'post_links': [
                'a[href*="http"]',
                'a[class*="link"]'
            ],
            'mentions': [
                'a[href*="/@"]',
                'span[class*="mention"]'
            ],
            'hashtags': [
                'a[href*="/hashtag"]',
                'span[class*="hashtag"]'
            ],
            'engagement': [
                'div[class*="engagement"]',
                'div[class*="metrics"]',
                'span[class*="count"]'
            ],
            'timestamp': [
                'time',
                'span[class*="time"]',
                'div[class*="timestamp"]'
            ],
            'author': [
                'div[class*="author"]',
                'span[class*="username"]',
                'a[class*="profile"]'
            ]
        }
        
        # Common Threads URL patterns (support both .net and .com domains)
        self.url_patterns = {
            'post': re.compile(r'https?://(?:www\.)?threads\.(?:net|com)/@([^/]+)/post/([^/?&\s]+)'),
            'profile': re.compile(r'https?://(?:www\.)?threads\.(?:net|com)/@([^/?&\s]+)/?(?:\?.*)?$')
        }
        
    async def __aenter__(self):
        """Async context manager entry"""
        self._initialize_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self._cleanup()
        
    def get_platform_domains(self) -> List[str]:
        """Return supported Threads domains"""
        return ['threads.net', 'www.threads.net', 'threads.com', 'www.threads.com']
        
    def _validate_threads_url(self, url: str) -> Dict[str, str]:
        """
        Validate and parse Threads URL
        
        Returns:
            Dict with url_type, username, and post_id (if applicable)
        """
        if not self._validate_url(url):
            raise ContentExtractionError(f"Invalid URL format: {url}")
            
        # Check for post URL
        post_match = self.url_patterns['post'].match(url)
        if post_match:
            return {
                'url_type': 'post',
                'username': post_match.group(1),
                'post_id': post_match.group(2),
                'original_url': url
            }
            
        # Check for profile URL
        profile_match = self.url_patterns['profile'].match(url)
        if profile_match:
            return {
                'url_type': 'profile',
                'username': profile_match.group(1),
                'post_id': None,
                'original_url': url
            }
            
        raise ContentExtractionError(f"Unsupported Threads URL pattern: {url}")
        
    async def _wait_for_content(self, driver, timeout: int = 15) -> None:
        """Wait for Threads content to load"""
        try:
            # Wait for any of the post container selectors
            wait = WebDriverWait(driver, timeout)
            
            # Try multiple selectors in order of preference
            for selector in self.selectors['post_container']:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    logger.debug(f"Found content with selector: {selector}")
                    return
                except TimeoutException:
                    continue
                    
            # If no post container found, wait for body and hope for the best
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
        except TimeoutException:
            raise ContentExtractionError("Timeout waiting for Threads content to load")
            
    def _extract_post_text(self, soup: BeautifulSoup) -> str:
        """Extract main post text content"""
        text_content = []
        
        # First try meta tags (most reliable for Threads)
        meta_selectors = [
            'meta[property="og:description"]',
            'meta[name="description"]',
            'meta[name="twitter:description"]'
        ]
        
        for selector in meta_selectors:
            meta_element = soup.select_one(selector)
            if meta_element:
                content = meta_element.get('content', '')
                if content and len(content.strip()) > 0:
                    text_content.append(content.strip())
                    break
        
        # If meta tags don't work, try multiple selectors for post text
        if not text_content:
            for selector in self.selectors['post_text']:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    if text and text not in text_content:
                        text_content.append(text)
                        
        # If no specific text selectors work, try broader approach
        if not text_content:
            # Look for text in post containers
            for container_selector in self.selectors['post_container']:
                containers = soup.select(container_selector)
                for container in containers:
                    # Get all text from the container, excluding nested elements we've already processed
                    text = container.get_text(separator=' ', strip=True)
                    if text and len(text) > 10:  # Minimum length filter
                        text_content.append(text)
                        break
                if text_content:
                    break
                    
        return ' '.join(text_content) if text_content else ""
        
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract all links from the post"""
        links = []
        seen_urls = set()
        
        for selector in self.selectors['post_links']:
            link_elements = soup.select(selector)
            for link in link_elements:
                href = link.get('href')
                if href and href not in seen_urls:
                    # Clean and normalize URL
                    clean_url = self._clean_url(href, base_url)
                    if clean_url and clean_url.startswith(('http://', 'https://')):
                        links.append({
                            'url': clean_url,
                            'text': link.get_text(strip=True),
                            'title': link.get('title', '')
                        })
                        seen_urls.add(href)
                        
        return links
        
    def _extract_mentions(self, soup: BeautifulSoup) -> List[str]:
        """Extract user mentions from the post"""
        mentions = []
        seen_mentions = set()
        
        # Extract from mention-specific selectors
        for selector in self.selectors['mentions']:
            mention_elements = soup.select(selector)
            for mention in mention_elements:
                href = mention.get('href', '')
                text = mention.get_text(strip=True)
                
                # Extract username from href or text
                username = None
                if '/@' in href:
                    username = href.split('/@')[-1].split('/')[0]
                elif text.startswith('@'):
                    username = text[1:]  # Remove @ symbol
                    
                if username and username not in seen_mentions:
                    mentions.append(username)
                    seen_mentions.add(username)
                    
        # Also extract from text using regex
        post_text = self._extract_post_text(soup)
        mention_matches = re.findall(r'@([a-zA-Z0-9_\.]+)', post_text)
        for username in mention_matches:
            if username not in seen_mentions:
                mentions.append(username)
                seen_mentions.add(username)
                
        return mentions
        
    def _extract_hashtags(self, soup: BeautifulSoup) -> List[str]:
        """Extract hashtags from the post"""
        hashtags = []
        seen_hashtags = set()
        
        # Extract from hashtag-specific selectors
        for selector in self.selectors['hashtags']:
            hashtag_elements = soup.select(selector)
            for hashtag in hashtag_elements:
                text = hashtag.get_text(strip=True)
                if text.startswith('#'):
                    tag = text[1:]  # Remove # symbol
                    if tag and tag not in seen_hashtags:
                        hashtags.append(tag)
                        seen_hashtags.add(tag)
                        
        # Also extract from text using regex
        post_text = self._extract_post_text(soup)
        hashtag_matches = re.findall(r'#([a-zA-Z0-9_]+)', post_text)
        for tag in hashtag_matches:
            if tag not in seen_hashtags:
                hashtags.append(tag)
                seen_hashtags.add(tag)
                
        return hashtags
        
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract post metadata like timestamp, author, engagement"""
        metadata = {}
        
        # Extract timestamp
        timestamp_text = self._extract_text_content(soup, self.selectors['timestamp'])
        if timestamp_text:
            metadata['timestamp'] = timestamp_text
            
        # Extract author information
        author_text = self._extract_text_content(soup, self.selectors['author'])
        if author_text:
            metadata['author'] = author_text
            
        # Extract engagement metrics (likes, replies, etc.)
        engagement_elements = []
        for selector in self.selectors['engagement']:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and any(char.isdigit() for char in text):
                    engagement_elements.append(text)
                    
        if engagement_elements:
            metadata['engagement'] = engagement_elements
            
        return metadata
        
    async def extract_content(self, url: str) -> Dict[str, Any]:
        """
        Extract content from a Threads post URL
        
        Args:
            url: Threads post URL
            
        Returns:
            Dictionary containing extracted content
        """
        try:
            # Validate and parse URL
            url_info = self._validate_threads_url(url)
            
            if url_info['url_type'] != 'post':
                raise ContentExtractionError("Only post URLs are supported for content extraction")
                
            # Use browser to load the page
            page_source = await self._make_request(url, use_browser=True)
            
            if not isinstance(page_source, str):
                raise ContentExtractionError("Failed to get page source from browser")
                
            # Parse HTML
            soup = self._parse_html(page_source)
            
            # Extract content components
            post_text = self._extract_post_text(soup)
            links = self._extract_links(soup, url)
            mentions = self._extract_mentions(soup)
            hashtags = self._extract_hashtags(soup)
            metadata = self._extract_metadata(soup)
            
            # Determine content type
            content_type = ContentType.TEXT  # Threads is primarily text-based
            
            return {
                'url': url,
                'platform': self.platform.value,
                'content_type': content_type.value,
                'username': url_info['username'],
                'post_id': url_info['post_id'],
                'text': post_text,
                'links': links,
                'mentions': mentions,
                'hashtags': hashtags,
                'metadata': metadata,
                'extracted_at': datetime.now(timezone.utc).isoformat(),
                'success': True,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Failed to extract content from {url}: {str(e)}")
            return {
                'url': url,
                'platform': self.platform.value,
                'content_type': None,
                'text': None,
                'links': [],
                'mentions': [],
                'hashtags': [],
                'metadata': {},
                'extracted_at': datetime.now(timezone.utc).isoformat(),
                'success': False,
                'error': str(e)
            }
            
    async def extract_bulk_content(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Extract content from multiple Threads URLs
        
        Args:
            urls: List of Threads URLs
            
        Returns:
            List of extraction results
        """
        results = []
        
        for url in urls:
            try:
                result = await self.extract_content(url)
                results.append(result)
                
                # Add delay between requests to avoid rate limiting
                if len(results) < len(urls):  # Don't delay after last request
                    delay = self._get_random_delay()
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Failed to extract content from {url}: {str(e)}")
                results.append({
                    'url': url,
                    'platform': self.platform.value,
                    'success': False,
                    'error': str(e),
                    'extracted_at': datetime.now(timezone.utc).isoformat()
                })
                
        return results
        
    async def download_content(self, url: str, output_dir: str = "downloads") -> Dict[str, Any]:
        """
        Download and save Threads content
        
        Args:
            url: Threads post URL
            output_dir: Directory to save content
            
        Returns:
            Download result with file paths
        """
        try:
            # Extract content first
            content = await self.extract_content(url)
            
            if not content['success']:
                # Ensure downloaded field is present for failed extractions
                content['downloaded'] = False
                return content
                
            # For Threads, we primarily save text content as JSON
            import json
            import os
            from pathlib import Path
            
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate filename based on post ID and username
            username = content['username']
            post_id = content['post_id']
            filename = f"threads_{username}_{post_id}.json"
            file_path = output_path / filename
            
            # Save content as JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
                
            # Update result with file information
            content.update({
                'downloaded': True,
                'file_path': str(file_path),
                'file_size': os.path.getsize(file_path),
                'download_timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"Successfully downloaded Threads content to {file_path}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to download content from {url}: {str(e)}")
            return {
                'url': url,
                'platform': self.platform.value,
                'success': False,
                'downloaded': False,
                'error': f"Download failed: {str(e)}",
                'extracted_at': datetime.now(timezone.utc).isoformat()
            }


# Convenience function for easy usage
async def extract_threads_content(url: str, **kwargs) -> Dict[str, Any]:
    """
    Convenience function to extract content from a Threads URL
    
    Args:
        url: Threads post URL
        **kwargs: Additional arguments for ThreadsDownloader
        
    Returns:
        Extracted content dictionary
    """
    async with ThreadsDownloader(**kwargs) as downloader:
        return await downloader.extract_content(url)


async def download_threads_content(url: str, output_dir: str = "downloads", **kwargs) -> Dict[str, Any]:
    """
    Convenience function to download content from a Threads URL
    
    Args:
        url: Threads post URL
        output_dir: Directory to save content
        **kwargs: Additional arguments for ThreadsDownloader
        
    Returns:
        Download result dictionary
    """
    async with ThreadsDownloader(**kwargs) as downloader:
        return await downloader.download_content(url, output_dir) 