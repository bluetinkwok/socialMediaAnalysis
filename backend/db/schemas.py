"""
Pydantic schemas for Social Media Analysis Platform
"""

from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class PlatformType(str, Enum):
    """Supported social media platforms"""
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    THREADS = "threads"
    REDNOTE = "rednote"


class ContentType(str, Enum):
    """Types of content"""
    VIDEO = "video"
    IMAGE = "image"
    TEXT = "text"
    MIXED = "mixed"


class DownloadStatus(str, Enum):
    """Download job status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PROCESSING = "processing"  # Keep for backward compatibility
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    model_config = ConfigDict(from_attributes=True)


# Platform schemas
class PlatformBase(BaseSchema):
    name: str = Field(..., max_length=50)
    display_name: str = Field(..., max_length=100)
    is_active: bool = True
    base_url: Optional[str] = Field(None, max_length=255)


class PlatformCreate(PlatformBase):
    pass


class PlatformUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=50)
    display_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    base_url: Optional[str] = Field(None, max_length=255)


class Platform(PlatformBase):
    id: int
    created_at: datetime
    updated_at: datetime


# Engagement metrics schema
class EngagementMetrics(BaseSchema):
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    saves: Optional[int] = None
    retweets: Optional[int] = None
    reactions: Optional[Dict[str, int]] = None


# Media file schemas
class MediaFileBase(BaseSchema):
    filename: str = Field(..., max_length=255)
    file_path: str = Field(..., max_length=2048)
    file_type: str = Field(..., max_length=50)
    file_size: Optional[int] = None
    mime_type: Optional[str] = Field(None, max_length=100)
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None


class MediaFileCreate(MediaFileBase):
    post_id: int


class MediaFile(MediaFileBase):
    id: int
    post_id: int
    created_at: datetime
    updated_at: datetime


# Post schemas
class PostBase(BaseSchema):
    platform: PlatformType
    content_type: ContentType
    url: str = Field(..., max_length=2048)
    title: str
    description: Optional[str] = None
    content_text: Optional[str] = None
    author: str = Field(..., max_length=255)
    author_id: Optional[str] = Field(None, max_length=255)
    author_avatar: Optional[str] = Field(None, max_length=2048)
    thumbnail: Optional[str] = Field(None, max_length=2048)
    duration: Optional[int] = None
    hashtags: Optional[List[str]] = []
    mentions: Optional[List[str]] = []
    engagement_metrics: Optional[EngagementMetrics] = None
    publish_date: Optional[datetime] = None


class PostCreate(PostBase):
    platform_id: Optional[int] = None


class PostUpdate(BaseSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    content_text: Optional[str] = None
    author: Optional[str] = Field(None, max_length=255)
    author_id: Optional[str] = Field(None, max_length=255)
    author_avatar: Optional[str] = Field(None, max_length=2048)
    thumbnail: Optional[str] = Field(None, max_length=2048)
    duration: Optional[int] = None
    hashtags: Optional[List[str]] = None
    mentions: Optional[List[str]] = None
    engagement_metrics: Optional[EngagementMetrics] = None
    publish_date: Optional[datetime] = None
    is_analyzed: Optional[bool] = None
    performance_score: Optional[float] = None


class Post(PostBase):
    id: int
    platform_id: Optional[int] = None
    is_analyzed: bool = False
    performance_score: Optional[float] = None
    download_date: datetime
    created_at: datetime
    updated_at: datetime
    
    # Related data
    files: List[MediaFile] = []


class PostWithAnalytics(Post):
    """Post with analytics data included"""
    analytics: Optional['AnalyticsData'] = None


# Download job schemas
class DownloadOptions(BaseSchema):
    include_comments: bool = False
    max_quality: str = Field(default="high", pattern="^(low|medium|high)$")
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    max_items: Optional[int] = Field(None, gt=0, le=1000)


class DownloadJobBase(BaseSchema):
    platform: PlatformType
    urls: List[str] = Field(..., min_length=1)
    download_options: Optional[DownloadOptions] = None


class DownloadJobCreate(DownloadJobBase):
    pass


class DownloadJobUpdate(BaseSchema):
    status: Optional[DownloadStatus] = None
    total_items: Optional[int] = None
    processed_items: Optional[int] = None
    progress_percentage: Optional[float] = Field(None, ge=0, le=100)
    errors: Optional[List[str]] = None
    error_count: Optional[int] = None


class DownloadJob(DownloadJobBase):
    id: int
    job_id: str
    status: DownloadStatus
    total_items: int = 0
    processed_items: int = 0
    progress_percentage: float = 0.0
    errors: List[str] = []
    error_count: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime


# Analytics schemas
class AnalyticsDataBase(BaseSchema):
    engagement_rate: Optional[float] = None
    virality_score: Optional[float] = None
    performance_score: Optional[float] = None
    trend_score: Optional[float] = None
    platform_rank: Optional[int] = None
    category_rank: Optional[int] = None
    peak_engagement_hour: Optional[int] = Field(None, ge=0, le=23)
    engagement_velocity: Optional[float] = None
    success_patterns: Optional[List[str]] = []
    content_features: Optional[Dict[str, Any]] = {}


class AnalyticsDataCreate(AnalyticsDataBase):
    post_id: int


class AnalyticsData(AnalyticsDataBase):
    id: int
    post_id: int
    analyzed_at: datetime
    created_at: datetime
    updated_at: datetime


# Trend data schemas
class TrendDataBase(BaseSchema):
    trend_type: str = Field(..., max_length=50)
    trend_value: str = Field(..., max_length=255)
    platform: PlatformType
    occurrence_count: int = 1
    engagement_sum: int = 0
    trend_score: Optional[float] = None
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None


class TrendDataCreate(TrendDataBase):
    pass


class TrendData(TrendDataBase):
    id: int
    trend_date: datetime
    created_at: datetime
    updated_at: datetime


# API Response schemas
class PaginatedResponse(BaseSchema):
    items: List[Any]
    total: int
    page: int = Field(..., ge=1)
    limit: int = Field(..., ge=1, le=100)
    has_next: bool
    has_prev: bool


class ApiResponse(BaseSchema):
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[str] = None


# Search and filter schemas
class ContentFilter(BaseSchema):
    platforms: Optional[List[PlatformType]] = None
    content_types: Optional[List[ContentType]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_views: Optional[int] = None
    min_likes: Optional[int] = None
    has_media: Optional[bool] = None
    is_analyzed: Optional[bool] = None


class SearchQuery(BaseSchema):
    query: str = Field(..., min_length=1, max_length=255)
    filters: Optional[ContentFilter] = None
    sort_by: str = Field(default="created_at", pattern="^(created_at|download_date|performance_score|engagement_rate)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


# Statistics schemas
class PlatformStats(BaseSchema):
    platform: PlatformType
    total_posts: int
    total_files: int
    avg_engagement: float
    top_content_type: ContentType


class OverallStats(BaseSchema):
    total_posts: int
    total_files: int
    total_downloads: int
    active_platforms: int
    platform_stats: List[PlatformStats]
    recent_activity: List[Post]


# Update forward references
PostWithAnalytics.model_rebuild() 