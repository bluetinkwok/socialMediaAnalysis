"""
YouTube Content Downloader - Downloads videos, thumbnails, and extracts metadata from YouTube
"""

import asyncio
import logging
import os
import re
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlparse, parse_qs

import yt_dlp
import aiofiles
from yt_dlp import YoutubeDL

from .base_extractor import BaseContentExtractor
from db.models import PlatformType, ContentType
from .rate_limiter import RateLimiter
from .progress_tracker import ProgressTracker, ProgressStep


class YouTubeDownloader(BaseContentExtractor):
    """
    YouTube content downloader using yt-dlp for video, thumbnail, and metadata extraction.
    Supports both regular YouTube videos and YouTube Shorts.
    """
    
    def __init__(self, progress_tracker: Optional[ProgressTracker] = None):
        super().__init__(platform=PlatformType.YOUTUBE, progress_tracker=progress_tracker)
        self.rate_limiter = RateLimiter(delay=1.0, burst_limit=3)  # Conservative rate limiting
        self.logger = logging.getLogger(__name__)
        
        # Base download directory
        self.download_base = Path("downloads/youtube")
        
        # Default yt-dlp configuration
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'writethumbnail': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en', 'en-US'],
            'format': 'best[height<=720]',  # Default to 720p for reasonable file sizes
            'outtmpl': '%(id)s.%(ext)s',
        }
    
    def _get_download_directory(self, video_id: str, file_type: str) -> Path:
        """
        Create download directory with structure: youtube/[YYYY-MM-DD]/video_id/{videos,images,texts}
        
        Args:
            video_id: YouTube video ID
            file_type: Type of file (video, image, text)
            
        Returns:
            Path to the specific download directory
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Map file types to directory names
        type_mapping = {
            "video": "videos",
            "image": "images", 
            "text": "texts"
        }
        
        subdir = type_mapping.get(file_type, "texts")
        download_dir = self.download_base / today / video_id / subdir
        download_dir.mkdir(parents=True, exist_ok=True)
        
        return download_dir
    
    async def extract_content(self, url: str) -> Dict[str, Any]:
        """
        Extract content and metadata from YouTube URL.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary containing extracted content and metadata
        """
        # Start progress tracking if available
        if self.progress_tracker:
            await self._start_progress()
            await self._update_progress(ProgressStep.INITIALIZING, "Initializing YouTube extractor")
        
        if not self.validate_url(url):
            error_msg = f"Invalid YouTube URL: {url}"
            if self.progress_tracker:
                await self._report_error(error_msg)
            raise ValueError(error_msg)
        
        # Update progress to URL validation step
        if self.progress_tracker:
            await self._update_progress(ProgressStep.VALIDATING_URL, f"Validating URL: {url}")
        
        # Apply rate limiting
        await self.rate_limiter.wait()
        
        try:
            # Update progress to fetching content
            if self.progress_tracker:
                await self._update_progress(ProgressStep.FETCHING_CONTENT, "Fetching video information")
            
            # Extract video information using yt-dlp
            with YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Extract video ID
                video_id = info.get('id', self._extract_video_id_from_url(url))
                
                # Update progress to parsing content
                if self.progress_tracker:
                    await self._update_progress(ProgressStep.PARSING_CONTENT, f"Processing metadata for video {video_id}")
                
                # Process metadata
                content_data = {
                    'url': url,
                    'platform': self.platform,
                    'extracted_at': datetime.now(timezone.utc).isoformat(),
                    'title': info.get('title', 'YouTube Video'),
                    'description': info.get('description', ''),
                    'video_id': video_id,
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'channel': info.get('uploader', 'Unknown Channel'),
                    'channel_id': info.get('uploader_id', 'Unknown'),
                    'upload_date': self._format_upload_date(info.get('upload_date')),
                    'thumbnail_url': info.get('thumbnail'),
                    'video_url': info.get('webpage_url', url),
                    'format_info': self._extract_format_info(info),
                    'subtitles_available': list(info.get('subtitles', {}).keys()),
                    'automatic_captions_available': list(info.get('automatic_captions', {}).keys()),
                    'content_type': self._determine_content_type(info),
                    'engagement_metrics': {
                        'views': info.get('view_count', 0),
                        'likes': info.get('like_count', 0),
                        'comments': info.get('comment_count', 0),
                        'shares': 0  # YouTube API doesn't provide shares count
                    },
                    'author': info.get('uploader', 'Unknown Channel'),
                    'author_id': info.get('uploader_id', 'Unknown'),
                    'publish_date': self._format_upload_date(info.get('upload_date')),
                    'media_urls': self._extract_media_urls(info),
                    'available_formats': self._get_available_formats(info)
                }
                
                # Update progress to finalizing
                if self.progress_tracker:
                    await self._update_progress(ProgressStep.FINALIZING, "Extraction complete")
                    await self.progress_tracker.complete(True, f"Successfully extracted metadata for {content_data['title']}")
                
                return content_data
                
        except Exception as e:
            error_msg = f"Error extracting YouTube content from {url}: {e}"
            self.logger.error(error_msg)
            
            if self.progress_tracker:
                await self._report_error(error_msg)
                await self.progress_tracker.complete(False, "Failed to extract content")
            
            # Return minimal data structure for error case
            return {
                'url': url,
                'platform': self.platform,
                'extracted_at': datetime.now(timezone.utc).isoformat(),
                'title': 'YouTube Video',
                'description': 'Error extracting content',
                'video_id': self._extract_video_id_from_url(url),
                'error': str(e),
                'content_type': ContentType.VIDEO,
                'engagement_metrics': {'views': 0, 'likes': 0, 'comments': 0, 'shares': 0},
                'author': 'Unknown Channel',
                'author_id': 'Unknown',
                'publish_date': None,
                'media_urls': []
            }
    
    async def download_content(self, url: str, quality: str = 'medium', format_id: str = None) -> Dict[str, Any]:
        """
        Download video, thumbnail, and subtitles from YouTube URL.
        
        Args:
            url: YouTube video URL
            quality: Quality level ('low', 'medium', 'high', 'best')
            format_id: Specific format ID to download (overrides quality)
            
        Returns:
            Dictionary containing download results
        """
        # Start progress tracking if available
        if self.progress_tracker:
            await self._start_progress()
            await self._update_progress(ProgressStep.INITIALIZING, "Initializing YouTube downloader")
        
        if not self.validate_url(url):
            error_msg = f"Invalid YouTube URL: {url}"
            if self.progress_tracker:
                await self._report_error(error_msg)
            raise ValueError(error_msg)
        
        # Update progress to URL validation step
        if self.progress_tracker:
            await self._update_progress(ProgressStep.VALIDATING_URL, f"Validating URL: {url}")
        
        # Apply rate limiting
        await self.rate_limiter.wait()
        
        video_id = self._extract_video_id_from_url(url)
        download_results = {
            'video_id': video_id,
            'url': url,
            'downloads': {
                'video': None,
                'thumbnail': None,
                'subtitles': [],
                'metadata': None
            },
            'errors': []
        }
        
        try:
            # Update progress to fetching content
            if self.progress_tracker:
                await self._update_progress(ProgressStep.FETCHING_CONTENT, f"Fetching video information for {video_id}")
            
            # Setup download directories
            video_dir = self._get_download_directory(video_id, "video")
            image_dir = self._get_download_directory(video_id, "image")
            text_dir = self._get_download_directory(video_id, "text")
            
            # Configure yt-dlp for downloading with selected quality
            download_opts = self.ydl_opts.copy()
            
            # Set format based on quality or format_id
            if format_id:
                download_opts['format'] = format_id
            else:
                download_opts['format'] = self._get_format_for_quality(quality)
                
            download_opts.update({
                'outtmpl': {
                    'default': str(video_dir / f'{video_id}.%(ext)s'),
                    'thumbnail': str(image_dir / f'{video_id}_thumbnail.%(ext)s'),
                    'subtitle': str(text_dir / f'{video_id}_%(lang)s.%(ext)s'),
                }
            })
            
            # Add progress hook if progress tracking is enabled
            if self.progress_tracker:
                download_opts['progress_hooks'] = [self._progress_hook]
            
            # Update progress to downloading files
            if self.progress_tracker:
                await self._update_progress(ProgressStep.DOWNLOADING_FILES, f"Downloading video {video_id}")
            
            # Download content
            with YoutubeDL(download_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Update progress to storing data
                if self.progress_tracker:
                    await self._update_progress(ProgressStep.STORING_DATA, "Processing downloaded files")
                
                # Record successful downloads
                if info:
                    # Check for video file
                    video_files = list(video_dir.glob(f"{video_id}.*"))
                    if video_files:
                        video_file = video_files[0]
                        download_results['downloads']['video'] = {
                            'file_path': str(video_file),
                            'file_size': video_file.stat().st_size,
                            'format': video_file.suffix,
                            'success': True
                        }
                    
                    # Check for thumbnail
                    thumbnail_files = list(image_dir.glob(f"{video_id}_thumbnail.*"))
                    if thumbnail_files:
                        thumbnail_file = thumbnail_files[0]
                        download_results['downloads']['thumbnail'] = {
                            'file_path': str(thumbnail_file),
                            'file_size': thumbnail_file.stat().st_size,
                            'format': thumbnail_file.suffix,
                            'success': True
                        }
                    
                    # Check for subtitles
                    subtitle_files = list(text_dir.glob(f"{video_id}_*.vtt")) + list(text_dir.glob(f"{video_id}_*.srt"))
                    for subtitle_file in subtitle_files:
                        lang = subtitle_file.stem.split('_')[-1]
                        download_results['downloads']['subtitles'].append({
                            'language': lang,
                            'file_path': str(subtitle_file),
                            'file_size': subtitle_file.stat().st_size,
                            'format': subtitle_file.suffix,
                            'success': True
                        })
                    
                    # Save metadata
                    metadata_file = text_dir / f"{video_id}_metadata.json"
                    async with aiofiles.open(metadata_file, 'w', encoding='utf-8') as f:
                        await f.write(json.dumps(info, indent=2, default=str))
                    
                    download_results['downloads']['metadata'] = {
                        'file_path': str(metadata_file),
                        'file_size': metadata_file.stat().st_size,
                        'success': True
                    }
                    
                    # Update progress to finalizing
                    if self.progress_tracker:
                        await self._update_progress(ProgressStep.FINALIZING, "Download complete")
                        await self.progress_tracker.complete(True, f"Successfully downloaded video {info.get('title', video_id)}")
                
        except Exception as e:
            error_msg = f"Error downloading YouTube content: {e}"
            self.logger.error(error_msg)
            download_results['errors'].append(error_msg)
            
            if self.progress_tracker:
                await self._report_error(error_msg)
                await self.progress_tracker.complete(False, "Download failed")
        
        return download_results
    
    def _progress_hook(self, d: Dict[str, Any]) -> None:
        """
        Progress hook for yt-dlp to track download progress
        
        Args:
            d: Progress information from yt-dlp
        """
        if not self.progress_tracker:
            return
            
        status = d.get('status')
        
        if status == 'downloading':
            # Calculate download progress
            total_bytes = d.get('total_bytes')
            downloaded_bytes = d.get('downloaded_bytes', 0)
            
            if total_bytes:
                progress = (downloaded_bytes / total_bytes) * 100
                asyncio.create_task(
                    self._update_progress(
                        ProgressStep.DOWNLOADING_FILES,
                        f"Downloading: {d.get('filename', 'video')} - {progress:.1f}%",
                        progress / 100
                    )
                )
            elif d.get('total_bytes_estimate'):
                # Use estimated total if exact total not available
                total_bytes_estimate = d.get('total_bytes_estimate')
                progress = (downloaded_bytes / total_bytes_estimate) * 100
                asyncio.create_task(
                    self._update_progress(
                        ProgressStep.DOWNLOADING_FILES,
                        f"Downloading: {d.get('filename', 'video')} - {progress:.1f}% (estimated)",
                        progress / 100
                    )
                )
            else:
                # If no size info available, just show downloaded bytes
                asyncio.create_task(
                    self._update_progress(
                        ProgressStep.DOWNLOADING_FILES,
                        f"Downloading: {d.get('filename', 'video')} - {downloaded_bytes/1024/1024:.1f} MB",
                        0.5  # Use 50% as placeholder
                    )
                )
                
        elif status == 'finished':
            filename = d.get('filename', '')
            asyncio.create_task(
                self._update_progress(
                    ProgressStep.STORING_DATA,
                    f"Download finished: {filename}",
                    0.9  # 90% complete
                )
            )
            
        elif status == 'error':
            error_msg = f"Download error: {d.get('error', 'Unknown error')}"
            asyncio.create_task(self._report_error(error_msg))
    
    def _get_format_for_quality(self, quality: str) -> str:
        """
        Get yt-dlp format string for the requested quality
        
        Args:
            quality: Quality level ('low', 'medium', 'high', 'best')
            
        Returns:
            Format string for yt-dlp
        """
        quality_mapping = {
            'low': 'worst[height>=240]',
            'medium': 'best[height<=480]',
            'high': 'best[height<=720]',
            'best': 'best'
        }
        
        return quality_mapping.get(quality.lower(), 'best[height<=720]')
    
    def _get_available_formats(self, info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract available formats from video info
        
        Args:
            info: Video info from yt-dlp
            
        Returns:
            List of available formats with details
        """
        formats = info.get('formats', [])
        if not formats:
            return []
            
        available_formats = []
        
        for fmt in formats:
            # Skip formats without video
            if fmt.get('vcodec') == 'none':
                continue
                
            format_info = {
                'format_id': fmt.get('format_id'),
                'ext': fmt.get('ext'),
                'resolution': f"{fmt.get('width', 0)}x{fmt.get('height', 0)}",
                'filesize': fmt.get('filesize'),
                'filesize_approx': fmt.get('filesize_approx'),
                'fps': fmt.get('fps'),
                'vcodec': fmt.get('vcodec'),
                'acodec': fmt.get('acodec'),
                'format_note': fmt.get('format_note', '')
            }
            
            available_formats.append(format_info)
            
        return available_formats
    
    def get_platform_domains(self) -> List[str]:
        """
        Get list of domains supported by this downloader.
        
        Returns:
            List of supported domain names
        """
        return [
            'youtube.com',
            'www.youtube.com',
            'm.youtube.com',
            'youtu.be',
            'music.youtube.com'
        ]
    
    def validate_url(self, url: str) -> bool:
        """
        Validate if the URL is a valid YouTube URL.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            parsed = urlparse(url)
            valid_domains = self.get_platform_domains()
            
            if parsed.netloc.lower() not in valid_domains:
                return False
            
            # Check for video ID patterns
            if parsed.netloc == 'youtu.be':
                # Short URL format: https://youtu.be/VIDEO_ID
                return len(parsed.path) > 1
            
            # Regular YouTube URLs
            if 'watch' in parsed.path or 'shorts' in parsed.path:
                # Check for video ID parameter
                query_params = parse_qs(parsed.query)
                return 'v' in query_params or 'shorts' in parsed.path
            
            # Embed URLs
            if 'embed' in parsed.path:
                return len(parsed.path.split('/')) >= 3
            
            return False
            
        except Exception:
            return False
    
    async def extract_bulk_content(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Extract content from multiple YouTube URLs in bulk.
        
        Args:
            urls: List of YouTube URLs to extract from
            
        Returns:
            List of extracted content data
        """
        # Start progress tracking if available
        if self.progress_tracker:
            await self._start_progress(len(urls))
            await self._update_progress(ProgressStep.INITIALIZING, f"Initializing batch extraction for {len(urls)} URLs")
        
        results = []
        
        for i, url in enumerate(urls):
            try:
                if self.progress_tracker:
                    await self._update_progress(
                        ProgressStep.FETCHING_CONTENT, 
                        f"Processing URL {i+1}/{len(urls)}: {url}",
                        i / len(urls)
                    )
                
                content_data = await self.extract_content(url)
                results.append(content_data)
                
                # Update progress for this item
                if self.progress_tracker:
                    await self.progress_tracker.update_item_progress(
                        i + 1, 
                        f"Completed {i+1}/{len(urls)} URLs"
                    )
                
            except Exception as e:
                error_msg = f"Error extracting content from {url}: {e}"
                self.logger.error(error_msg)
                
                if self.progress_tracker:
                    await self._report_error(error_msg, warning=True)
                    
                results.append({
                    'url': url,
                    'error': str(e),
                    'status': 'failed'
                })
        
        # Complete progress tracking
        if self.progress_tracker:
            success_count = sum(1 for r in results if 'error' not in r)
            await self.progress_tracker.complete(
                success_count > 0,
                f"Completed batch extraction: {success_count}/{len(urls)} successful"
            )
        
        return results
    
    def _extract_video_id_from_url(self, url: str) -> str:
        """Extract YouTube video ID from URL."""
        try:
            parsed = urlparse(url)
            
            if parsed.netloc == 'youtu.be':
                # Short URL format
                return parsed.path[1:]  # Remove leading slash
            
            # Regular YouTube URLs
            if 'watch' in parsed.path:
                query_params = parse_qs(parsed.query)
                return query_params.get('v', [''])[0]
            
            # Shorts URLs
            if 'shorts' in parsed.path:
                return parsed.path.split('/')[-1]
            
            # Embed URLs
            if 'embed' in parsed.path:
                return parsed.path.split('/')[-1]
            
            return 'unknown'
            
        except Exception:
            return 'unknown'
    
    def _format_upload_date(self, upload_date: str) -> Optional[str]:
        """Format upload date from yt-dlp format to ISO format."""
        if not upload_date:
            return None
        
        try:
            # yt-dlp returns dates in YYYYMMDD format
            if len(upload_date) == 8:
                year = upload_date[:4]
                month = upload_date[4:6]
                day = upload_date[6:8]
                return f"{year}-{month}-{day}"
            return upload_date
        except Exception:
            return upload_date
    
    def _determine_content_type(self, info: Dict[str, Any]) -> ContentType:
        """Determine content type based on video info."""
        duration = info.get('duration', 0)
        
        # YouTube Shorts are typically under 60 seconds
        if duration and duration <= 60:
            return ContentType.VIDEO  # Could add SHORT_VIDEO type if needed
        
        return ContentType.VIDEO
    
    def _extract_format_info(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract format information from video info."""
        formats = info.get('formats', [])
        if not formats:
            return {}
        
        # Get the best format
        best_format = formats[-1] if formats else {}
        
        return {
            'resolution': f"{best_format.get('width', 0)}x{best_format.get('height', 0)}",
            'fps': best_format.get('fps', 0),
            'video_codec': best_format.get('vcodec', 'unknown'),
            'audio_codec': best_format.get('acodec', 'unknown'),
            'filesize': best_format.get('filesize', 0)
        }
    
    def _extract_media_urls(self, info: Dict[str, Any]) -> List[str]:
        """Extract media URLs from video info."""
        media_urls = []
        
        # Add video URL
        if info.get('url'):
            media_urls.append(info['url'])
        
        # Add thumbnail URL
        if info.get('thumbnail'):
            media_urls.append(info['thumbnail'])
        
        return media_urls


# Global instance for easy access
youtube_downloader = YouTubeDownloader() 