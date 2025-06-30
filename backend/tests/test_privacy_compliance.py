"""
Tests for the privacy compliance system.
"""

import os
import pytest
from datetime import datetime, timedelta, timezone
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from core.privacy_compliance import (
    PrivacyComplianceService, record_consent, check_consent,
    create_data_subject_request, process_data_subject_request,
    log_data_processing
)
from core.data_retention import (
    DataRetentionService, apply_retention_policy,
    delete_expired_files, anonymize_user_data, delete_user_data
)
from db.privacy_models import (
    UserConsent, ConsentType, DataSubjectRequest, DataSubjectRequestType,
    DataSubjectRequestStatus, DataProcessingLog, PrivacySettings,
    DataRetentionPolicy
)
from db.models import Base, User


@pytest.fixture
def db():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    # Create a test user
    user = User(
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password",
        is_active=True
    )
    session.add(user)
    session.commit()
    
    yield session
    
    session.close()


@pytest.fixture
def privacy_service(db):
    """Create a privacy compliance service."""
    return PrivacyComplianceService(db)


@pytest.fixture
def retention_service(db):
    """Create a data retention service."""
    return DataRetentionService(db)


class TestPrivacyCompliance:
    """Tests for privacy compliance features."""
    
    def test_record_consent(self, privacy_service, db):
        """Test recording user consent."""
        user_id = 1
        consent_type = ConsentType.MARKETING
        granted = True
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0"
        
        consent = privacy_service.record_consent(
            user_id, consent_type, granted, ip_address, user_agent
        )
        
        assert consent.id is not None
        assert consent.user_id == user_id
        assert consent.consent_type == consent_type
        assert consent.granted == granted
        
        # Check it was saved to the database
        db_consent = db.query(UserConsent).filter_by(id=consent.id).first()
        assert db_consent is not None
        assert db_consent.user_id == user_id
        assert db_consent.consent_type == consent_type
        assert db_consent.granted == granted
    
    def test_check_consent(self, privacy_service, db):
        """Test checking user consent."""
        user_id = 1
        consent_type = ConsentType.MARKETING
        
        # No consent record yet
        assert privacy_service.check_consent(user_id, consent_type) is False
        
        # Add consent record (granted)
        privacy_service.record_consent(user_id, consent_type, True)
        assert privacy_service.check_consent(user_id, consent_type) is True
        
        # Add consent record (revoked)
        privacy_service.record_consent(user_id, consent_type, False)
        assert privacy_service.check_consent(user_id, consent_type) is False
    
    def test_create_data_subject_request(self, privacy_service, db):
        """Test creating a data subject request."""
        user_id = 1
        request_type = DataSubjectRequestType.ACCESS
        request_details = {"reason": "Testing"}
        
        request = privacy_service.create_data_subject_request(
            user_id, request_type, request_details
        )
        
        assert request.id is not None
        assert request.user_id == user_id
        assert request.request_type == request_type
        assert request.request_details == request_details
        assert request.status == DataSubjectRequestStatus.PENDING
        
        # Check it was saved to the database
        db_request = db.query(DataSubjectRequest).filter_by(id=request.id).first()
        assert db_request is not None
        assert db_request.user_id == user_id
        assert db_request.request_type == request_type
        assert db_request.status == DataSubjectRequestStatus.PENDING
    
    def test_log_data_processing(self, privacy_service, db):
        """Test logging data processing activities."""
        activity_type = "test_processing"
        user_id = 1
        data_categories = ["personal", "preferences"]
        purpose = "Testing"
        legal_basis = "Legitimate Interest"
        
        log = privacy_service.log_data_processing(
            activity_type, user_id, data_categories, purpose, legal_basis
        )
        
        assert log.id is not None
        assert log.activity_type == activity_type
        assert log.user_id == user_id
        assert log.data_categories == data_categories
        assert log.processing_purpose == purpose
        assert log.legal_basis == legal_basis
        
        # Check it was saved to the database
        db_log = db.query(DataProcessingLog).filter_by(id=log.id).first()
        assert db_log is not None
        assert db_log.activity_type == activity_type
        assert db_log.user_id == user_id
    
    def test_get_or_create_privacy_settings(self, privacy_service, db):
        """Test getting or creating privacy settings."""
        user_id = 1
        
        # No settings yet
        settings = privacy_service.get_or_create_privacy_settings(user_id)
        
        assert settings.id is not None
        assert settings.user_id == user_id
        assert settings.marketing_emails is False
        assert settings.data_sharing is False
        
        # Check it was saved to the database
        db_settings = db.query(PrivacySettings).filter_by(user_id=user_id).first()
        assert db_settings is not None
        assert db_settings.id == settings.id
        
        # Get existing settings
        settings2 = privacy_service.get_or_create_privacy_settings(user_id)
        assert settings2.id == settings.id
    
    def test_process_data_subject_request(self, privacy_service, db):
        """Test processing a data subject request."""
        user_id = 1
        request_type = DataSubjectRequestType.ACCESS
        
        # Create a request
        request = privacy_service.create_data_subject_request(user_id, request_type)
        
        # Mock the export_user_data function
        with mock.patch("core.privacy_compliance.export_user_data") as mock_export:
            mock_export.return_value = {"data": "test"}
            
            # Process the request
            processed_request = privacy_service.process_data_subject_request(request.id)
            
            assert processed_request.id == request.id
            assert processed_request.status == DataSubjectRequestStatus.COMPLETED
            assert processed_request.completed_at is not None
            assert mock_export.called
            mock_export.assert_called_with(user_id, db)


class TestDataRetention:
    """Tests for data retention features."""
    
    def test_apply_retention_policy(self, retention_service, db):
        """Test applying a retention policy to a model."""
        # Create a test data retention policy
        policy = DataRetentionPolicy(
            data_type="test_data",
            retention_period_days=30,
            legal_basis="Testing",
            description="Test policy"
        )
        db.add(policy)
        db.commit()
        
        # Create a mock model class
        class MockModel:
            __tablename__ = "mock_model"
            created_at = None
        
        # Mock the database query and execution
        with mock.patch.object(db, "execute") as mock_execute:
            mock_execute.return_value.scalar.return_value = 5
            
            # Apply retention policy
            count = retention_service.apply_retention_policy(
                MockModel, "test_data", "created_at"
            )
            
            assert count == 5
            assert mock_execute.call_count == 2
    
    def test_anonymize_user_data(self, retention_service, db):
        """Test anonymizing user data."""
        user_id = 1
        
        # Get the user
        user = db.query(User).filter_by(id=user_id).first()
        assert user is not None
        assert user.anonymized is None or user.anonymized is False
        
        # Anonymize the user
        result = retention_service.anonymize_user_data(user_id)
        
        assert result is True
        
        # Check the user was anonymized
        user = db.query(User).filter_by(id=user_id).first()
        assert user.anonymized is True
        assert user.anonymized_at is not None
        assert user.is_active is False
        assert "anonymized" in user.email
    
    def test_delete_expired_files(self, retention_service, tmp_path):
        """Test deleting expired files."""
        # Create test files
        old_file = tmp_path / "old.txt"
        new_file = tmp_path / "new.txt"
        
        old_file.write_text("Old file")
        new_file.write_text("New file")
        
        # Set old file's modification time to 10 days ago
        old_time = datetime.now() - timedelta(days=10)
        os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))
        
        # Apply retention policy (7 days)
        with mock.patch.dict("core.data_retention.RETENTION_POLICY_CONFIG", {"test": 7}):
            count = retention_service.delete_expired_files(tmp_path, "test")
            
            assert count == 1
            assert not old_file.exists()
            assert new_file.exists()


# Test the convenience functions
def test_record_consent_function(db):
    """Test the record_consent convenience function."""
    user_id = 1
    consent_type = ConsentType.ANALYTICS
    granted = True
    
    consent = record_consent(user_id, consent_type, granted, db=db)
    
    assert consent.id is not None
    assert consent.user_id == user_id
    assert consent.consent_type == consent_type
    assert consent.granted == granted


def test_check_consent_function(db):
    """Test the check_consent convenience function."""
    user_id = 1
    consent_type = ConsentType.ANALYTICS
    
    # Record consent
    record_consent(user_id, consent_type, True, db=db)
    
    # Check consent
    result = check_consent(user_id, consent_type, db=db)
    
    assert result is True


def test_create_data_subject_request_function(db):
    """Test the create_data_subject_request convenience function."""
    user_id = 1
    request_type = DataSubjectRequestType.DELETE
    
    request = create_data_subject_request(user_id, request_type, db=db)
    
    assert request.id is not None
    assert request.user_id == user_id
    assert request.request_type == request_type
    assert request.status == DataSubjectRequestStatus.PENDING


def test_log_data_processing_function(db):
    """Test the log_data_processing convenience function."""
    activity_type = "test_function"
    user_id = 1
    
    log = log_data_processing(activity_type, user_id, db=db)
    
    assert log.id is not None
    assert log.activity_type == activity_type
    assert log.user_id == user_id 