#!/usr/bin/env python3
"""
Test Encryption Functionality

This script tests the encryption and privacy features implemented in Task 35.
"""

import json
import logging
import os
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import encryption modules
from core.encryption import (
    encryption_service, key_manager, derive_key_from_password, EncryptionError
)
from core.file_encryption import encrypt_file, decrypt_file, verify_file_integrity
from core.data_retention import apply_retention_policy, get_retention_policy
from core.privacy_compliance import (
    record_consent, check_consent, record_data_subject_request, 
    anonymize_user_data, export_user_data
)
from db.database import SessionLocal, engine, create_database, Base
from db.privacy_models import (
    UserConsent, ConsentType, DataSubjectRequest, DataSubjectRequestType,
    DataSubjectRequestStatus, DataProcessingLog, DataBreachLog, PrivacySettings,
    DataRetentionPolicy
)
from db.encrypted_fields import CustomEncryptionEngine
from db.models import User, Role


def setup_test_database():
    """Set up a test database with required tables."""
    logger.info("Setting up test database...")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create a test user
    db = SessionLocal()
    try:
        # Check if test user exists
        test_user = db.query(User).filter_by(username="testuser").first()
        if not test_user:
            test_user = User(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed_password_for_testing",
                is_active=True,
                role=Role.USER
            )
            db.add(test_user)
            db.commit()
            logger.info("Created test user")
    except Exception as e:
        logger.error(f"Failed to create test user: {str(e)}")
        db.rollback()
    finally:
        db.close()


def test_key_management():
    """Test key management functionality"""
    logger.info("Testing key management...")
    
    # Get current key ID
    current_key_id = key_manager.current_key["id"]
    logger.info(f"Current key ID: {current_key_id}")
    
    # Test key rotation
    old_key_id, new_key_id = key_manager.rotate_key()
    logger.info(f"Key rotated: {old_key_id} -> {new_key_id}")
    
    # Verify we can still access the old key
    old_key = key_manager.get_key_by_id(old_key_id)
    assert old_key is not None, "Could not retrieve old key"
    logger.info("Successfully retrieved old key")
    
    # Reset to original key for other tests
    key_manager.current_key = key_manager.old_keys[old_key_id]
    logger.info("Key management tests passed")


def test_encryption_service():
    """Test encryption service functionality"""
    logger.info("Testing encryption service...")
    
    # Test string encryption/decryption
    test_string = "This is a test string with special chars: !@#$%^&*()"
    encrypted_data = encryption_service.encrypt(test_string)
    logger.info(f"Encrypted data: {encrypted_data}")
    
    # Verify encrypted data has the right format
    assert "encrypted" in encrypted_data, "Encrypted data missing 'encrypted' field"
    assert "key_id" in encrypted_data, "Encrypted data missing 'key_id' field"
    
    # Test decryption
    decrypted_string = encryption_service.decrypt_to_string(encrypted_data)
    assert decrypted_string == test_string, "Decrypted string doesn't match original"
    logger.info("String encryption/decryption successful")
    
    # Test binary data encryption/decryption
    test_bytes = os.urandom(1024)  # 1KB of random data
    encrypted_bytes = encryption_service.encrypt(test_bytes)
    decrypted_bytes = encryption_service.decrypt(encrypted_bytes)
    assert decrypted_bytes == test_bytes, "Decrypted bytes don't match original"
    logger.info("Binary encryption/decryption successful")
    
    logger.info("Encryption service tests passed")


def test_file_encryption():
    """Test file encryption functionality"""
    logger.info("Testing file encryption...")
    
    # Create a test file
    test_file_path = "test_file.txt"
    test_content = "This is a test file for encryption.\n" * 100
    with open(test_file_path, "w") as f:
        f.write(test_content)
    
    # Encrypt the file
    encrypted_file_path = "test_file.enc"
    metadata = encrypt_file(test_file_path, encrypted_file_path)
    logger.info(f"File encrypted with metadata: {metadata}")
    
    # Verify encrypted file exists and is different from original
    assert os.path.exists(encrypted_file_path), "Encrypted file was not created"
    with open(encrypted_file_path, "rb") as f:
        encrypted_content = f.read()
    assert test_content.encode() not in encrypted_content, "File doesn't appear to be encrypted"
    
    # Decrypt the file
    decrypted_file_path = "test_file_decrypted.txt"
    decrypt_file(encrypted_file_path, decrypted_file_path, metadata)
    
    # Verify decrypted content matches original
    with open(decrypted_file_path, "r") as f:
        decrypted_content = f.read()
    assert decrypted_content == test_content, "Decrypted content doesn't match original"
    
    # Test integrity verification
    integrity_result = verify_file_integrity(encrypted_file_path, metadata)
    assert integrity_result, "File integrity verification failed"
    logger.info("File integrity verification successful")
    
    # Clean up test files
    for file_path in [test_file_path, encrypted_file_path, decrypted_file_path]:
        if os.path.exists(file_path):
            os.remove(file_path)
    
    logger.info("File encryption tests passed")


def test_data_retention():
    """Test data retention functionality"""
    logger.info("Testing data retention...")
    
    # Get a database session
    db = SessionLocal()
    
    try:
        # Verify default retention policies were created
        policies = db.query(DataRetentionPolicy).all()
        assert len(policies) >= 5, "Default retention policies not found"
        logger.info(f"Found {len(policies)} retention policies")
        
        # Test getting a specific policy
        user_data_policy = get_retention_policy("user_data", db)
        assert user_data_policy is not None, "Could not retrieve user_data retention policy"
        logger.info(f"User data retention period: {user_data_policy.retention_period_days} days")
        
        # Test applying retention policy (this is just a simulation)
        result = apply_retention_policy("analytics_data", db, simulate=True)
        logger.info(f"Retention policy simulation result: {result}")
        
    finally:
        db.close()
    
    logger.info("Data retention tests passed")


def test_privacy_compliance():
    """Test privacy compliance functionality"""
    logger.info("Testing privacy compliance...")
    
    # Get a database session
    db = SessionLocal()
    
    try:
        # Get test user
        test_user = db.query(User).filter_by(username="testuser").first()
        if not test_user:
            logger.warning("Test user not found, skipping privacy compliance tests")
            return
        
        user_id = test_user.id
        
        # Test consent recording
        consent_result = record_consent(
            user_id=user_id,
            consent_type=ConsentType.MARKETING,
            granted=True,
            db=db
        )
        logger.info(f"Recorded consent: {consent_result}")
        
        # Test consent checking
        has_consent = check_consent(user_id, ConsentType.MARKETING, db)
        assert has_consent, "Consent check failed"
        logger.info("Consent check successful")
        
        # Test data subject request
        request_result = record_data_subject_request(
            user_id=user_id,
            request_type=DataSubjectRequestType.ACCESS,
            request_details="Test access request",
            db=db
        )
        logger.info(f"Recorded data subject request: {request_result}")
        
        # Clean up test data
        db.query(UserConsent).filter_by(user_id=user_id).delete()
        db.query(DataSubjectRequest).filter_by(user_id=user_id).delete()
        db.commit()
        
    finally:
        db.close()
    
    logger.info("Privacy compliance tests passed")


def test_custom_encryption_engine():
    """Test the custom encryption engine for SQLAlchemy-Utils"""
    logger.info("Testing custom encryption engine...")
    
    # Create an instance of the engine
    engine = CustomEncryptionEngine()
    
    # Test encryption
    test_value = "sensitive data"
    encrypted_value = engine.encrypt(test_value)
    logger.info(f"Encrypted value: {encrypted_value}")
    
    # Test decryption
    decrypted_value = engine.decrypt(encrypted_value)
    assert decrypted_value == test_value, "Custom engine decryption failed"
    logger.info("Custom encryption engine tests passed")


def run_all_tests():
    """Run all encryption and privacy tests"""
    try:
        logger.info("Starting encryption and privacy tests...")
        
        # Set up test database
        setup_test_database()
        
        # Run tests
        test_key_management()
        test_encryption_service()
        test_file_encryption()
        test_data_retention()
        test_privacy_compliance()
        test_custom_encryption_engine()
        
        logger.info("All tests passed successfully!")
        return True
    except Exception as e:
        logger.error(f"Tests failed: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
