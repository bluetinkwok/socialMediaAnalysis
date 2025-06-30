# Encryption and Privacy Features Documentation

This document provides an overview of the encryption and privacy features implemented in the Social Media Analysis Platform.

## Table of Contents

1. [Introduction](#introduction)
2. [Key Management](#key-management)
3. [Database Encryption](#database-encryption)
4. [File Encryption](#file-encryption)
5. [Data Retention](#data-retention)
6. [Privacy Compliance](#privacy-compliance)
7. [Usage Examples](#usage-examples)
8. [Security Considerations](#security-considerations)

## Introduction

The encryption and privacy features provide secure data handling capabilities for sensitive information, including:

- Secure key management with automatic rotation
- Database field encryption for sensitive data
- File encryption for stored media
- Data retention policies with automated enforcement
- GDPR/CCPA compliance features (consent management, data subject rights)

## Key Management

The key management system handles encryption keys securely, with support for key rotation and multiple active keys.

### Key Features

- Secure key generation using strong cryptographic algorithms
- Secure key storage with proper file permissions
- Automatic key rotation (default: 90 days)
- Support for multiple keys to allow decryption of data encrypted with older keys

### Usage

```python
from core.encryption import key_manager

# Initialize key manager (loads or generates keys)
key_manager.initialize()

# Get the current key
key = key_manager.get_current_key()

# Rotate keys
old_key_id, new_key_id = key_manager.rotate_key()

# Get a specific key by ID
key = key_manager.get_key_by_id(key_id)
```

## Database Encryption

The database encryption system provides field-level encryption for sensitive data.

### Encrypted Field Types

- `EncryptedString`: For sensitive text data
- `EncryptedJSON`: For sensitive JSON data
- `EncryptedBinary`: For sensitive binary data

### Usage

```python
from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declarative_base
from db.encrypted_fields import encrypted_string_column, encrypted_json_column

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)  # Not encrypted
    phone = encrypted_string_column()  # Encrypted
    address = encrypted_string_column()  # Encrypted
    preferences = encrypted_json_column()  # Encrypted JSON
```

## File Encryption

The file encryption system encrypts files stored on disk, with per-file unique encryption keys.

### Key Features

- AES-256-CBC encryption for files
- Per-file unique encryption keys for enhanced security
- Metadata storage for encrypted files
- Integrity verification during decryption
- Streaming encryption/decryption for large files

### Usage

```python
from core.file_encryption import encrypt_file, decrypt_file

# Encrypt a file
encrypted_path, metadata = encrypt_file("/path/to/file.jpg")

# Decrypt a file
decrypted_path = decrypt_file(encrypted_path)
```

## Data Retention

The data retention system enforces configurable retention periods for different types of data.

### Key Features

- Configurable retention periods for different data types
- Automated enforcement of retention policies
- Secure deletion of expired data
- Data anonymization for expired user data

### Usage

```python
from core.data_retention import apply_retention_policy, delete_expired_files
from models.analytics import AnalyticsData

# Apply retention policy to database records
deleted_count = apply_retention_policy(
    AnalyticsData, 
    policy_type="analytics_data",
    date_column="created_at"
)

# Delete expired files
deleted_count = delete_expired_files(
    "/path/to/uploads",
    policy_type="temporary_files",
    recursive=True
)
```

## Privacy Compliance

The privacy compliance system provides features for GDPR/CCPA compliance.

### Key Features

- Consent management for different purposes
- Data subject rights handling (access, deletion, etc.)
- Privacy settings management
- Data processing activity logging

### Usage

```python
from core.privacy_compliance import (
    record_consent, check_consent, create_data_subject_request,
    process_data_subject_request, log_data_processing
)
from db.privacy_models import ConsentType, DataSubjectRequestType

# Record user consent
consent = record_consent(
    user_id=123,
    consent_type=ConsentType.MARKETING,
    granted=True,
    ip_address="192.168.1.1"
)

# Check if user has granted consent
has_consent = check_consent(user_id=123, consent_type=ConsentType.MARKETING)

# Create a data subject request
request = create_data_subject_request(
    user_id=123,
    request_type=DataSubjectRequestType.ACCESS
)

# Process a data subject request
processed_request = process_data_subject_request(request_id=request.id)

# Log data processing activity
log = log_data_processing(
    activity_type="content_analysis",
    user_id=123,
    data_categories=["content", "metadata"],
    processing_purpose="Content analysis for insights",
    legal_basis="Legitimate interest"
)
```

## Usage Examples

### Encrypting Sensitive User Data

```python
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from db.encrypted_fields import encrypted_string_column

Base = declarative_base()

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    public_name = Column(String)  # Not encrypted
    email = encrypted_string_column()  # Encrypted
    phone = encrypted_string_column()  # Encrypted
    address = encrypted_string_column()  # Encrypted
```

### Handling a Data Export Request

```python
from core.privacy_compliance import create_data_subject_request, process_data_subject_request
from db.privacy_models import DataSubjectRequestType

# Create an export request
request = create_data_subject_request(
    user_id=123,
    request_type=DataSubjectRequestType.ACCESS
)

# Process the export request
processed_request = process_data_subject_request(request.id)

# The export data is available in the processed request
```

### Applying Data Retention Policies

```python
from core.data_retention import DataRetentionService

# Create a retention service
retention_service = DataRetentionService()

# Apply retention policies to different data types
retention_service.apply_retention_policy(UserData, "user_data")
retention_service.apply_retention_policy(AnalyticsData, "analytics_data")
retention_service.apply_retention_policy(LogData, "log_data")

# Delete expired files
retention_service.delete_expired_files("uploads/temp", "temporary_files")
```

## Security Considerations

### Key Management

- Encryption keys are stored in a dedicated directory (`.keys`) with restricted permissions (0o700)
- Keys are automatically rotated every 90 days (configurable)
- Old keys are retained to allow decryption of existing data

### Data Encryption

- AES-256-CBC encryption is used for file encryption
- Fernet symmetric encryption is used for database field encryption
- Each file has its own unique encryption key
- File integrity is verified during decryption

### Privacy Controls

- User consent is recorded with IP address and timestamp for audit purposes
- Data subject requests are tracked and logged
- Data processing activities are logged for compliance purposes
- Data retention policies are enforced automatically 