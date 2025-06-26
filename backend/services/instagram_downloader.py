"""
Instagram Content Downloader with Advanced Anti-Detection
"""

import asyncio
import logging
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse, parse_qs
import re
import requests

try:
    import instaloader
except ImportError:
    instaloader = None

from .base_extractor import BaseContentExtractor
from .scraping_infrastructure import AntiDetectionScraper, create_stealth_scraper
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class InstagramDownloader(BaseContentExtractor):
    """
    Instagram content downloader using instaloader with anti-detection measures
    """
    
    SUPPORTED_DOMAINS = [
        'instagram.com',
        'www.instagram.com',
        'm.instagram.com'
    ]
    
    def __init__(self, download_dir: str = "downloads", rate_limit: float = 2.0):
        # Don't call super().__init__() as BaseContentExtractor has different parameters
        self.download_dir = download_dir
        self.rate_limiter = RateLimiter(rate_limit)
        self.scraper = None
        
        # Initialize instaloader
        if instaloader:
            self.loader = instaloader.Instaloader(
                dirname_pattern="{target}",
                filename_pattern="{date_utc}_UTC_{typename}_{shortcode}",
                download_videos=True,
                download_comments=False,
                save_metadata=True,
                compress_json=False
            )
        else:
            self.loader = None
            logger.warning("instaloader not available, falling back to scraping")
    
    def get_platform_domains(self) -> List[str]:
        """Return list of supported Instagram domains"""
        return self.SUPPORTED_DOMAINS
    
    def validate_url(self, url: str) -> bool:
        """Validate if URL is a supported Instagram URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Check if it's an Instagram domain
            if not any(domain.endswith(d) for d in self.SUPPORTED_DOMAINS):
                return False
            
            # Check if it's a valid Instagram content URL
            path = parsed.path.lower()
            valid_patterns = [
                r'^/p/[a-zA-Z0-9_-]+/?$',  # Posts
                r'^/reel/[a-zA-Z0-9_-]+/?$',  # Reels
                r'^/tv/[a-zA-Z0-9_-]+/?$',  # IGTV
                r'^/stories/[a-zA-Z0-9_.]+/[0-9]+/?$',  # Stories
                r'^/[a-zA-Z0-9_.]+/?$'  # Profile
            ]
            
            return any(re.match(pattern, path) for pattern in valid_patterns)
            
        except Exception as e:
            logger.error(f"Error validating Instagram URL {url}: {e}")
            return False
    
    def _extract_shortcode_from_url(self, url: str) -> Optional[str]:
        """Extract Instagram shortcode from URL"""
        try:
            parsed = urlparse(url)
            path = parsed.path.strip('/')
            
            # Extract shortcode from different URL types
            if path.startswith(('p/', 'reel/', 'tv/')):
                parts = path.split('/')
                if len(parts) >= 2:
                    return parts[1]
            
            return None
        except Exception as e:
            logger.error(f"Error extracting shortcode from {url}: {e}")
            return None
    
    def _get_download_directory(self, url: str) -> Path:
        """Get download directory for Instagram content"""
        today = datetime.now().strftime("%Y-%m-%d")
        shortcode = self._extract_shortcode_from_url(url) or "unknown"
        
        return Path(self.download_dir) / "instagram" / today / shortcode
    
    async def extract_content(self, url: str) -> Dict[str, Any]:
        """Extract content metadata from Instagram URL"""
        if not self.validate_url(url):
            raise ValueError(f"Invalid Instagram URL: {url}")

        await self.rate_limiter.wait()

        # Try instaloader first
        if self.loader:
            try:
                logger.info(f"Attempting extraction with instaloader for {url}")
                return await self._extract_with_instaloader(url)
            except Exception as e:
                logger.warning(f"Instaloader failed for {url}: {e}. Falling back to scraping...")
                # Fall through to scraping method
        
        # Fallback to scraping
        try:
            logger.info(f"Attempting extraction with scraping for {url}")
            return await self._extract_with_scraping(url)
        except Exception as e:
            logger.error(f"Both extraction methods failed for {url}: {e}")
            raise
    
    async def _extract_with_instaloader(self, url: str) -> Dict[str, Any]:
        """Extract content using instaloader library"""
        shortcode = self._extract_shortcode_from_url(url)
        if not shortcode:
            raise ValueError(f"Could not extract shortcode from URL: {url}")

        try:
            # Get post from shortcode
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)

            return {
                'url': url,
                'shortcode': shortcode,
                'title': post.caption or "",
                'description': post.caption or "",
                'author': post.owner_username,
                'upload_date': post.date_utc.isoformat() if post.date_utc else None,
                'view_count': post.video_view_count if post.is_video else None,
                'like_count': post.likes,
                'comment_count': post.comments,
                'is_video': post.is_video,
                'duration': post.video_duration if post.is_video else None,
                'thumbnail_url': post.url,
                'media_urls': [post.video_url] if post.is_video else [post.url],
                'hashtags': post.caption_hashtags,
                'mentions': post.caption_mentions,
                'location': post.location.name if post.location else None,
                'extracted_at': datetime.now().isoformat()
            }
        except Exception as e:
            error_msg = str(e).lower()
            # Check for private account indicators
            if any(indicator in error_msg for indicator in [
                'fetching post metadata failed',
                'private',
                'not found',
                '403 forbidden'
            ]):
                # This might be a private account, let the fallback handle it
                logger.info(f"Potential private account or access issue for {url}: {e}")
                raise  # Re-raise to trigger fallback
            else:
                logger.error(f"Error extracting with instaloader: {e}")
                raise
    
    async def _extract_with_scraping(self, url: str) -> Dict[str, Any]:
        """Extract content using web scraping as fallback"""
        if not self.scraper:
            try:
                self.scraper = await create_stealth_scraper()
            except Exception as e:
                # If Chrome setup fails, check if this might be a private account
                # by doing a simple HTTP request first
                try:
                    response = requests.get(url, timeout=10)
                    if 'This account is private' in response.text or 'private' in response.text.lower():
                        return {
                            'url': url,
                            'shortcode': self._extract_shortcode_from_url(url),
                            'status': 'private_account',
                            'error': 'The account is private, cannot extract the data',
                            'extracted_at': datetime.now().isoformat(),
                            'extraction_method': 'http_check'
                        }
                except:
                    pass
                # If we can't determine if it's private, re-raise the Chrome error
                raise e

        try:
            await self.scraper.navigate_to(url)
            await asyncio.sleep(2)  # Wait for content to load

            # Check for private account message
            page_text = await self.scraper.get_page_source()
            if 'This account is private' in page_text or 'account is private' in page_text.lower():
                return {
                    'url': url,
                    'shortcode': self._extract_shortcode_from_url(url),
                    'status': 'private_account', 
                    'error': 'The account is private, cannot extract the data',
                    'extracted_at': datetime.now().isoformat(),
                    'extraction_method': 'scraping'
                }

            # Extract basic metadata from page
            title = await self.scraper.get_text('meta[property="og:title"]', attribute='content')
            description = await self.scraper.get_text('meta[property="og:description"]', attribute='content')
            image_url = await self.scraper.get_text('meta[property="og:image"]', attribute='content')

            return {
                'url': url,
                'shortcode': self._extract_shortcode_from_url(url),
                'title': title or "",
                'description': description or "",
                'thumbnail_url': image_url,
                'extracted_at': datetime.now().isoformat(),
                'extraction_method': 'scraping'
            }
        except Exception as e:
            logger.error(f"Error extracting with scraping: {e}")
            raise
    
    async def download_content(self, url: str, download_dir: Optional[str] = None) -> Dict[str, Any]:
        """Download Instagram content"""
        if not self.validate_url(url):
            raise ValueError(f"Invalid Instagram URL: {url}")

        # Get content metadata first
        content_info = await self.extract_content(url)
        
        # Check if account is private
        if content_info.get('status') == 'private_account':
            return {
                **content_info,
                'download_status': 'skipped',
                'download_path': None,
                'message': content_info.get('error', 'The account is private, cannot extract the data')
            }

        # Set up download directory
        target_dir = Path(download_dir) if download_dir else self._get_download_directory(url)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Try instaloader first
        if self.loader and content_info.get('shortcode'):
            try:
                logger.info(f"Attempting download with instaloader for {url}")
                return await self._download_with_instaloader(content_info, target_dir)
            except Exception as e:
                logger.warning(f"Instaloader download failed for {url}: {e}. Falling back to scraping...")
                # Fall through to scraping method
        
        # Fallback to scraping
        try:
            logger.info(f"Attempting download with scraping for {url}")
            return await self._download_with_scraping(content_info, target_dir)
        except Exception as e:
            logger.error(f"Both download methods failed for {url}: {e}")
            raise
    
    async def _download_with_instaloader(self, content_info: Dict[str, Any], target_dir: Path) -> Dict[str, Any]:
        """Download content using instaloader"""
        shortcode = content_info['shortcode']
        
        try:
            # Set download directory
            original_dir = self.loader.dirname_pattern
            self.loader.dirname_pattern = str(target_dir)
            
            # Download post
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            self.loader.download_post(post, target="")
            
            # Restore original directory pattern
            self.loader.dirname_pattern = original_dir
            
            # Create metadata file
            metadata_file = target_dir / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(content_info, f, indent=2, ensure_ascii=False)
            
            return {
                **content_info,
                'download_status': 'success',
                'download_path': str(target_dir),
                'files_downloaded': list(target_dir.glob('*'))
            }
            
        except Exception as e:
            logger.error(f"Error downloading with instaloader: {e}")
            return {
                **content_info,
                'download_status': 'failed',
                'error': str(e)
            }
    
    async def _download_with_scraping(self, content_info: Dict[str, Any], target_dir: Path) -> Dict[str, Any]:
        """Download content using web scraping"""
        # For now, just save metadata - actual media download would require more complex scraping
        metadata_file = target_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(content_info, f, indent=2, ensure_ascii=False)
        
        return {
            **content_info,
            'download_status': 'metadata_only',
            'download_path': str(target_dir),
            'note': 'Full media download requires instaloader library'
        }
    
    async def extract_bulk_content(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Extract content from multiple Instagram URLs"""
        results = []
        
        for url in urls:
            try:
                result = await self.extract_content(url)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing URL {url}: {e}")
                results.append({
                    'url': url,
                    'error': str(e),
                    'status': 'failed'
                })
        
        return results
    
    async def cleanup(self):
        """Clean up resources"""
        if self.scraper:
            await self.scraper.cleanup()
            self.scraper = None


# Utility function for easy access
def create_instagram_downloader(download_dir: str = "downloads", rate_limit: float = 2.0) -> InstagramDownloader:
    """Create an Instagram downloader instance"""
    return InstagramDownloader(download_dir, rate_limit)
