"""
SQLAlchemy models for Social Media Analysis Platform
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, Boolean, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from backend.db.base_models import Base


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
    IN_PROGRESS = "in_progress"
    PROCESSING = "processing"  # Keep for backward compatibility
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MonitoringFrequency(enum.Enum):
    """Monitoring frequency options"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"  # For custom interval in minutes


class MonitoringStatus(enum.Enum):
    """Monitoring job status"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class Role(enum.Enum):
    """User roles for access control"""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class User(Base):
    """User table for authentication and authorization"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    role = Column(Enum(Role), default=Role.USER, nullable=False)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Privacy and GDPR fields
    anonymized = Column(Boolean, default=False)
    anonymized_at = Column(DateTime(timezone=True))
    data_export_requested_at = Column(DateTime(timezone=True))
    data_export_completed_at = Column(DateTime(timezone=True))
    deletion_requested_at = Column(DateTime(timezone=True))
    processing_restricted = Column(Boolean, default=False)
    processing_restricted_at = Column(DateTime(timezone=True))
    
    # Relationships for privacy
    consents = relationship("UserConsent", back_populates="user", cascade="all, delete-orphan")
    data_requests = relationship("DataSubjectRequest", back_populates="user")
    privacy_settings = relationship("PrivacySettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role={self.role})>"


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
    job_id = Column(String(255), unique=True, nullable=False, index=True)  # UUID for external references
    
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
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, unique=True)  # One analytics record per post
    
    # Core Performance metrics
    engagement_rate = Column(Float, index=True)
    performance_score = Column(Float, index=True)
    
    # Advanced metrics from MetricsCalculator
    virality_score = Column(Float)
    trend_score = Column(Float)
    engagement_velocity = Column(Float)
    content_quality_score = Column(Float)
    audience_reach_score = Column(Float)
    interaction_depth_score = Column(Float)
    
    # Scoring breakdown components
    weighted_components = Column(JSON)  # Breakdown of weighted score components
    applied_bonuses = Column(JSON)  # Applied bonuses and their values
    applied_penalties = Column(JSON)  # Applied penalties and their values
    platform_adjustment = Column(Float)  # Platform-specific adjustment factor
    confidence_score = Column(Float)  # Confidence in the calculated score (0-100)
    
    # Comparative metrics
    platform_rank = Column(Integer)  # Rank within platform
    category_rank = Column(Integer)  # Rank within content type
    overall_rank = Column(Integer)  # Overall rank across all content
    
    # Time-based metrics
    peak_engagement_hour = Column(Integer)  # Hour when engagement peaked
    days_since_publish = Column(Integer)  # Days since original publish date
    
    # Pattern recognition and features
    success_patterns = Column(JSON)  # Identified success patterns with details
    content_features = Column(JSON)  # Extracted content features for analysis
    
    # Processing metadata
    algorithm_version = Column(String(50), default="1.0")  # Version of analytics algorithm used
    processing_duration = Column(Float)  # Time taken to process analytics (seconds)
    data_quality_flags = Column(JSON)  # Flags indicating data quality issues
    
    # Timestamps
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    post = relationship("Post", back_populates="analytics")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_analytics_performance_score', 'performance_score'),
        Index('idx_analytics_platform_rank', 'platform_rank'),
        Index('idx_analytics_engagement_rate', 'engagement_rate'),
        Index('idx_analytics_analyzed_at', 'analyzed_at'),
        Index('idx_analytics_post_performance', 'post_id', 'performance_score'),
    )
    
    def __repr__(self):
        return f"<AnalyticsData(id={self.id}, post_id={self.post_id}, score={self.performance_score})>"
    
    def to_dict(self) -> dict:
        """Convert analytics data to dictionary for API responses"""
        return {
            'id': self.id,
            'post_id': self.post_id,
            'engagement_rate': self.engagement_rate,
            'performance_score': self.performance_score,
            'virality_score': self.virality_score,
            'trend_score': self.trend_score,
            'engagement_velocity': self.engagement_velocity,
            'content_quality_score': self.content_quality_score,
            'audience_reach_score': self.audience_reach_score,
            'interaction_depth_score': self.interaction_depth_score,
            'platform_adjustment': self.platform_adjustment,
            'confidence_score': self.confidence_score,
            'platform_rank': self.platform_rank,
            'category_rank': self.category_rank,
            'overall_rank': self.overall_rank,
            'success_patterns': self.success_patterns,
            'content_features': self.content_features,
            'algorithm_version': self.algorithm_version,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


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


class MonitoringJob(Base):
    """Configuration for automated monitoring of channels/accounts"""
    __tablename__ = "monitoring_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(255), unique=True, nullable=False, index=True)  # UUID for external references
    
    # Monitoring target information
    name = Column(String(255), nullable=False)  # User-friendly name for the monitoring job
    platform = Column(Enum(PlatformType), nullable=False, index=True)
    target_url = Column(String(2048), nullable=False)  # Channel/account URL to monitor
    target_id = Column(String(255))  # Platform-specific ID for the target
    target_type = Column(String(50), nullable=False)  # channel, account, hashtag, etc.
    
    # Scheduling configuration
    frequency = Column(Enum(MonitoringFrequency), default=MonitoringFrequency.DAILY, nullable=False)
    interval_minutes = Column(Integer)  # For custom frequency, interval in minutes
    max_items_per_run = Column(Integer, default=10)  # Maximum number of items to download per run
    
    # Status and tracking
    status = Column(Enum(MonitoringStatus), default=MonitoringStatus.ACTIVE, index=True)
    last_run_at = Column(DateTime(timezone=True))
    next_run_at = Column(DateTime(timezone=True))
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)
    
    # Notification settings
    notify_on_new_content = Column(Boolean, default=True)
    notify_on_failure = Column(Boolean, default=True)
    notification_email = Column(String(255))
    
    # Advanced options
    download_options = Column(JSON)  # Additional download configuration options
    filter_criteria = Column(JSON)  # Criteria for filtering content to download
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True))  # Optional expiration date
    
    # User who created the monitoring job
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_monitoring_status_next_run', 'status', 'next_run_at'),
        Index('idx_monitoring_platform', 'platform'),
        Index('idx_monitoring_user', 'user_id'),
    )
    
    def __repr__(self):
        return f"<MonitoringJob(id={self.id}, name='{self.name}', platform={self.platform}, status={self.status})>"
    
    def to_dict(self) -> dict:
        """Convert monitoring job to dictionary for API responses"""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'name': self.name,
            'platform': self.platform.value,
            'target_url': self.target_url,
            'target_id': self.target_id,
            'target_type': self.target_type,
            'frequency': self.frequency.value,
            'interval_minutes': self.interval_minutes,
            'max_items_per_run': self.max_items_per_run,
            'status': self.status.value,
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None,
            'next_run_at': self.next_run_at.isoformat() if self.next_run_at else None,
            'total_runs': self.total_runs,
            'successful_runs': self.successful_runs,
            'failed_runs': self.failed_runs,
            'notify_on_new_content': self.notify_on_new_content,
            'notify_on_failure': self.notify_on_failure,
            'notification_email': self.notification_email,
            'download_options': self.download_options,
            'filter_criteria': self.filter_criteria,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'user_id': self.user_id
        }


class MonitoringRun(Base):
    """Record of individual monitoring job runs"""
    __tablename__ = "monitoring_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationship to monitoring job
    monitoring_job_id = Column(Integer, ForeignKey("monitoring_jobs.id"), nullable=False, index=True)
    monitoring_job = relationship("MonitoringJob")
    
    # Run information
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    status = Column(Enum(DownloadStatus), default=DownloadStatus.IN_PROGRESS)
    
    # Results
    items_found = Column(Integer, default=0)
    items_processed = Column(Integer, default=0)
    new_items_downloaded = Column(Integer, default=0)
    
    # Related download job (if any)
    download_job_id = Column(Integer, ForeignKey("download_jobs.id"), nullable=True)
    download_job = relationship("DownloadJob")
    
    # Error information
    error_message = Column(Text)
    error_details = Column(JSON)
    
    def __repr__(self):
        return f"<MonitoringRun(id={self.id}, job_id={self.monitoring_job_id}, status={self.status})>"

# Import privacy models at the end to resolve circular import
# This needs to be after all the model definitions
from backend.db.privacy_models import UserConsent, DataSubjectRequest, PrivacySettings 