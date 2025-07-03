"""
SQLAlchemy Base and Model Imports

This module centralizes the SQLAlchemy Base declaration and imports all models
to resolve circular import issues.
"""

from sqlalchemy.ext.declarative import declarative_base

# Create the declarative base
Base = declarative_base()

# Import all models here to ensure they're registered with Base
# These imports are intentionally placed at the bottom to avoid circular imports

# First import the models without relationships to privacy models
from backend.db.models import (
    PlatformType, ContentType, DownloadStatus, MonitoringFrequency, 
    MonitoringStatus, Role, Platform, Post, MediaFile, DownloadJob,
    AnalyticsData, TrendData, UserSession, MonitoringJob, MonitoringRun
)

# Then import the privacy models
from backend.db.privacy_models import (
    ConsentType, DataSubjectRequestType, DataSubjectRequestStatus,
    UserConsent, DataSubjectRequest, DataProcessingLog, DataBreachLog,
    PrivacySettings, DataRetentionPolicy
)

# Finally import User which has relationships to privacy models
from backend.db.models import User 