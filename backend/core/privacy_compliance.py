"""
Privacy Compliance Module

This module provides utilities for managing privacy compliance requirements,
including consent management, data subject rights, and privacy settings.
"""

import logging
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from core.config import get_settings
from core.data_retention import DataRetentionService, anonymize_user_data, delete_user_data, export_user_data
from db.database import get_db
from db.privacy_models import (
    UserConsent, ConsentType, DataSubjectRequest, DataSubjectRequestType, 
    DataSubjectRequestStatus, DataProcessingLog, PrivacySettings
)

logger = logging.getLogger(__name__)
settings = get_settings()


class PrivacyComplianceError(Exception):
    """Base exception for privacy compliance errors."""
    pass


class PrivacyComplianceService:
    """
    Service for managing privacy compliance requirements.
    """
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize the privacy compliance service.
        
        Args:
            db: Database session (optional)
        """
        self.db = db
        self.retention_service = DataRetentionService(db)
    
    def record_consent(
        self, 
        user_id: int, 
        consent_type: ConsentType, 
        granted: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserConsent:
        """
        Record a user's consent.
        
        Args:
            user_id: ID of the user
            consent_type: Type of consent
            granted: Whether consent is granted
            ip_address: User's IP address (optional)
            user_agent: User's browser/device info (optional)
            
        Returns:
            Created UserConsent record
            
        Raises:
            PrivacyComplianceError: If consent recording fails
        """
        try:
            # Use provided DB session or get a new one
            db_to_use = self.db or next(get_db())
            try:
                # Create consent record
                consent = UserConsent(
                    user_id=user_id,
                    consent_type=consent_type,
                    granted=granted,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                db_to_use.add(consent)
                
                if not self.db:  # Only commit if we created the session
                    db_to_use.commit()
                    db_to_use.refresh(consent)
                
                logger.info(f"Recorded consent for user {user_id}: {consent_type} = {granted}")
                return consent
                
            finally:
                if not self.db:  # Only close if we created the session
                    db_to_use.close()
                    
        except Exception as e:
            logger.error(f"Failed to record consent: {str(e)}")
            raise PrivacyComplianceError(f"Failed to record consent: {str(e)}")
    
    def check_consent(
        self, 
        user_id: int, 
        consent_type: ConsentType
    ) -> bool:
        """
        Check if a user has granted a specific type of consent.
        
        Args:
            user_id: ID of the user
            consent_type: Type of consent to check
            
        Returns:
            True if consent is granted, False otherwise
            
        Raises:
            PrivacyComplianceError: If consent check fails
        """
        try:
            # Use provided DB session or get a new one
            db_to_use = self.db or next(get_db())
            try:
                # Get the latest consent record
                consent = db_to_use.query(UserConsent)\
                    .filter(
                        UserConsent.user_id == user_id,
                        UserConsent.consent_type == consent_type
                    )\
                    .order_by(UserConsent.timestamp.desc())\
                    .first()
                
                if consent:
                    return consent.granted
                
                # No consent record found
                return False
                
            finally:
                if not self.db:  # Only close if we created the session
                    db_to_use.close()
                    
        except Exception as e:
            logger.error(f"Failed to check consent: {str(e)}")
            raise PrivacyComplianceError(f"Failed to check consent: {str(e)}")
    
    def create_data_subject_request(
        self, 
        user_id: int, 
        request_type: DataSubjectRequestType,
        request_details: Optional[Dict[str, Any]] = None
    ) -> DataSubjectRequest:
        """
        Create a data subject request (e.g., access, deletion).
        
        Args:
            user_id: ID of the user
            request_type: Type of request
            request_details: Additional details about the request
            
        Returns:
            Created DataSubjectRequest record
            
        Raises:
            PrivacyComplianceError: If request creation fails
        """
        try:
            # Use provided DB session or get a new one
            db_to_use = self.db or next(get_db())
            try:
                # Create request record
                request = DataSubjectRequest(
                    user_id=user_id,
                    request_type=request_type,
                    request_details=request_details,
                    status=DataSubjectRequestStatus.PENDING
                )
                
                db_to_use.add(request)
                
                if not self.db:  # Only commit if we created the session
                    db_to_use.commit()
                    db_to_use.refresh(request)
                
                logger.info(f"Created data subject request for user {user_id}: {request_type}")
                return request
                
            finally:
                if not self.db:  # Only close if we created the session
                    db_to_use.close()
                    
        except Exception as e:
            logger.error(f"Failed to create data subject request: {str(e)}")
            raise PrivacyComplianceError(f"Failed to create data subject request: {str(e)}")
    
    def process_data_subject_request(
        self, 
        request_id: int,
        notes: Optional[str] = None
    ) -> DataSubjectRequest:
        """
        Process a data subject request.
        
        Args:
            request_id: ID of the request to process
            notes: Additional notes about the processing
            
        Returns:
            Updated DataSubjectRequest record
            
        Raises:
            PrivacyComplianceError: If request processing fails
        """
        try:
            # Use provided DB session or get a new one
            db_to_use = self.db or next(get_db())
            try:
                # Get the request
                request = db_to_use.query(DataSubjectRequest)\
                    .filter(DataSubjectRequest.id == request_id)\
                    .first()
                
                if not request:
                    raise PrivacyComplianceError(f"Data subject request not found: {request_id}")
                
                # Update status to processing
                request.status = DataSubjectRequestStatus.PROCESSING
                
                if not self.db:  # Only commit if we created the session
                    db_to_use.commit()
                    db_to_use.refresh(request)
                
                # Process the request based on type
                user_id = request.user_id
                if not user_id:
                    raise PrivacyComplianceError(f"Request {request_id} has no associated user")
                
                if request.request_type == DataSubjectRequestType.ACCESS:
                    # Export user data
                    data = export_user_data(user_id, db_to_use)
                    request.notes = notes or f"Data exported on {datetime.now(timezone.utc).isoformat()}"
                    
                elif request.request_type == DataSubjectRequestType.DELETE:
                    # Delete user data
                    delete_user_data(user_id, db_to_use)
                    request.notes = notes or f"Data deleted on {datetime.now(timezone.utc).isoformat()}"
                    
                elif request.request_type == DataSubjectRequestType.PORTABILITY:
                    # Similar to access but in a portable format
                    data = export_user_data(user_id, db_to_use)
                    request.notes = notes or f"Data exported in portable format on {datetime.now(timezone.utc).isoformat()}"
                    
                elif request.request_type == DataSubjectRequestType.RESTRICT:
                    # Restrict processing
                    from models.user import User
                    user = db_to_use.query(User).filter(User.id == user_id).first()
                    if user:
                        user.processing_restricted = True
                        user.processing_restricted_at = datetime.now(timezone.utc)
                    request.notes = notes or f"Processing restricted on {datetime.now(timezone.utc).isoformat()}"
                    
                else:
                    # Other request types
                    request.notes = notes or f"Processed on {datetime.now(timezone.utc).isoformat()}"
                
                # Update status to completed
                request.status = DataSubjectRequestStatus.COMPLETED
                request.completed_at = datetime.now(timezone.utc)
                
                if not self.db:  # Only commit if we created the session
                    db_to_use.commit()
                    db_to_use.refresh(request)
                
                logger.info(f"Processed data subject request {request_id} for user {user_id}")
                return request
                
            finally:
                if not self.db:  # Only close if we created the session
                    db_to_use.close()
                    
        except Exception as e:
            logger.error(f"Failed to process data subject request: {str(e)}")
            raise PrivacyComplianceError(f"Failed to process data subject request: {str(e)}")
    
    def log_data_processing(
        self,
        activity_type: str,
        user_id: Optional[int] = None,
        data_categories: Optional[List[str]] = None,
        processing_purpose: Optional[str] = None,
        legal_basis: Optional[str] = None
    ) -> DataProcessingLog:
        """
        Log a data processing activity.
        
        Args:
            activity_type: Type of processing activity
            user_id: ID of the user (optional)
            data_categories: Categories of data being processed
            processing_purpose: Purpose of processing
            legal_basis: Legal basis for processing
            
        Returns:
            Created DataProcessingLog record
            
        Raises:
            PrivacyComplianceError: If logging fails
        """
        try:
            # Use provided DB session or get a new one
            db_to_use = self.db or next(get_db())
            try:
                # Create log record
                log = DataProcessingLog(
                    activity_type=activity_type,
                    user_id=user_id,
                    data_categories=data_categories,
                    processing_purpose=processing_purpose,
                    legal_basis=legal_basis
                )
                
                db_to_use.add(log)
                
                if not self.db:  # Only commit if we created the session
                    db_to_use.commit()
                    db_to_use.refresh(log)
                
                logger.info(f"Logged data processing activity: {activity_type}")
                return log
                
            finally:
                if not self.db:  # Only close if we created the session
                    db_to_use.close()
                    
        except Exception as e:
            logger.error(f"Failed to log data processing: {str(e)}")
            raise PrivacyComplianceError(f"Failed to log data processing: {str(e)}")
    
    def get_or_create_privacy_settings(self, user_id: int) -> PrivacySettings:
        """
        Get or create privacy settings for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            PrivacySettings record
            
        Raises:
            PrivacyComplianceError: If settings retrieval fails
        """
        try:
            # Use provided DB session or get a new one
            db_to_use = self.db or next(get_db())
            try:
                # Try to get existing settings
                settings = db_to_use.query(PrivacySettings)\
                    .filter(PrivacySettings.user_id == user_id)\
                    .first()
                
                if settings:
                    return settings
                
                # Create new settings
                settings = PrivacySettings(
                    user_id=user_id,
                    marketing_emails=False,
                    data_sharing=False,
                    personalized_content=False,
                    analytics_tracking=False,
                    third_party_cookies=False,
                    location_tracking=False
                )
                
                db_to_use.add(settings)
                
                if not self.db:  # Only commit if we created the session
                    db_to_use.commit()
                    db_to_use.refresh(settings)
                
                logger.info(f"Created privacy settings for user {user_id}")
                return settings
                
            finally:
                if not self.db:  # Only close if we created the session
                    db_to_use.close()
                    
        except Exception as e:
            logger.error(f"Failed to get/create privacy settings: {str(e)}")
            raise PrivacyComplianceError(f"Failed to get/create privacy settings: {str(e)}")


# Convenience functions
def record_consent(
    user_id: int, 
    consent_type: ConsentType, 
    granted: bool,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    db: Optional[Session] = None
) -> UserConsent:
    """
    Record a user's consent.
    
    Args:
        user_id: ID of the user
        consent_type: Type of consent
        granted: Whether consent is granted
        ip_address: User's IP address (optional)
        user_agent: User's browser/device info (optional)
        db: Database session (optional)
        
    Returns:
        Created UserConsent record
    """
    service = PrivacyComplianceService(db)
    return service.record_consent(user_id, consent_type, granted, ip_address, user_agent)


def check_consent(
    user_id: int, 
    consent_type: ConsentType,
    db: Optional[Session] = None
) -> bool:
    """
    Check if a user has granted a specific type of consent.
    
    Args:
        user_id: ID of the user
        consent_type: Type of consent to check
        db: Database session (optional)
        
    Returns:
        True if consent is granted, False otherwise
    """
    service = PrivacyComplianceService(db)
    return service.check_consent(user_id, consent_type)


def create_data_subject_request(
    user_id: int, 
    request_type: DataSubjectRequestType,
    request_details: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None
) -> DataSubjectRequest:
    """
    Create a data subject request (e.g., access, deletion).
    
    Args:
        user_id: ID of the user
        request_type: Type of request
        request_details: Additional details about the request
        db: Database session (optional)
        
    Returns:
        Created DataSubjectRequest record
    """
    service = PrivacyComplianceService(db)
    return service.create_data_subject_request(user_id, request_type, request_details)


def process_data_subject_request(
    request_id: int,
    notes: Optional[str] = None,
    db: Optional[Session] = None
) -> DataSubjectRequest:
    """
    Process a data subject request.
    
    Args:
        request_id: ID of the request to process
        notes: Additional notes about the processing
        db: Database session (optional)
        
    Returns:
        Updated DataSubjectRequest record
    """
    service = PrivacyComplianceService(db)
    return service.process_data_subject_request(request_id, notes)


def log_data_processing(
    activity_type: str,
    user_id: Optional[int] = None,
    data_categories: Optional[List[str]] = None,
    processing_purpose: Optional[str] = None,
    legal_basis: Optional[str] = None,
    db: Optional[Session] = None
) -> DataProcessingLog:
    """
    Log a data processing activity.
    
    Args:
        activity_type: Type of processing activity
        user_id: ID of the user (optional)
        data_categories: Categories of data being processed
        processing_purpose: Purpose of processing
        legal_basis: Legal basis for processing
        db: Database session (optional)
        
    Returns:
        Created DataProcessingLog record
    """
    service = PrivacyComplianceService(db)
    return service.log_data_processing(
        activity_type, user_id, data_categories, processing_purpose, legal_basis
    ) 