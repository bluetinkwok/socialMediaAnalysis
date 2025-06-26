"""
Storage service for managing content data and file storage integration.
Handles storing extracted content from downloaders into SQLite database and file system.
"""

import asyncio
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .database import get_database
from .models import (
    Post, MediaFile, DownloadJob, Platform,
    PlatformType, ContentType, DownloadStatus
)
from core.config import settings

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Custom exception for storage operations"""
    pass


class StorageService:
    """
    Service for managing content storage operations.
    Handles both database operations and file system management.
    """
    
    def __init__(self, base_storage_path: Optional[str] = None):
        """
        Initialize storage service.
        
        Args:
            base_storage_path: Base path for file storage (defaults to config setting)
        """
        self.base_storage_path = Path(base_storage_path or settings.downloads_path)
        self.base_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Create platform-specific directories
        for platform in PlatformType:
            platform_dir = self.base_storage_path / platform.value
            platform_dir.mkdir(exist_ok=True)
            
            # Create subdirectories for different file types
            for subdir in ['videos', 'images', 'text', 'metadata']:
                (platform_dir / subdir).mkdir(exist_ok=True)
    
    async def store_extracted_content(
        self, 
        content_data: Dict[str, Any], 
        db: Session
    ) -> Optional[Post]:
        """
        Store extracted content from downloader into database.
        
        Args:
            content_data: Content data from downloader extract_content() method
            db: Database session
            
        Returns:
            Created Post object or None if storage failed
        """
        try:
            if not content_data.get('success', False):
                logger.warning(f"Skipping failed extraction: {content_data.get('error', 'Unknown error')}")
                return None
            
            # Parse platform
            platform_str = content_data.get('platform', '').lower()
            try:
                platform = PlatformType(platform_str)
            except ValueError:
                logger.error(f"Unsupported platform: {platform_str}")
                return None
            
            # Parse content type
            content_type_str = content_data.get('content_type', 'text').lower()
            try:
                content_type = ContentType(content_type_str)
            except ValueError:
                logger.warning(f"Unknown content type: {content_type_str}, defaulting to TEXT")
                content_type = ContentType.TEXT
            
            # Check if post already exists
            existing_post = db.query(Post).filter(Post.url == content_data['url']).first()
            if existing_post:
                logger.info(f"Post already exists for URL: {content_data['url']}")
                return existing_post
            
            # Extract author information
            author = content_data.get('username') or content_data.get('author') or 'Unknown'
            author_id = content_data.get('author_id') or content_data.get('username')
            
            # Create post record
            post = Post(
                platform=platform,
                content_type=content_type,
                url=content_data['url'],
                title=self._extract_title(content_data),
                description=content_data.get('description', ''),
                content_text=content_data.get('text', ''),
                author=author,
                author_id=author_id,
                author_avatar=content_data.get('author_avatar'),
                thumbnail=content_data.get('thumbnail'),
                duration=content_data.get('duration'),
                hashtags=content_data.get('hashtags', []),
                mentions=content_data.get('mentions', []),
                engagement_metrics=content_data.get('engagement_metrics', {}),
                publish_date=self._parse_publish_date(content_data),
                download_date=datetime.now(timezone.utc)
            )
            
            db.add(post)
            db.flush()  # Get the post ID without committing
            
            # Store media files if any
            await self._store_media_files(content_data, post, db)
            
            db.commit()
            logger.info(f"Successfully stored content for URL: {content_data['url']}")
            return post
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to store content: {str(e)}")
            raise StorageError(f"Content storage failed: {str(e)}")
    
    async def store_downloaded_content(
        self, 
        download_result: Dict[str, Any], 
        db: Session
    ) -> Optional[Post]:
        """
        Store downloaded content (including files) into database and organize files.
        
        Args:
            download_result: Result from downloader download_content() method
            db: Database session
            
        Returns:
            Created/updated Post object or None if storage failed
        """
        try:
            # First store the basic content
            post = await self.store_extracted_content(download_result, db)
            if not post:
                return None
            
            # Handle downloaded files
            if download_result.get('downloaded', False):
                await self._organize_downloaded_files(download_result, post, db)
            
            db.commit()
            return post
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to store downloaded content: {str(e)}")
            raise StorageError(f"Downloaded content storage failed: {str(e)}")
    
    def get_platform_storage_path(self, platform: PlatformType, file_type: str = 'metadata') -> Path:
        """
        Get storage path for a specific platform and file type.
        
        Args:
            platform: Platform type
            file_type: Type of file (videos, images, text, metadata)
            
        Returns:
            Path to storage directory
        """
        path = self.base_storage_path / platform.value / file_type
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def _extract_title(self, content_data: Dict[str, Any]) -> str:
        """Extract title from content data."""
        # Try different title fields
        title = content_data.get('title')
        if title:
            return title[:500]  # Limit title length
        
        # Fallback to truncated text content
        text = content_data.get('text', '')
        if text:
            return text[:100] + '...' if len(text) > 100 else text
        
        # Fallback to URL-based title
        url = content_data.get('url', '')
        parsed_url = urlparse(url)
        return f"Content from {parsed_url.netloc}" if parsed_url.netloc else "Untitled Content"
    
    def _parse_publish_date(self, content_data: Dict[str, Any]) -> Optional[datetime]:
        """Parse publish date from content data."""
        date_str = content_data.get('publish_date') or content_data.get('upload_date')
        if not date_str:
            return None
        
        try:
            # Handle various date formats
            if isinstance(date_str, str):
                # ISO format
                if 'T' in date_str:
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                # Simple date format YYYY-MM-DD
                elif '-' in date_str:
                    return datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            
            return None
        except Exception:
            logger.warning(f"Failed to parse publish date: {date_str}")
            return None
    
    async def _store_media_files(
        self, 
        content_data: Dict[str, Any], 
        post: Post, 
        db: Session
    ) -> None:
        """Store media file references from content data."""
        media_urls = content_data.get('media_urls', [])
        
        for i, media_url in enumerate(media_urls):
            try:
                # Determine file type from URL or content
                file_type = self._detect_file_type(media_url)
                filename = f"{post.platform.value}_{post.id}_media_{i}.{file_type}"
                
                media_file = MediaFile(
                    post_id=post.id,
                    filename=filename,
                    file_path=media_url,  # Store original URL for now
                    file_type=file_type,
                    mime_type=self._get_mime_type(file_type)
                )
                
                db.add(media_file)
                
            except Exception as e:
                logger.warning(f"Failed to store media file reference: {str(e)}")
    
    async def _organize_downloaded_files(
        self, 
        download_result: Dict[str, Any], 
        post: Post, 
        db: Session
    ) -> None:
        """Organize downloaded files and update database records."""
        try:
            # Handle single file download (like Threads JSON)
            if 'file_path' in download_result:
                await self._move_and_register_file(
                    download_result['file_path'],
                    post,
                    'metadata',
                    db
                )
            
            # Handle multiple downloads (like YouTube)
            downloads = download_result.get('downloads', {})
            if isinstance(downloads, dict):
                # YouTube-style downloads with different file types
                for file_type, file_info in downloads.items():
                    if isinstance(file_info, dict) and file_info.get('success'):
                        await self._move_and_register_file(
                            file_info['file_path'],
                            post,
                            file_type,
                            db
                        )
                    elif isinstance(file_info, list):
                        # Handle lists like subtitles
                        for item in file_info:
                            if isinstance(item, dict) and item.get('success'):
                                await self._move_and_register_file(
                                    item['file_path'],
                                    post,
                                    file_type,
                                    db
                                )
                                
        except Exception as e:
            logger.error(f"Failed to organize downloaded files: {str(e)}")
    
    async def _move_and_register_file(
        self, 
        source_path: str, 
        post: Post, 
        file_type: str, 
        db: Session
    ) -> None:
        """Move file to organized storage and register in database."""
        try:
            source = Path(source_path)
            if not source.exists():
                logger.warning(f"Source file does not exist: {source_path}")
                return
            
            # Determine target directory based on file type
            storage_type = self._map_file_type_to_storage(file_type)
            target_dir = self.get_platform_storage_path(post.platform, storage_type)
            
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{post.platform.value}_{post.id}_{timestamp}_{source.name}"
            target_path = target_dir / filename
            
            # Move file
            shutil.move(str(source), str(target_path))
            
            # Register in database
            media_file = MediaFile(
                post_id=post.id,
                filename=filename,
                file_path=str(target_path),
                file_type=file_type,
                file_size=target_path.stat().st_size,
                mime_type=self._get_mime_type(source.suffix)
            )
            
            db.add(media_file)
            logger.info(f"Moved and registered file: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to move and register file {source_path}: {str(e)}")
    
    def _detect_file_type(self, url_or_path: str) -> str:
        """Detect file type from URL or path."""
        path = Path(url_or_path)
        extension = path.suffix.lower().lstrip('.')
        
        video_extensions = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'}
        image_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'}
        text_extensions = {'txt', 'json', 'xml', 'csv', 'srt', 'vtt'}
        
        if extension in video_extensions:
            return 'video'
        elif extension in image_extensions:
            return 'image'
        elif extension in text_extensions:
            return 'text'
        else:
            return 'unknown'
    
    def _map_file_type_to_storage(self, file_type: str) -> str:
        """Map file type to storage directory."""
        mapping = {
            'video': 'videos',
            'thumbnail': 'images',
            'image': 'images',
            'subtitles': 'text',
            'metadata': 'metadata',
            'text': 'text'
        }
        return mapping.get(file_type, 'metadata')
    
    def _get_mime_type(self, extension: str) -> str:
        """Get MIME type for file extension."""
        extension = extension.lower().lstrip('.')
        
        mime_types = {
            'mp4': 'video/mp4',
            'avi': 'video/x-msvideo',
            'mov': 'video/quicktime',
            'mkv': 'video/x-matroska',
            'webm': 'video/webm',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'json': 'application/json',
            'txt': 'text/plain',
            'srt': 'text/plain',
            'vtt': 'text/vtt'
        }
        
        return mime_types.get(extension, 'application/octet-stream')


# Convenience functions for easy usage
async def store_content(content_data: Dict[str, Any], db: Session = None) -> Optional[Post]:
    """
    Convenience function to store extracted content.
    
    Args:
        content_data: Content data from downloader
        db: Database session (optional)
        
    Returns:
        Created Post object or None
    """
    if db is None:
        db = next(get_database())
    
    storage = StorageService()
    return await storage.store_extracted_content(content_data, db)


async def store_download(download_result: Dict[str, Any], db: Session = None) -> Optional[Post]:
    """
    Convenience function to store downloaded content.
    
    Args:
        download_result: Download result from downloader
        db: Database session (optional)
        
    Returns:
        Created Post object or None
    """
    if db is None:
        db = next(get_database())
    
    storage = StorageService()
    return await storage.store_downloaded_content(download_result, db)