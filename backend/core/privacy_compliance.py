"""
Privacy Compliance Module

This module provides utilities for GDPR/CCPA compliance and privacy management.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from db.privacy_models import (
    UserConsent, ConsentType, DataSubjectRequest, DataSubjectRequestType,
    DataSubjectRequestStatus, DataProcessingLog, DataBreachLog, PrivacySettings
)
from db.database import SessionLocal
from core.encryption import encryption_service

logger = logging.getLogger(__name__)


def record_consent(
    user_id: int,
    consent_type: ConsentType,
    granted: bool,
    db: Optional[Session] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> UserConsent:
    """
    Record a user's consent decision.
    
    Args:
        user_id: User ID
        consent_type: Type of consent
        granted: Whether consent was granted
        db: Database session (creates a new one if not provided)
        ip_address: User's IP address
        user_agent: User's browser/device information
        
    Returns:
        Created UserConsent object
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        # Create consent record
        consent = UserConsent(
            user_id=user_id,
            consent_type=consent_type,
            granted=granted,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now()
        )
        
        db.add(consent)
        db.commit()
        db.refresh(consent)
        
        logger.info(f"Recorded consent for user {user_id}: {consent_type} = {granted}")
        return consent
    except Exception as e:
        logger.error(f"Failed to record consent: {str(e)}")
        db.rollback()
        raise
    finally:
        if close_session:
            db.close()


def check_consent(
    user_id: int,
    consent_type: ConsentType,
    db: Optional[Session] = None
) -> bool:
    """
    Check if a user has granted a specific type of consent.
    
    Args:
        user_id: User ID
        consent_type: Type of consent to check
        db: Database session (creates a new one if not provided)
        
    Returns:
        True if consent has been granted, False otherwise
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        # Get the most recent consent record for this user and type
        consent = db.query(UserConsent).filter_by(
            user_id=user_id,
            consent_type=consent_type
        ).order_by(UserConsent.timestamp.desc()).first()
        
        # Return the consent status, or False if no record exists
        return consent.granted if consent else False
    except Exception as e:
        logger.error(f"Failed to check consent: {str(e)}")
        return False
    finally:
        if close_session:
            db.close()


def record_data_subject_request(
    user_id: int,
    request_type: DataSubjectRequestType,
    request_details: Optional[str] = None,
    db: Optional[Session] = None
) -> DataSubjectRequest:
    """
    Record a data subject request (e.g., right to access, right to be forgotten).
    
    Args:
        user_id: User ID
        request_type: Type of request
        request_details: Additional details about the request
        db: Database session (creates a new one if not provided)
        
    Returns:
        Created DataSubjectRequest object
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        # Create request record
        request = DataSubjectRequest(
            user_id=user_id,
            request_type=request_type,
            request_details=request_details,
            status=DataSubjectRequestStatus.PENDING,
            created_at=datetime.now()
        )
        
        db.add(request)
        db.commit()
        db.refresh(request)
        
        logger.info(f"Recorded data subject request for user {user_id}: {request_type}")
        return request
    except Exception as e:
        logger.error(f"Failed to record data subject request: {str(e)}")
        db.rollback()
        raise
    finally:
        if close_session:
            db.close()


def process_data_subject_request(
    request_id: int,
    new_status: DataSubjectRequestStatus,
    notes: Optional[str] = None,
    db: Optional[Session] = None
) -> Optional[DataSubjectRequest]:
    """
    Update the status of a data subject request and process it.
    
    Args:
        request_id: ID of the request to process
        new_status: New status to set
        notes: Processing notes
        db: Database session (creates a new one if not provided)
        
    Returns:
        Updated DataSubjectRequest object or None if not found
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        # Get the request
        request = db.query(DataSubjectRequest).filter_by(id=request_id).first()
        if not request:
            logger.warning(f"Data subject request not found: {request_id}")
            return None
        
        # Update status
        request.status = new_status
        request.notes = notes
        
        if new_status == DataSubjectRequestStatus.COMPLETED:
            request.completed_at = datetime.now()
            
            # Process the request based on its type
            if request.request_type == DataSubjectRequestType.DELETE:
                anonymize_user_data(request.user_id, db)
            elif request.request_type == DataSubjectRequestType.ACCESS:
                export_user_data(request.user_id, db)
            elif request.request_type == DataSubjectRequestType.RESTRICT:
                restrict_user_data_processing(request.user_id, db)
        
        db.commit()
        db.refresh(request)
        
        logger.info(f"Updated data subject request {request_id} status to {new_status}")
        return request
    except Exception as e:
        logger.error(f"Failed to process data subject request: {str(e)}")
        db.rollback()
        raise
    finally:
        if close_session:
            db.close()


def anonymize_user_data(
    user_id: int,
    db: Optional[Session] = None
) -> bool:
    """
    Anonymize a user's personal data.
    
    Args:
        user_id: User ID
        db: Database session (creates a new one if not provided)
        
    Returns:
        True if successful
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        # Update user record to anonymize personal data
        result = db.execute(
            text("""
                UPDATE users 
                SET 
                    username = 'anonymized_' || id,
                    email = 'anonymized_' || id || '@example.com',
                    anonymized = 1,
                    anonymized_at = CURRENT_TIMESTAMP
                WHERE id = :user_id
            """),
            {"user_id": user_id}
        )
        
        # Delete or anonymize related personal data
        # This would depend on the specific data model
        
        db.commit()
        logger.info(f"Anonymized data for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to anonymize user data: {str(e)}")
        db.rollback()
        return False
    finally:
        if close_session:
            db.close()


def export_user_data(
    user_id: int,
    db: Optional[Session] = None,
    output_dir: str = "exports"
) -> Optional[str]:
    """
    Export all data for a user in a machine-readable format.
    
    Args:
        user_id: User ID
        db: Database session (creates a new one if not provided)
        output_dir: Directory to save the export
        
    Returns:
        Path to the exported file or None if failed
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        # Create export directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate export filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_file = Path(output_dir) / f"user_{user_id}_export_{timestamp}.json"
        
        # Collect user data
        user_data = {}
        
        # Basic user info
        user_result = db.execute(
            text("SELECT * FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        ).fetchone()
        
        if user_result:
            user_data["user"] = dict(user_result)
            
            # Remove sensitive fields
            if "hashed_password" in user_data["user"]:
                user_data["user"]["hashed_password"] = "REDACTED"
        
        # Consent records
        consents = db.query(UserConsent).filter_by(user_id=user_id).all()
        user_data["consents"] = [
            {
                "consent_type": str(c.consent_type),
                "granted": c.granted,
                "timestamp": c.timestamp.isoformat() if c.timestamp else None
            }
            for c in consents
        ]
        
        # Data subject requests
        requests = db.query(DataSubjectRequest).filter_by(user_id=user_id).all()
        user_data["data_requests"] = [
            {
                "request_type": str(r.request_type),
                "status": str(r.status),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None
            }
            for r in requests
        ]
        
        # Privacy settings
        settings = db.query(PrivacySettings).filter_by(user_id=user_id).first()
        if settings:
            user_data["privacy_settings"] = {
                "marketing_emails": settings.marketing_emails,
                "data_sharing": settings.data_sharing,
                "personalized_content": settings.personalized_content,
                "analytics_tracking": settings.analytics_tracking,
                "third_party_cookies": settings.third_party_cookies,
                "location_tracking": settings.location_tracking
            }
        
        # Add other user-related data as needed
        
        # Write to file
        with open(export_file, 'w') as f:
            json.dump(user_data, f, indent=2)
        
        # Update user record to track export
        db.execute(
            text("""
                UPDATE users 
                SET 
                    data_export_completed_at = CURRENT_TIMESTAMP
                WHERE id = :user_id
            """),
            {"user_id": user_id}
        )
        
        db.commit()
        logger.info(f"Exported data for user {user_id} to {export_file}")
        return str(export_file)
    except Exception as e:
        logger.error(f"Failed to export user data: {str(e)}")
        db.rollback()
        return None
    finally:
        if close_session:
            db.close()


def restrict_user_data_processing(
    user_id: int,
    db: Optional[Session] = None
) -> bool:
    """
    Restrict processing of a user's data.
    
    Args:
        user_id: User ID
        db: Database session (creates a new one if not provided)
        
    Returns:
        True if successful
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        # Update user record to restrict processing
        result = db.execute(
            text("""
                UPDATE users 
                SET 
                    processing_restricted = 1,
                    processing_restricted_at = CURRENT_TIMESTAMP
                WHERE id = :user_id
            """),
            {"user_id": user_id}
        )
        
        # Update privacy settings to disable all optional processing
        settings = db.query(PrivacySettings).filter_by(user_id=user_id).first()
        if settings:
            settings.marketing_emails = False
            settings.data_sharing = False
            settings.personalized_content = False
            settings.analytics_tracking = False
            settings.third_party_cookies = False
            settings.location_tracking = False
        else:
            # Create new settings with all options disabled
            settings = PrivacySettings(
                user_id=user_id,
                marketing_emails=False,
                data_sharing=False,
                personalized_content=False,
                analytics_tracking=False,
                third_party_cookies=False,
                location_tracking=False
            )
            db.add(settings)
        
        db.commit()
        logger.info(f"Restricted data processing for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to restrict user data processing: {str(e)}")
        db.rollback()
        return False
    finally:
        if close_session:
            db.close()


def log_data_processing_activity(
    activity_type: str,
    user_id: Optional[int] = None,
    data_categories: Optional[List[str]] = None,
    processing_purpose: Optional[str] = None,
    legal_basis: Optional[str] = None,
    db: Optional[Session] = None
) -> Optional[DataProcessingLog]:
    """
    Log a data processing activity for GDPR compliance.
    
    Args:
        activity_type: Type of processing activity
        user_id: User ID (if applicable)
        data_categories: Categories of data being processed
        processing_purpose: Purpose of processing
        legal_basis: Legal basis for processing
        db: Database session (creates a new one if not provided)
        
    Returns:
        Created DataProcessingLog object or None if failed
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        # Create log record
        log = DataProcessingLog(
            activity_type=activity_type,
            user_id=user_id,
            data_categories=data_categories,
            processing_purpose=processing_purpose,
            legal_basis=legal_basis,
            timestamp=datetime.now()
        )
        
        db.add(log)
        db.commit()
        db.refresh(log)
        
        logger.info(f"Logged data processing activity: {activity_type}")
        return log
    except Exception as e:
        logger.error(f"Failed to log data processing activity: {str(e)}")
        db.rollback()
        return None
    finally:
        if close_session:
            db.close()


def log_data_breach(
    breach_type: str,
    description: str,
    affected_users: Optional[List[int]] = None,
    affected_data: List[str] = None,
    reported_to_authorities: bool = False,
    measures_taken: Optional[str] = None,
    db: Optional[Session] = None
) -> Optional[DataBreachLog]:
    """
    Log a data breach incident for GDPR compliance.
    
    Args:
        breach_type: Type of breach
        description: Description of the breach
        affected_users: List of affected user IDs
        affected_data: Categories of affected data
        reported_to_authorities: Whether the breach was reported to authorities
        measures_taken: Measures taken to address the breach
        db: Database session (creates a new one if not provided)
        
    Returns:
        Created DataBreachLog object or None if failed
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        # Create breach log record
        log = DataBreachLog(
            breach_type=breach_type,
            description=description,
            affected_users=affected_users,
            affected_data=affected_data or [],
            detection_time=datetime.now(),
            reported_to_authorities=reported_to_authorities,
            reported_time=datetime.now() if reported_to_authorities else None,
            measures_taken=measures_taken
        )
        
        db.add(log)
        db.commit()
        db.refresh(log)
        
        logger.warning(f"Logged data breach: {breach_type}")
        return log
    except Exception as e:
        logger.error(f"Failed to log data breach: {str(e)}")
        db.rollback()
        return None
    finally:
        if close_session:
            db.close() 