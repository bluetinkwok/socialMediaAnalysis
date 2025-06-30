"""
Privacy Models

This module defines privacy-related models for GDPR/CCPA compliance.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class ConsentType(str, Enum):
    """Types of user consent"""
    ESSENTIAL = "essential"  # Required for basic functionality
    ANALYTICS = "analytics"  # Analytics and performance tracking
    MARKETING = "marketing"  # Marketing and personalization
    THIRD_PARTY = "third_party"  # Third-party data sharing
    PROFILING = "profiling"  # User profiling and automated decision making


class UserConsent(BaseModel):
    """Model for user consent records"""
    id: Optional[int] = None
    user_id: int
    consent_type: ConsentType
    granted: bool
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    class Config:
        orm_mode = True


class ConsentRequest(BaseModel):
    """Model for consent update requests"""
    consent_type: ConsentType
    granted: bool


class ConsentResponse(BaseModel):
    """Model for consent responses"""
    consent_type: ConsentType
    granted: bool
    timestamp: Optional[datetime] = None


class DataSubjectRequestType(str, Enum):
    """Types of data subject requests"""
    ACCESS = "access"  # Right to access personal data
    DELETE = "delete"  # Right to erasure
    RECTIFY = "rectify"  # Right to rectification
    RESTRICT = "restrict"  # Right to restriction of processing
    PORTABILITY = "portability"  # Right to data portability
    OBJECT = "object"  # Right to object to processing
    AUTOMATED = "automated"  # Right regarding automated decision making


class DataSubjectRequest(BaseModel):
    """Model for data subject requests"""
    id: Optional[int] = None
    user_id: int
    request_type: DataSubjectRequestType
    request_details: Optional[Dict] = None
    status: str = "pending"  # pending, processing, completed, rejected
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True


class DataProcessingActivity(str, Enum):
    """Types of data processing activities"""
    COLLECTION = "collection"  # Collecting user data
    STORAGE = "storage"  # Storing user data
    USE = "use"  # Using user data
    DISCLOSURE = "disclosure"  # Disclosing user data
    ERASURE = "erasure"  # Erasing user data
    RESTRICTION = "restriction"  # Restricting processing of user data
    PORTABILITY = "portability"  # Exporting user data
    AUTOMATED = "automated"  # Automated decision making


class DataProcessingLog(BaseModel):
    """Model for data processing activity logs"""
    id: Optional[int] = None
    activity_type: str
    user_id: Optional[int] = None
    data_categories: List[str] = []
    processing_purpose: Optional[str] = None
    legal_basis: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    class Config:
        orm_mode = True


class DataBreachLog(BaseModel):
    """Model for data breach logs"""
    id: Optional[int] = None
    breach_type: str
    description: str
    affected_users: Optional[List[int]] = None
    affected_data: List[str] = []
    detection_time: datetime
    resolution_time: Optional[datetime] = None
    reported_to_authorities: bool = False
    reported_time: Optional[datetime] = None
    measures_taken: Optional[str] = None
    
    class Config:
        orm_mode = True


class PrivacySettings(BaseModel):
    """Model for user privacy settings"""
    user_id: int
    marketing_emails: bool = False
    data_sharing: bool = False
    personalized_content: bool = False
    analytics_tracking: bool = False
    third_party_cookies: bool = False
    location_tracking: bool = False
    
    class Config:
        orm_mode = True


class DataRetentionPolicy(BaseModel):
    """Model for data retention policies"""
    id: Optional[int] = None
    data_type: str
    retention_period_days: int
    legal_basis: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        orm_mode = True 