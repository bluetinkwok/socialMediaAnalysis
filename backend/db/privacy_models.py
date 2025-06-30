"""
Privacy Database Models

This module defines SQLAlchemy models for privacy-related database tables.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, Boolean, ForeignKey, Enum, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from db.models import Base
from core.encryption import encryption_service
from db.encrypted_fields import encrypted_string_column, encrypted_json_column


class ConsentType(enum.Enum):
    """Types of user consent"""
    ESSENTIAL = "essential"
    ANALYTICS = "analytics"
    MARKETING = "marketing"
    THIRD_PARTY = "third_party"
    PROFILING = "profiling"


class DataSubjectRequestType(enum.Enum):
    """Types of data subject requests"""
    ACCESS = "access"
    DELETE = "delete"
    RECTIFY = "rectify"
    RESTRICT = "restrict"
    PORTABILITY = "portability"
    OBJECT = "object"
    AUTOMATED = "automated"


class DataSubjectRequestStatus(enum.Enum):
    """Status of data subject requests"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"


class UserConsent(Base):
    """User consent records"""
    __tablename__ = "user_consents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = Column(Enum(ConsentType), nullable=False, index=True)
    granted = Column(Boolean, nullable=False)
    ip_address = encrypted_string_column(nullable=True)
    user_agent = encrypted_string_column(nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="consents")
    
    def __repr__(self):
        return f"<UserConsent(id={self.id}, user_id={self.user_id}, type={self.consent_type}, granted={self.granted})>"


class DataSubjectRequest(Base):
    """Data subject request records"""
    __tablename__ = "data_subject_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    request_type = Column(Enum(DataSubjectRequestType), nullable=False, index=True)
    request_details = encrypted_json_column(nullable=True)
    status = Column(Enum(DataSubjectRequestStatus), default=DataSubjectRequestStatus.PENDING, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = encrypted_string_column(nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="data_requests")
    
    def __repr__(self):
        return f"<DataSubjectRequest(id={self.id}, user_id={self.user_id}, type={self.request_type}, status={self.status})>"


class DataProcessingLog(Base):
    """Data processing activity logs"""
    __tablename__ = "data_processing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    activity_type = Column(String(50), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    data_categories = Column(JSON, nullable=True)
    processing_purpose = Column(String(255), nullable=True)
    legal_basis = Column(String(255), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<DataProcessingLog(id={self.id}, type={self.activity_type}, user_id={self.user_id})>"


class DataBreachLog(Base):
    """Data breach logs"""
    __tablename__ = "data_breach_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    breach_type = Column(String(50), nullable=False)
    description = encrypted_string_column(nullable=False)
    affected_users = Column(JSON, nullable=True)  # List of user IDs
    affected_data = Column(JSON, nullable=False)  # List of data categories
    detection_time = Column(DateTime(timezone=True), nullable=False)
    resolution_time = Column(DateTime(timezone=True), nullable=True)
    reported_to_authorities = Column(Boolean, default=False, nullable=False)
    reported_time = Column(DateTime(timezone=True), nullable=True)
    measures_taken = encrypted_string_column(nullable=True)
    
    def __repr__(self):
        return f"<DataBreachLog(id={self.id}, type={self.breach_type}, detection={self.detection_time})>"


class PrivacySettings(Base):
    """User privacy settings"""
    __tablename__ = "privacy_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    marketing_emails = Column(Boolean, default=False, nullable=False)
    data_sharing = Column(Boolean, default=False, nullable=False)
    personalized_content = Column(Boolean, default=False, nullable=False)
    analytics_tracking = Column(Boolean, default=False, nullable=False)
    third_party_cookies = Column(Boolean, default=False, nullable=False)
    location_tracking = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="privacy_settings")
    
    def __repr__(self):
        return f"<PrivacySettings(user_id={self.user_id})>"


class DataRetentionPolicy(Base):
    """Data retention policies"""
    __tablename__ = "data_retention_policies"
    
    id = Column(Integer, primary_key=True, index=True)
    data_type = Column(String(50), nullable=False, unique=True, index=True)
    retention_period_days = Column(Integer, nullable=False)
    legal_basis = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<DataRetentionPolicy(data_type={self.data_type}, period={self.retention_period_days} days)>" 