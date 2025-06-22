"""
SQLAlchemy models for Social Media Analysis Platform
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, Boolean, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()


class PlatformType(enum.Enum):
    """Supported social media platforms"""
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    THREADS = "threads"
    REDNOTE = "rednote"


class ContentType(enum.Enum):
    """Types of content"""
    VIDEO = "video"
    IMAGE = "image"
    TEXT = "text"
    MIXED = "mixed"


class DownloadStatus(enum.Enum):
    """Download job status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Platform(Base):
    """Platform configuration table"""
    __tablename__ = "platforms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    base_url = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    posts = relationship("Post", back_populates="platform_ref")


class Post(Base):
    """Main posts table for storing content metadata"""
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic content information
    platform = Column(Enum(PlatformType), nullable=False, index=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=True)
    content_type = Column(Enum(ContentType), nullable=False, index=True)
    url = Column(String(2048), nullable=False, unique=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    content_text = Column(Text)
    
    # Author information
    author = Column(String(255), nullable=False)
    author_id = Column(String(255))
    author_avatar = Column(String(2048))
    
    # Media information
    thumbnail = Column(String(2048))
    duration = Column(Integer)  # Duration in seconds for videos
    
    # Content metadata
    hashtags = Column(JSON)  # List of hashtags
    mentions = Column(JSON)  # List of mentions
    
    # Engagement metrics (stored as JSON for flexibility)
    engagement_metrics = Column(JSON)  # {views, likes, comments, shares, saves, etc.}
    
    # Timestamps
    publish_date = Column(DateTime(timezone=True))
    download_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Analysis flags
    is_analyzed = Column(Boolean, default=False)
    performance_score = Column(Float)
    
    # Relationships
    platform_ref = relationship("Platform", back_populates="posts")
    files = relationship("MediaFile", back_populates="post", cascade="all, delete-orphan")
    analytics = relationship("AnalyticsData", back_populates="post", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Post(id={self.id}, platform={self.platform}, title='{self.title[:50]}...')>"


class MediaFile(Base):
    """Files associated with posts"""
    __tablename__ = "media_files"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    
    # File information
    filename = Column(String(255), nullable=False)
    file_path = Column(String(2048), nullable=False)
    file_type = Column(String(50), nullable=False)  # video, image, text, etc.
    file_size = Column(Integer)  # Size in bytes
    mime_type = Column(String(100))
    
    # File metadata
    width = Column(Integer)  # For images/videos
    height = Column(Integer)  # For images/videos
    duration = Column(Float)  # For videos/audio
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    post = relationship("Post", back_populates="files")
    
    def __repr__(self):
        return f"<MediaFile(id={self.id}, filename='{self.filename}', type={self.file_type})>"


class DownloadJob(Base):
    """Download job tracking"""
    __tablename__ = "download_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Job information
    status = Column(Enum(DownloadStatus), default=DownloadStatus.PENDING, index=True)
    platform = Column(Enum(PlatformType), nullable=False)
    urls = Column(JSON)  # List of URLs to download
    
    # Progress tracking
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    progress_percentage = Column(Float, default=0.0)
    
    # Error handling
    errors = Column(JSON)  # List of error messages
    error_count = Column(Integer, default=0)
    
    # Options
    download_options = Column(JSON)  # Download configuration options
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<DownloadJob(id={self.id}, status={self.status}, platform={self.platform})>"


class AnalyticsData(Base):
    """Analytics data for posts"""
    __tablename__ = "analytics_data"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    
    # Performance metrics
    engagement_rate = Column(Float)
    virality_score = Column(Float)
    performance_score = Column(Float)
    trend_score = Column(Float)
    
    # Comparative metrics
    platform_rank = Column(Integer)  # Rank within platform
    category_rank = Column(Integer)  # Rank within content type
    
    # Time-based metrics
    peak_engagement_hour = Column(Integer)  # Hour when engagement peaked
    engagement_velocity = Column(Float)  # Rate of engagement growth
    
    # Pattern recognition
    success_patterns = Column(JSON)  # Identified success patterns
    content_features = Column(JSON)  # Extracted content features
    
    # Timestamps
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    post = relationship("Post", back_populates="analytics")
    
    def __repr__(self):
        return f"<AnalyticsData(id={self.id}, post_id={self.post_id}, score={self.performance_score})>"


class TrendData(Base):
    """Trending content and hashtags"""
    __tablename__ = "trend_data"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Trend information
    trend_type = Column(String(50), nullable=False)  # hashtag, content, pattern
    trend_value = Column(String(255), nullable=False)  # The trending item
    platform = Column(Enum(PlatformType), nullable=False)
    
    # Metrics
    occurrence_count = Column(Integer, default=1)
    engagement_sum = Column(Integer, default=0)
    trend_score = Column(Float)
    
    # Time window
    trend_date = Column(DateTime(timezone=True), server_default=func.now())
    window_start = Column(DateTime(timezone=True))
    window_end = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<TrendData(id={self.id}, type={self.trend_type}, value='{self.trend_value}')>"


class UserSession(Base):
    """User sessions for tracking API usage"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Session information
    session_id = Column(String(255), unique=True, nullable=False)
    user_agent = Column(Text)
    ip_address = Column(String(45))  # IPv6 compatible
    
    # Activity tracking
    requests_count = Column(Integer, default=0)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, session_id='{self.session_id[:8]}...')>" 