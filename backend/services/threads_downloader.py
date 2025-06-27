"""
Threads Content Downloader - Extract text content and links from Threads posts
"""

import asyncio
import logging
import re
import time
import os
import aiofiles
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

from .base_extractor import BaseContentExtractor, ContentExtractionError
from .progress_tracker import ProgressStep
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
        
        # Threads-specific headers
        self.threads_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
        
        # Content patterns for different post types
        self.content_patterns = {
            'text_post': r'<div[^>]*data-testid="post-text"[^>]*>(.*?)</div>',
            'image_post': r'<img[^>]*src="([^"]*)"[^>]*alt="[^"]*post[^"]*"',
            'video_post': r'<video[^>]*src="([^"]*)"',
            'link_preview': r'<a[^>]*href="([^"]*)"[^>]*class="[^"]*link-preview[^"]*"',
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
        Extract content from a single Threads URL with progress tracking
        
        Args:
            url: Threads URL to extract content from
            
        Returns:
            Dictionary containing extracted content data
        """
        try:
            # Start progress tracking
            await self._start_progress(total_items=1)
            await self._update_progress(ProgressStep.INITIALIZING, "Starting content extraction")
            
            # Validate URL
            await self._update_progress(ProgressStep.VALIDATING_URL, "Validating Threads URL")
            if not self._validate_url(url):
                error_msg = f"Invalid Threads URL: {url}"
                await self._report_error(error_msg)
                return self._create_error_result(url, error_msg)
                
            # Determine content type from URL
            content_type = self._determine_content_type_from_url(url)
            await self._update_progress(
                ProgressStep.VALIDATING_URL, 
                f"Detected content type: {content_type}",
                0.3
            )
            
            # Fetch page content
            await self._update_progress(ProgressStep.FETCHING_CONTENT, "Fetching page content")
            try:
                response = await self._make_request(url, headers=self.threads_headers, use_browser=True)
                html_content = response if isinstance(response, str) else response.text
                await self._update_progress(
                    ProgressStep.FETCHING_CONTENT, 
                    "Page content retrieved successfully",
                    0.8
                )
            except Exception as e:
                error_msg = f"Failed to fetch content from {url}: {str(e)}"
                await self._report_error(error_msg)
                return self._create_error_result(url, error_msg)
                
            # Parse HTML content
            await self._update_progress(ProgressStep.PARSING_CONTENT, "Parsing HTML content")
            soup = self._parse_html(html_content)
            await self._update_progress(
                ProgressStep.PARSING_CONTENT, 
                "HTML parsing completed",
                0.5
            )
            
            # Extract content based on type
            await self._update_progress(ProgressStep.EXTRACTING_MEDIA, "Extracting content data")
            
            if content_type == "post":
                content_data = await self._extract_post_content(soup, url)
            elif content_type == "profile":
                content_data = await self._extract_profile_content(soup, url)
            else:
                # Generic content extraction
                content_data = await self._extract_generic_content(soup, url)
                
            await self._update_progress(
                ProgressStep.EXTRACTING_MEDIA, 
                f"Content extraction completed - found {len(content_data.get('media_urls', []))} media items",
                1.0
            )
            
            # Store/finalize data
            await self._update_progress(ProgressStep.STORING_DATA, "Finalizing extracted data")
            content_data.update({
                'extraction_timestamp': datetime.utcnow().isoformat(),
                'platform': self.platform.value,
                'url': url,
                'content_type': content_type,
                'success': True
            })
            
            await self._update_progress(ProgressStep.FINALIZING, "Content extraction completed successfully")
            
            return content_data
            
        except Exception as e:
            error_msg = f"Content extraction failed for {url}: {str(e)}"
            logger.error(error_msg)
            await self._report_error(error_msg)
            return self._create_error_result(url, error_msg)

    async def extract_bulk_content(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Extract content from multiple Threads URLs with progress tracking
        
        Args:
            urls: List of Threads URLs to extract content from
            
        Returns:
            List of dictionaries containing extracted content data
        """
        results = []
        total_urls = len(urls)
        
        try:
            # Start progress tracking for bulk operation
            await self._start_progress(total_items=total_urls)
            await self._update_progress(
                ProgressStep.INITIALIZING, 
                f"Starting bulk extraction for {total_urls} URLs"
            )
            
            for i, url in enumerate(urls, 1):
                try:
                    await self._update_progress(
                        ProgressStep.FETCHING_CONTENT,
                        f"Processing URL {i}/{total_urls}: {url}",
                        (i - 1) / total_urls
                    )
                    
                    # Extract content for individual URL
                    content_data = await self.extract_content(url)
                    results.append(content_data)
                    
                    if content_data.get('success'):
                        logger.info(f"Successfully extracted content from {url}")
                    else:
                        await self._report_error(
                            f"Failed to extract content from {url}: {content_data.get('error', 'Unknown error')}", 
                            warning=True
                        )
                        
                except Exception as e:
                    error_msg = f"Error processing {url}: {str(e)}"
                    logger.error(error_msg)
                    await self._report_error(error_msg, warning=True)
                    results.append(self._create_error_result(url, error_msg))
                
                # Update progress
                await self._update_progress(
                    ProgressStep.STORING_DATA,
                    f"Completed {i}/{total_urls} URLs",
                    i / total_urls
                )
                
                # Rate limiting between requests
                if i < total_urls:
                    await asyncio.sleep(self._get_random_delay(1.0))
                    
            # Finalize bulk operation
            successful_extractions = sum(1 for result in results if result.get('success', False))
            await self._update_progress(
                ProgressStep.FINALIZING,
                f"Bulk extraction completed: {successful_extractions}/{total_urls} successful"
            )
            
            return results
            
        except Exception as e:
            error_msg = f"Bulk extraction failed: {str(e)}"
            logger.error(error_msg)
            await self._report_error(error_msg)
            return [self._create_error_result(url, error_msg) for url in urls]

    async def download_content(self, url: str) -> Dict[str, Any]:
        """
        Download content including media files with progress tracking
        
        Args:
            url: Threads URL to download content from
            
        Returns:
            Dictionary containing downloaded content data and file paths
        """
        try:
            await self._update_progress(ProgressStep.INITIALIZING, "Starting content download")
            
            # First extract content metadata
            content_data = await self.extract_content(url)
            
            if not content_data.get('success'):
                return content_data
                
            # Download media files if any
            media_urls = content_data.get('media_urls', [])
            if media_urls:
                await self._update_progress(
                    ProgressStep.DOWNLOADING_FILES, 
                    f"Downloading {len(media_urls)} media files"
                )
                
                downloaded_files = []
                for i, media_url in enumerate(media_urls):
                    try:
                        file_path = await self._download_media_file(media_url, url)
                        if file_path:
                            downloaded_files.append(file_path)
                            
                        await self._update_progress(
                            ProgressStep.DOWNLOADING_FILES,
                            f"Downloaded file {i+1}/{len(media_urls)}",
                            (i + 1) / len(media_urls)
                        )
                        
                    except Exception as e:
                        await self._report_error(f"Failed to download media file {media_url}: {str(e)}", warning=True)
                        
                content_data['downloaded_files'] = downloaded_files
                await self._update_progress(
                    ProgressStep.DOWNLOADING_FILES,
                    f"Downloaded {len(downloaded_files)}/{len(media_urls)} files successfully"
                )
            else:
                await self._update_progress(ProgressStep.DOWNLOADING_FILES, "No media files to download")
                
            await self._update_progress(ProgressStep.FINALIZING, "Content download completed")
            return content_data
            
        except Exception as e:
            error_msg = f"Content download failed for {url}: {str(e)}"
            logger.error(error_msg)
            await self._report_error(error_msg)
            return self._create_error_result(url, error_msg)

    def _create_error_result(self, url: str, error: str) -> Dict[str, Any]:
        """Create standardized error result"""
        return {
            'success': False,
            'url': url,
            'platform': self.platform.value,
            'error': error,
            'extraction_timestamp': datetime.utcnow().isoformat(),
            'content_type': 'unknown',
            'title': None,
            'content': None,
            'media_urls': [],
            'metadata': {}
        }

    def _determine_content_type_from_url(self, url: str) -> str:
        """Determine content type from URL structure"""
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        if '/post/' in path or '/@' in path and '/post/' in path:
            return "post"
        elif '/@' in path and '/post/' not in path:
            return "profile"
        else:
            return "unknown"

    async def _extract_post_content(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract content from a Threads post"""
        try:
            # Extract post text
            post_text = self._extract_text_content(soup, [
                '[data-testid="post-text"]',
                '.post-text',
                '.thread-text',
                'div[role="article"] div[dir="auto"]'
            ]) or ""
            
            # Extract media URLs
            media_urls = []
            
            # Look for images
            image_urls = self._extract_all_attributes(soup, 'img[src*="cdninstagram"]', 'src')
            media_urls.extend(image_urls)
            
            # Look for videos
            video_urls = self._extract_all_attributes(soup, 'video source', 'src')
            media_urls.extend(video_urls)
            
            # Extract metadata
            metadata = self._extract_post_metadata(soup, url)
            
            # Extract engagement metrics
            engagement = self._extract_engagement_metrics(soup)
            
            return {
                'title': metadata.get('title', ''),
                'content': post_text,
                'media_urls': media_urls,
                'metadata': {
                    **metadata,
                    'engagement': engagement,
                    'links': self._extract_links(soup, url),
                    'mentions': self._extract_mentions(soup),
                    'hashtags': self._extract_hashtags(soup)
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting post content: {str(e)}")
            return {
                'title': '',
                'content': '',
                'media_urls': [],
                'metadata': {'error': str(e)}
            }

    async def _extract_profile_content(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract content from a Threads profile"""
        try:
            # Extract profile information
            username = self._extract_text_content(soup, [
                'h1', 
                '[data-testid="profile-username"]',
                '.profile-username'
            ]) or ""
            
            bio = self._extract_text_content(soup, [
                '[data-testid="profile-bio"]',
                '.profile-bio',
                'div[role="main"] div[dir="auto"]'
            ]) or ""
            
            # Extract profile picture
            profile_pic_url = self._extract_attribute(soup, 'img[alt*="profile picture"]', 'src')
            
            # Extract follower counts (if visible)
            follower_info = self._extract_follower_info(soup)
            
            return {
                'title': f"@{username}" if username else "Threads Profile",
                'content': bio,
                'media_urls': [profile_pic_url] if profile_pic_url else [],
                'metadata': {
                    'username': username,
                    'bio': bio,
                    'profile_picture_url': profile_pic_url,
                    **follower_info
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting profile content: {str(e)}")
            return {
                'title': '',
                'content': '',
                'media_urls': [],
                'metadata': {'error': str(e)}
            }

    async def _extract_generic_content(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract generic content from any Threads page"""
        try:
            # Try to extract any text content
            content = self._extract_text_content(soup, [
                'main',
                '[role="main"]',
                'article',
                'div[dir="auto"]'
            ]) or ""
            
            # Extract any media
            media_urls = []
            
            # Images
            images = self._extract_all_attributes(soup, 'img[src]', 'src')
            media_urls.extend([img for img in images if 'cdninstagram' in img or 'threads' in img])
            
            # Videos
            videos = self._extract_all_attributes(soup, 'video source', 'src')
            media_urls.extend(videos)
            
            # Extract page title
            title = self._extract_text_content(soup, ['title', 'h1', 'h2']) or "Threads Content"
            
            return {
                'title': title,
                'content': content,
                'media_urls': media_urls,
                'metadata': {
                    'page_type': 'generic',
                    'links': self._extract_links(soup, url)
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting generic content: {str(e)}")
            return {
                'title': '',
                'content': '',
                'media_urls': [],
                'metadata': {'error': str(e)}
            }

    def _extract_post_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract metadata from a Threads post"""
        metadata = {}
        
        try:
            # Extract post ID from URL
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.split('/')
            if 'post' in path_parts:
                post_index = path_parts.index('post')
                if post_index + 1 < len(path_parts):
                    metadata['post_id'] = path_parts[post_index + 1]
            
            # Extract username from URL
            if '/@' in parsed_url.path:
                username_match = re.search(r'/@([^/]+)', parsed_url.path)
                if username_match:
                    metadata['username'] = username_match.group(1)
            
            # Extract timestamp if available
            time_element = soup.find('time')
            if time_element:
                timestamp = time_element.get('datetime') or time_element.get('title')
                if timestamp:
                    metadata['timestamp'] = timestamp
            
            # Extract meta tags
            meta_tags = soup.find_all('meta')
            for meta in meta_tags:
                if meta.get('property') == 'og:title':
                    metadata['title'] = meta.get('content', '')
                elif meta.get('property') == 'og:description':
                    metadata['description'] = meta.get('content', '')
                elif meta.get('name') == 'description':
                    metadata['page_description'] = meta.get('content', '')
                    
        except Exception as e:
            logger.error(f"Error extracting post metadata: {str(e)}")
            metadata['metadata_error'] = str(e)
            
        return metadata

    def _extract_follower_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract follower information from profile page"""
        follower_info = {}
        
        try:
            # Look for follower count patterns
            follower_elements = soup.find_all(text=re.compile(r'\d+\s*(followers?|following)', re.I))
            
            for element in follower_elements:
                text = element.strip().lower()
                if 'follower' in text:
                    # Extract number
                    numbers = re.findall(r'[\d,]+', text)
                    if numbers:
                        follower_info['followers'] = numbers[0].replace(',', '')
                elif 'following' in text:
                    numbers = re.findall(r'[\d,]+', text)
                    if numbers:
                        follower_info['following'] = numbers[0].replace(',', '')
                        
        except Exception as e:
            logger.error(f"Error extracting follower info: {str(e)}")
            
        return follower_info

    def _extract_mentions(self, soup: BeautifulSoup) -> List[str]:
        """Extract @mentions from content"""
        mentions = []
        
        try:
            # Look for mention links or patterns
            mention_links = soup.find_all('a', href=re.compile(r'/@[\w.]+'))
            for link in mention_links:
                href = link.get('href', '')
                mention_match = re.search(r'/@([\w.]+)', href)
                if mention_match:
                    mentions.append(mention_match.group(1))
            
            # Also look for @mentions in text content
            text_content = soup.get_text()
            text_mentions = re.findall(r'@([\w.]+)', text_content)
            mentions.extend(text_mentions)
            
            # Remove duplicates and return
            return list(set(mentions))
            
        except Exception as e:
            logger.error(f"Error extracting mentions: {str(e)}")
            return []

    def _extract_hashtags(self, soup: BeautifulSoup) -> List[str]:
        """Extract #hashtags from content"""
        hashtags = []
        
        try:
            # Look for hashtag links
            hashtag_links = soup.find_all('a', href=re.compile(r'/tag/[\w]+'))
            for link in hashtag_links:
                href = link.get('href', '')
                hashtag_match = re.search(r'/tag/([\w]+)', href)
                if hashtag_match:
                    hashtags.append(hashtag_match.group(1))
            
            # Also look for #hashtags in text content
            text_content = soup.get_text()
            text_hashtags = re.findall(r'#([\w]+)', text_content)
            hashtags.extend(text_hashtags)
            
            # Remove duplicates and return
            return list(set(hashtags))
            
        except Exception as e:
            logger.error(f"Error extracting hashtags: {str(e)}")
            return []

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract external links from content"""
        links = []
        
        try:
            # Find all links
            link_elements = soup.find_all('a', href=True)
            
            for link in link_elements:
                href = link.get('href', '')
                if href:
                    # Convert relative URLs to absolute
                    absolute_url = urljoin(base_url, href)
                    
                    # Filter out internal Threads links
                    if not any(domain in absolute_url for domain in self.get_platform_domains()):
                        links.append(absolute_url)
            
            return list(set(links))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error extracting links: {str(e)}")
            return []

    async def _download_media_file(self, media_url: str, source_url: str) -> Optional[str]:
        """Download a media file and return the local file path"""
        try:
            # Create downloads directory
            downloads_dir = "downloads/threads"
            os.makedirs(downloads_dir, exist_ok=True)
            
            # Generate filename
            parsed_url = urlparse(media_url)
            filename = os.path.basename(parsed_url.path)
            if not filename or '.' not in filename:
                # Generate filename based on URL hash
                import hashlib
                url_hash = hashlib.md5(media_url.encode()).hexdigest()[:8]
                extension = '.jpg'  # Default extension
                if 'video' in media_url.lower():
                    extension = '.mp4'
                filename = f"threads_media_{url_hash}{extension}"
            
            file_path = os.path.join(downloads_dir, filename)
            
            # Download the file
            response = await self._make_request(media_url)
            if isinstance(response, str):
                # If it's a string response, it's probably an error
                logger.warning(f"Unexpected string response for media URL: {media_url}")
                return None
                
            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(response.content)
                
            logger.info(f"Downloaded media file: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to download media file {media_url}: {str(e)}")
            return None


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