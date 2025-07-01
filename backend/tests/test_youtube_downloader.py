"""
Unit tests for YouTube Content Downloader
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
from datetime import datetime

from services.youtube_downloader import YouTubeDownloader
from db.models import PlatformType, ContentType
from services.progress_tracker import ProgressTracker, ProgressStep


class TestYouTubeDownloader:
    """Test cases for YouTube content downloader"""
    
    @pytest.fixture
    def downloader(self):
        """Create YouTube downloader instance for testing"""
        return YouTubeDownloader()
    
    @pytest.fixture
    def downloader_with_progress(self):
        """Create YouTube downloader instance with progress tracker for testing"""
        mock_progress_tracker = AsyncMock(spec=ProgressTracker)
        return YouTubeDownloader(progress_tracker=mock_progress_tracker)
    
    @pytest.fixture
    def mock_video_info(self):
        """Mock video information from yt-dlp"""
        return {
            'id': 'dQw4w9WgXcQ',
            'title': 'Rick Astley - Never Gonna Give You Up (Official Music Video)',
            'description': 'The official video for "Never Gonna Give You Up" by Rick Astley',
            'duration': 212,
            'view_count': 1500000000,
            'like_count': 15000000,
            'comment_count': 2500000,
            'uploader': 'Rick Astley',
            'uploader_id': 'RickAstleyYT',
            'upload_date': '20091025',
            'thumbnail': 'https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg',
            'webpage_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'url': 'https://youtube.com/watch?v=dQw4w9WgXcQ',
            'formats': [{
                'format_id': '22',
                'ext': 'mp4',
                'width': 1280,
                'height': 720,
                'fps': 30,
                'vcodec': 'avc1.640028',
                'acodec': 'mp4a.40.2',
                'filesize': 52428800
            }, {
                'format_id': '18',
                'ext': 'mp4',
                'width': 640,
                'height': 360,
                'fps': 30,
                'vcodec': 'avc1.42001E',
                'acodec': 'mp4a.40.2',
                'filesize': 26214400
            }],
            'subtitles': {
                'en': [{'url': 'https://example.com/subtitles.vtt'}]
            },
            'automatic_captions': {
                'en': [{'url': 'https://example.com/auto_captions.vtt'}]
            }
        }
    
    @pytest.fixture
    def mock_shorts_info(self):
        """Mock YouTube Shorts information"""
        return {
            'id': 'abc123xyz',
            'title': 'Amazing Short Video',
            'description': 'A cool YouTube Short',
            'duration': 45,
            'view_count': 100000,
            'like_count': 5000,
            'uploader': 'Creator Name',
            'uploader_id': 'creator123',
            'upload_date': '20240101',
            'thumbnail': 'https://i.ytimg.com/vi/abc123xyz/maxresdefault.jpg',
            'webpage_url': 'https://www.youtube.com/shorts/abc123xyz',
            'formats': [{
                'format_id': '22',
                'ext': 'mp4',
                'width': 1080,
                'height': 1920,
                'fps': 30,
                'vcodec': 'avc1.640028',
                'acodec': 'mp4a.40.2',
                'filesize': 15728640
            }]
        }
    
    def test_initialization(self, downloader):
        """Test downloader initialization"""
        assert downloader.platform == PlatformType.YOUTUBE
        assert downloader.download_base == Path("downloads/youtube")
        assert downloader.rate_limiter is not None
        assert 'quiet' in downloader.ydl_opts
        assert downloader.ydl_opts['writethumbnail'] is True
        assert downloader.ydl_opts['writesubtitles'] is True
    
    def test_initialization_with_progress_tracker(self, downloader_with_progress):
        """Test downloader initialization with progress tracker"""
        assert downloader_with_progress.platform == PlatformType.YOUTUBE
        assert downloader_with_progress.progress_tracker is not None
    
    def test_get_platform_domains(self, downloader):
        """Test platform domain validation"""
        domains = downloader.get_platform_domains()
        expected_domains = [
            'youtube.com',
            'www.youtube.com',
            'm.youtube.com',
            'youtu.be',
            'music.youtube.com'
        ]
        assert all(domain in domains for domain in expected_domains)
    
    @pytest.mark.parametrize("url,expected", [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", True),
        ("https://youtube.com/watch?v=dQw4w9WgXcQ", True),
        ("https://youtu.be/dQw4w9WgXcQ", True),
        ("https://www.youtube.com/shorts/abc123xyz", True),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", True),
        ("https://music.youtube.com/watch?v=dQw4w9WgXcQ", True),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", True),
        ("https://example.com/video", False),
        ("https://vimeo.com/123456", False),
        ("invalid-url", False),
        ("", False),
    ])
    def test_validate_url(self, downloader, url, expected):
        """Test URL validation for various YouTube URL formats"""
        assert downloader.validate_url(url) == expected
    
    @pytest.mark.parametrize("url,expected_id", [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/abc123xyz", "abc123xyz"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("invalid-url", "unknown"),
    ])
    def test_extract_video_id_from_url(self, downloader, url, expected_id):
        """Test video ID extraction from various URL formats"""
        assert downloader._extract_video_id_from_url(url) == expected_id
    
    def test_format_upload_date(self, downloader):
        """Test upload date formatting"""
        assert downloader._format_upload_date("20091025") == "2009-10-25"
        assert downloader._format_upload_date("20240101") == "2024-01-01"
        assert downloader._format_upload_date(None) is None
        assert downloader._format_upload_date("") is None
        assert downloader._format_upload_date("invalid") == "invalid"
    
    def test_determine_content_type(self, downloader, mock_video_info, mock_shorts_info):
        """Test content type determination"""
        # Regular video (> 60 seconds)
        assert downloader._determine_content_type(mock_video_info) == ContentType.VIDEO
        
        # Short video (< 60 seconds)
        assert downloader._determine_content_type(mock_shorts_info) == ContentType.VIDEO
        
        # Video with no duration
        assert downloader._determine_content_type({}) == ContentType.VIDEO
    
    def test_extract_format_info(self, downloader, mock_video_info):
        """Test format information extraction"""
        format_info = downloader._extract_format_info(mock_video_info)
        
        assert format_info['resolution'] == '1280x720'
        assert format_info['fps'] == 30
        assert format_info['video_codec'] == 'avc1.640028'
        assert format_info['audio_codec'] == 'mp4a.40.2'
        assert format_info['filesize'] == 52428800
        
        # Test with empty formats
        empty_info = downloader._extract_format_info({'formats': []})
        assert empty_info == {}
    
    def test_extract_media_urls(self, downloader, mock_video_info):
        """Test media URL extraction"""
        media_urls = downloader._extract_media_urls(mock_video_info)
        
        assert 'https://youtube.com/watch?v=dQw4w9WgXcQ' in media_urls
        assert 'https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg' in media_urls
    
    def test_get_available_formats(self, downloader, mock_video_info):
        """Test available formats extraction"""
        formats = downloader._get_available_formats(mock_video_info)
        
        assert len(formats) == 2
        assert formats[0]['format_id'] == '22'
        assert formats[0]['resolution'] == '1280x720'
        assert formats[1]['format_id'] == '18'
        assert formats[1]['resolution'] == '640x360'
    
    def test_get_format_for_quality(self, downloader):
        """Test format selection based on quality"""
        assert downloader._get_format_for_quality('low') == 'worst[height>=240]'
        assert downloader._get_format_for_quality('medium') == 'best[height<=480]'
        assert downloader._get_format_for_quality('high') == 'best[height<=720]'
        assert downloader._get_format_for_quality('best') == 'best'
        assert downloader._get_format_for_quality('invalid') == 'best[height<=720]'
    
    @pytest.mark.asyncio
    async def test_extract_content_success(self, downloader, mock_video_info):
        """Test successful content extraction"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        with patch('services.youtube_downloader.YoutubeDL') as mock_ydl_class:
            mock_ydl = Mock()
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            
            with patch.object(downloader.rate_limiter, 'wait', new_callable=AsyncMock):
                result = await downloader.extract_content(url)
        
        assert result['url'] == url
        assert result['platform'] == PlatformType.YOUTUBE
        assert result['title'] == 'Rick Astley - Never Gonna Give You Up (Official Music Video)'
        assert result['video_id'] == 'dQw4w9WgXcQ'
        assert result['duration'] == 212
        assert result['view_count'] == 1500000000
        assert result['like_count'] == 15000000
        assert result['channel'] == 'Rick Astley'
        assert result['upload_date'] == '2009-10-25'
        assert result['content_type'] == ContentType.VIDEO
        assert 'engagement_metrics' in result
        assert result['engagement_metrics']['views'] == 1500000000
        assert 'available_formats' in result
        assert len(result['available_formats']) == 2
    
    @pytest.mark.asyncio
    async def test_extract_content_with_progress_tracking(self, downloader_with_progress, mock_video_info):
        """Test content extraction with progress tracking"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        with patch('services.youtube_downloader.YoutubeDL') as mock_ydl_class:
            mock_ydl = Mock()
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            
            with patch.object(downloader_with_progress.rate_limiter, 'wait', new_callable=AsyncMock):
                result = await downloader_with_progress.extract_content(url)
        
        # Verify progress tracking calls
        progress_tracker = downloader_with_progress.progress_tracker
        assert progress_tracker._start_progress.called
        assert progress_tracker.update_step.called
        assert progress_tracker.complete.called
        
        # Check that all steps were tracked
        step_calls = [call[0][0] for call in progress_tracker.update_step.call_args_list]
        assert ProgressStep.INITIALIZING in step_calls
        assert ProgressStep.VALIDATING_URL in step_calls
        assert ProgressStep.FETCHING_CONTENT in step_calls
        assert ProgressStep.PARSING_CONTENT in step_calls
        assert ProgressStep.FINALIZING in step_calls
    
    @pytest.mark.asyncio
    async def test_extract_content_invalid_url(self, downloader):
        """Test content extraction with invalid URL"""
        url = "https://example.com/not-youtube"
        
        with pytest.raises(ValueError, match="Invalid YouTube URL"):
            await downloader.extract_content(url)
    
    @pytest.mark.asyncio
    async def test_extract_content_yt_dlp_error(self, downloader):
        """Test content extraction when yt-dlp fails"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        with patch('services.youtube_downloader.YoutubeDL') as mock_ydl_class:
            mock_ydl = Mock()
            mock_ydl.extract_info.side_effect = Exception("Network error")
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            
            with patch.object(downloader.rate_limiter, 'wait', new_callable=AsyncMock):
                result = await downloader.extract_content(url)
        
        assert result['url'] == url
        assert result['error'] == "Network error"
        assert result['video_id'] == 'dQw4w9WgXcQ'
        assert result['title'] == 'YouTube Video'
        assert result['description'] == 'Error extracting content'
    
    @pytest.mark.asyncio
    async def test_download_content_success(self, downloader, mock_video_info):
        """Test successful content download"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = "dQw4w9WgXcQ"
        
        with patch('pathlib.Path.mkdir'), \
             patch('services.youtube_downloader.YoutubeDL') as mock_ydl_class, \
             patch('aiofiles.open', new_callable=AsyncMock) as mock_aiofiles:
            
            # Setup mock file objects
            mock_video_file = Mock()
            mock_video_file.stat.return_value.st_size = 52428800
            mock_video_file.suffix = '.mp4'
            mock_video_file.__str__ = lambda self: f'/path/to/{video_id}.mp4'

            mock_thumbnail_file = Mock()
            mock_thumbnail_file.stat.return_value.st_size = 1024000
            mock_thumbnail_file.suffix = '.jpg'
            mock_thumbnail_file.__str__ = lambda self: f'/path/to/{video_id}_thumbnail.jpg'

            mock_subtitle_file = Mock()
            mock_subtitle_file.stat.return_value.st_size = 50000
            mock_subtitle_file.suffix = '.vtt'
            mock_subtitle_file.stem = f'{video_id}_en'
            mock_subtitle_file.__str__ = lambda self: f'/path/to/{video_id}_en.vtt'
            
            # Setup mock directory objects
            mock_video_dir = Mock()
            mock_image_dir = Mock()
            mock_text_dir = Mock()
            
            # Setup mock YoutubeDL
            mock_ydl = Mock()
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            
            # Setup mock Path.glob
            video_glob_called = False
            image_glob_called = False
            subtitle_glob_called = False
            
            def video_glob_effect(pattern):
                nonlocal video_glob_called
                if not video_glob_called:
                    video_glob_called = True
                    return [mock_video_file]
                return []
                
            def image_glob_effect(pattern):
                nonlocal image_glob_called
                if not image_glob_called:
                    image_glob_called = True
                    return [mock_thumbnail_file]
                return []
                
            def text_glob_effect(pattern):
                nonlocal subtitle_glob_called
                if ("*.vtt" in str(pattern) or "*.srt" in str(pattern)) and not subtitle_glob_called:
                    subtitle_glob_called = True
                    return [mock_subtitle_file]
                return []
            
            # Setup mock _get_download_directory
            with patch.object(downloader, '_get_download_directory') as mock_get_dir:
                mock_get_dir.side_effect = lambda video_id, file_type: {
                    'video': mock_video_dir,
                    'image': mock_image_dir,
                    'text': mock_text_dir
                }.get(file_type)
                
                mock_video_dir.glob.side_effect = video_glob_effect
                mock_image_dir.glob.side_effect = image_glob_effect
                mock_text_dir.glob.side_effect = text_glob_effect
                
                # Mock metadata file
                mock_metadata_file = MagicMock()
                mock_metadata_file.stat.return_value.st_size = 5000
                mock_text_dir.__truediv__ = MagicMock(return_value=mock_metadata_file)
                
                # Mock file write
                mock_file = AsyncMock()
                mock_aiofiles.return_value.__aenter__.return_value = mock_file
                
                with patch.object(downloader.rate_limiter, 'wait', new_callable=AsyncMock):
                    result = await downloader.download_content(url, quality='high')
        
        assert result['video_id'] == video_id
        assert result['url'] == url
        assert 'downloads' in result
        assert result['downloads']['video']['success'] is True
        assert result['downloads']['thumbnail']['success'] is True
        assert len(result['downloads']['subtitles']) == 1
        assert result['downloads']['subtitles'][0]['language'] == 'en'
        assert result['downloads']['metadata']['success'] is True
        assert len(result['errors']) == 0
        
        # Verify format selection was used
        format_arg = mock_ydl_class.call_args[0][0]['format']
        assert format_arg == 'best[height<=720]'  # high quality
    
    @pytest.mark.asyncio
    async def test_download_content_with_format_id(self, downloader, mock_video_info):
        """Test download with specific format ID"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        with patch('pathlib.Path.mkdir'), \
             patch('services.youtube_downloader.YoutubeDL') as mock_ydl_class, \
             patch('aiofiles.open', new_callable=AsyncMock), \
             patch.object(downloader, '_get_download_directory') as mock_get_dir:
            
            # Setup mocks
            mock_dir = Mock()
            mock_dir.glob.return_value = []
            mock_get_dir.return_value = mock_dir
            
            mock_ydl = Mock()
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            
            with patch.object(downloader.rate_limiter, 'wait', new_callable=AsyncMock):
                await downloader.download_content(url, format_id='22')
        
        # Verify format ID was used
        format_arg = mock_ydl_class.call_args[0][0]['format']
        assert format_arg == '22'
    
    @pytest.mark.asyncio
    async def test_download_content_with_progress_tracking(self, downloader_with_progress, mock_video_info):
        """Test download with progress tracking"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        with patch('pathlib.Path.mkdir'), \
             patch('services.youtube_downloader.YoutubeDL') as mock_ydl_class, \
             patch('aiofiles.open', new_callable=AsyncMock), \
             patch.object(downloader_with_progress, '_get_download_directory') as mock_get_dir:
            
            # Setup mocks
            mock_dir = Mock()
            mock_dir.glob.return_value = []
            mock_get_dir.return_value = mock_dir
            
            mock_ydl = Mock()
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            
            with patch.object(downloader_with_progress.rate_limiter, 'wait', new_callable=AsyncMock):
                await downloader_with_progress.download_content(url)
        
        # Verify progress tracking calls
        progress_tracker = downloader_with_progress.progress_tracker
        assert progress_tracker._start_progress.called
        assert progress_tracker.update_step.called
        assert progress_tracker.complete.called
        
        # Check that all steps were tracked
        step_calls = [call[0][0] for call in progress_tracker.update_step.call_args_list]
        assert ProgressStep.INITIALIZING in step_calls
        assert ProgressStep.VALIDATING_URL in step_calls
        assert ProgressStep.FETCHING_CONTENT in step_calls
        assert ProgressStep.DOWNLOADING_FILES in step_calls
        assert ProgressStep.FINALIZING in step_calls
    
    @pytest.mark.asyncio
    async def test_download_content_invalid_url(self, downloader):
        """Test download with invalid URL"""
        url = "https://example.com/not-youtube"
        
        with pytest.raises(ValueError, match="Invalid YouTube URL"):
            await downloader.download_content(url)
    
    @pytest.mark.asyncio
    async def test_download_content_yt_dlp_error(self, downloader):
        """Test download when yt-dlp fails"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        with patch('pathlib.Path.mkdir'), \
             patch('services.youtube_downloader.YoutubeDL') as mock_ydl_class:
            
            mock_ydl = Mock()
            mock_ydl.extract_info.side_effect = Exception("Download failed")
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            
            with patch.object(downloader.rate_limiter, 'wait', new_callable=AsyncMock):
                result = await downloader.download_content(url)
        
        assert result['video_id'] == 'dQw4w9WgXcQ'
        assert result['url'] == url
        assert len(result['errors']) == 1
        assert "Download failed" in result['errors'][0]
    
    @pytest.mark.asyncio
    async def test_extract_bulk_content(self, downloader, mock_video_info):
        """Test bulk content extraction"""
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/abc123xyz",
            "https://invalid.com/video"  # This should fail
        ]
        
        with patch('services.youtube_downloader.YoutubeDL') as mock_ydl_class:
            mock_ydl = Mock()
            
            def extract_info_side_effect(url, download=False):
                if 'dQw4w9WgXcQ' in url:
                    return mock_video_info
                elif 'abc123xyz' in url:
                    return {**mock_video_info, 'id': 'abc123xyz', 'title': 'Another Video'}
                else:
                    raise Exception("Invalid URL")
            
            mock_ydl.extract_info.side_effect = extract_info_side_effect
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            
            with patch.object(downloader.rate_limiter, 'wait', new_callable=AsyncMock):
                results = await downloader.extract_bulk_content(urls)
        
        assert len(results) == 3
        assert results[0]['video_id'] == 'dQw4w9WgXcQ'
        assert results[1]['video_id'] == 'abc123xyz'
        assert 'error' in results[2]
        assert results[2]['status'] == 'failed'
    
    @pytest.mark.asyncio
    async def test_extract_bulk_content_with_progress_tracking(self, downloader_with_progress, mock_video_info):
        """Test bulk content extraction with progress tracking"""
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/abc123xyz"
        ]
        
        with patch('services.youtube_downloader.YoutubeDL') as mock_ydl_class:
            mock_ydl = Mock()
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            
            with patch.object(downloader_with_progress.rate_limiter, 'wait', new_callable=AsyncMock):
                results = await downloader_with_progress.extract_bulk_content(urls)
        
        # Verify progress tracking calls
        progress_tracker = downloader_with_progress.progress_tracker
        assert progress_tracker._start_progress.called_with(2)  # 2 URLs
        assert progress_tracker.update_step.called
        assert progress_tracker.update_item_progress.called
        assert progress_tracker.complete.called
        
        # Check that all steps were tracked
        step_calls = [call[0][0] for call in progress_tracker.update_step.call_args_list]
        assert ProgressStep.INITIALIZING in step_calls
        assert ProgressStep.FETCHING_CONTENT in step_calls
    
    def test_youtube_shorts_url_validation(self, downloader):
        """Test validation of YouTube Shorts URLs"""
        shorts_urls = [
            "https://www.youtube.com/shorts/abc123xyz",
            "https://youtube.com/shorts/def456uvw",
            "https://m.youtube.com/shorts/ghi789rst"
        ]
        
        for url in shorts_urls:
            assert downloader.validate_url(url) is True
    
    def test_progress_hook(self, downloader_with_progress):
        """Test progress hook for yt-dlp"""
        # Test downloading status with total bytes
        download_info = {
            'status': 'downloading',
            'filename': 'test.mp4',
            'downloaded_bytes': 5242880,  # 5MB
            'total_bytes': 10485760,  # 10MB
        }
        
        with patch('asyncio.create_task') as mock_create_task:
            downloader_with_progress._progress_hook(download_info)
            assert mock_create_task.called
        
        # Test downloading status with estimated total bytes
        download_info = {
            'status': 'downloading',
            'filename': 'test.mp4',
            'downloaded_bytes': 5242880,  # 5MB
            'total_bytes_estimate': 10485760,  # 10MB (estimated)
        }
        
        with patch('asyncio.create_task') as mock_create_task:
            downloader_with_progress._progress_hook(download_info)
            assert mock_create_task.called
        
        # Test downloading status without size info
        download_info = {
            'status': 'downloading',
            'filename': 'test.mp4',
            'downloaded_bytes': 5242880,  # 5MB
        }
        
        with patch('asyncio.create_task') as mock_create_task:
            downloader_with_progress._progress_hook(download_info)
            assert mock_create_task.called
        
        # Test finished status
        download_info = {
            'status': 'finished',
            'filename': 'test.mp4',
        }
        
        with patch('asyncio.create_task') as mock_create_task:
            downloader_with_progress._progress_hook(download_info)
            assert mock_create_task.called
        
        # Test error status
        download_info = {
            'status': 'error',
            'error': 'Connection failed',
        }
        
        with patch('asyncio.create_task') as mock_create_task:
            downloader_with_progress._progress_hook(download_info)
            assert mock_create_task.called
    
    def test_global_instance_creation(self):
        """Test that global instance is created properly"""
        from services.youtube_downloader import youtube_downloader
        
        assert isinstance(youtube_downloader, YouTubeDownloader)
        assert youtube_downloader.platform == PlatformType.YOUTUBE 