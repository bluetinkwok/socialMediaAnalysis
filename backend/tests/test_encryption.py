"""
Tests for the encryption system.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

import pytest
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

from core.encryption import (
    KeyManager, EncryptionService, encryption_service, key_manager,
    EncryptionError, KeyManagementError
)
from core.file_encryption import FileEncryptor, encrypt_file, decrypt_file
from db.encrypted_fields import (
    EncryptedString, EncryptedJSON, EncryptedBinary,
    encrypted_string_column, encrypted_json_column, encrypted_binary_column
)


class TestKeyManager:
    """Tests for the KeyManager class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.key_dir = Path(self.temp_dir.name) / ".keys"
        self.key_dir.mkdir(mode=0o700, exist_ok=True)
        self.key_manager = KeyManager(key_dir=str(self.key_dir))
    
    def teardown_method(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()
    
    def test_initialize(self):
        """Test key manager initialization."""
        self.key_manager.initialize()
        assert self.key_manager.current_key is not None
        assert "id" in self.key_manager.current_key
        assert "key" in self.key_manager.current_key
        assert "created_at" in self.key_manager.current_key
        assert "expires_at" in self.key_manager.current_key
    
    def test_get_current_key(self):
        """Test getting the current key."""
        self.key_manager.initialize()
        key = self.key_manager.get_current_key()
        assert isinstance(key, bytes)
        assert len(key) == 32  # Fernet key is 32 bytes
    
    def test_rotate_key(self):
        """Test key rotation."""
        self.key_manager.initialize()
        old_key_id = self.key_manager.current_key["id"]
        
        old_id, new_id = self.key_manager.rotate_key()
        
        assert old_id == old_key_id
        assert new_id != old_key_id
        assert old_key_id in self.key_manager.old_keys
    
    def test_get_key_by_id(self):
        """Test retrieving a key by ID."""
        self.key_manager.initialize()
        key_id = self.key_manager.current_key["id"]
        
        key = self.key_manager.get_key_by_id(key_id)
        
        assert key is not None
        assert isinstance(key, bytes)
        assert len(key) == 32
        
        # Test with non-existent key ID
        assert self.key_manager.get_key_by_id("nonexistent") is None


class TestEncryptionService:
    """Tests for the EncryptionService class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.key_dir = Path(self.temp_dir.name) / ".keys"
        self.key_dir.mkdir(mode=0o700, exist_ok=True)
        self.key_manager = KeyManager(key_dir=str(self.key_dir))
        self.key_manager.initialize()
        self.encryption_service = EncryptionService(self.key_manager)
    
    def teardown_method(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()
    
    def test_encrypt_decrypt_string(self):
        """Test encrypting and decrypting a string."""
        original = "This is a test string"
        
        encrypted = self.encryption_service.encrypt(original)
        
        assert isinstance(encrypted, dict)
        assert "data" in encrypted
        assert "key_id" in encrypted
        assert "timestamp" in encrypted
        
        decrypted = self.encryption_service.decrypt_to_string(encrypted)
        
        assert decrypted == original
    
    def test_encrypt_decrypt_bytes(self):
        """Test encrypting and decrypting bytes."""
        original = b"This is a test byte string"
        
        encrypted = self.encryption_service.encrypt(original)
        
        assert isinstance(encrypted, dict)
        assert "data" in encrypted
        assert "key_id" in encrypted
        assert "timestamp" in encrypted
        
        decrypted = self.encryption_service.decrypt(encrypted)
        
        assert decrypted == original
    
    def test_key_rotation(self):
        """Test encryption with key rotation."""
        original = "This is a test string"
        
        # Encrypt with the current key
        encrypted = self.encryption_service.encrypt(original)
        key_id = encrypted["key_id"]
        
        # Rotate the key
        self.key_manager.rotate_key()
        
        # Should still be able to decrypt with the old key
        decrypted = self.encryption_service.decrypt_to_string(encrypted)
        assert decrypted == original
        
        # Encrypt with the new key
        new_encrypted = self.encryption_service.encrypt(original)
        assert new_encrypted["key_id"] != key_id


class TestFileEncryption:
    """Tests for file encryption."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.key_dir = Path(self.temp_dir.name) / ".keys"
        self.key_dir.mkdir(mode=0o700, exist_ok=True)
        self.key_manager = KeyManager(key_dir=str(self.key_dir))
        self.key_manager.initialize()
        self.encryption_service = EncryptionService(self.key_manager)
        self.file_encryptor = FileEncryptor()
        
        # Create a test file
        self.test_file = Path(self.temp_dir.name) / "test.txt"
        with open(self.test_file, "w") as f:
            f.write("This is a test file content")
    
    def teardown_method(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()
    
    def test_encrypt_decrypt_file(self):
        """Test encrypting and decrypting a file."""
        # Encrypt the file
        encrypted_path, metadata = self.file_encryptor.encrypt_file(self.test_file)
        
        assert encrypted_path.exists()
        assert Path(str(encrypted_path) + ".meta").exists()
        assert encrypted_path != self.test_file
        
        # Decrypt the file
        decrypted_path = self.file_encryptor.decrypt_file(encrypted_path)
        
        assert decrypted_path.exists()
        
        # Check content
        with open(decrypted_path, "r") as f:
            content = f.read()
        
        assert content == "This is a test file content"
    
    def test_encrypt_decrypt_file_functions(self):
        """Test the convenience functions for file encryption."""
        # Encrypt the file
        encrypted_path, metadata = encrypt_file(self.test_file)
        
        assert encrypted_path.exists()
        assert Path(str(encrypted_path) + ".meta").exists()
        
        # Decrypt the file
        decrypted_path = decrypt_file(encrypted_path)
        
        assert decrypted_path.exists()
        
        # Check content
        with open(decrypted_path, "r") as f:
            content = f.read()
        
        assert content == "This is a test file content"


# Create a test model for encrypted fields
Base = declarative_base()

class TestModel(Base):
    """Test model with encrypted fields."""
    __tablename__ = "test_encrypted"
    
    id = Column(Integer, primary_key=True)
    encrypted_str = Column(EncryptedString)
    encrypted_json = Column(EncryptedJSON)
    encrypted_binary = Column(EncryptedBinary)
    helper_str = encrypted_string_column()
    helper_json = encrypted_json_column()
    helper_binary = encrypted_binary_column()


class TestEncryptedFields:
    """Tests for encrypted database fields."""
    
    def test_encrypted_string(self):
        """Test EncryptedString field."""
        field = EncryptedString()
        
        original = "This is a test string"
        encrypted = field.process_bind_param(original, None)
        
        assert encrypted != original
        assert isinstance(encrypted, str)
        
        decrypted = field.process_result_value(encrypted, None)
        
        assert decrypted == original
    
    def test_encrypted_json(self):
        """Test EncryptedJSON field."""
        field = EncryptedJSON()
        
        original = {"key": "value", "nested": {"list": [1, 2, 3]}}
        encrypted = field.process_bind_param(original, None)
        
        assert encrypted != json.dumps(original)
        assert isinstance(encrypted, str)
        
        decrypted = field.process_result_value(encrypted, None)
        
        assert decrypted == original
    
    def test_encrypted_binary(self):
        """Test EncryptedBinary field."""
        field = EncryptedBinary()
        
        original = b"This is binary data"
        encrypted = field.process_bind_param(original, None)
        
        assert encrypted != original
        assert isinstance(encrypted, str)
        
        decrypted = field.process_result_value(encrypted, None)
        
        assert decrypted == original
    
    def test_helper_functions(self):
        """Test helper functions for creating encrypted columns."""
        str_col = encrypted_string_column()
        json_col = encrypted_json_column()
        binary_col = encrypted_binary_column()
        
        assert isinstance(str_col.type, EncryptedString)
        assert isinstance(json_col.type, EncryptedJSON)
        assert isinstance(binary_col.type, EncryptedBinary) 