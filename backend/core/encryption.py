"""
Encryption Utilities

This module provides utilities for encryption, key management, and secure data handling.
"""

import base64
import json
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy.orm import Session

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Constants
KEY_ROTATION_DAYS = 90  # Number of days before rotating keys
KEY_DIRECTORY = ".keys"  # Directory to store keys (relative to project root)
CURRENT_KEY_FILE = "current_key.json"  # File to store current key info
KEY_PREFIX = "key_"  # Prefix for key files


class EncryptionError(Exception):
    """Base exception for encryption-related errors."""
    pass


class KeyManagementError(EncryptionError):
    """Exception for key management errors."""
    pass


class KeyManager:
    """
    Handles encryption key management including generation, storage, retrieval, and rotation.
    """
    
    def __init__(self, key_dir: Optional[str] = None):
        """
        Initialize the key manager.
        
        Args:
            key_dir: Directory to store keys (defaults to .keys in project root)
        """
        self.key_dir = Path(key_dir or KEY_DIRECTORY)
        self._ensure_key_directory()
        self.current_key = None
        self.old_keys = {}
    
    def _ensure_key_directory(self) -> None:
        """Ensure the key directory exists with proper permissions."""
        if not self.key_dir.exists():
            self.key_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        elif self.key_dir.stat().st_mode & 0o777 != 0o700:
            # Fix permissions if needed
            os.chmod(self.key_dir, 0o700)
    
    def initialize(self) -> None:
        """
        Initialize the key manager by loading existing keys or generating new ones.
        """
        try:
            # Try to load the current key
            if not self._load_current_key():
                # Generate a new key if none exists
                self._generate_new_key()
            
            # Load any old keys
            self._load_old_keys()
            
            # Check if key rotation is needed
            self._check_key_rotation()
            
        except Exception as e:
            logger.error(f"Failed to initialize key manager: {str(e)}")
            raise KeyManagementError(f"Key manager initialization failed: {str(e)}")
    
    def get_current_key(self) -> bytes:
        """
        Get the current encryption key.
        
        Returns:
            The current encryption key as bytes
        
        Raises:
            KeyManagementError: If no current key is available
        """
        if not self.current_key:
            self.initialize()
        
        if not self.current_key:
            raise KeyManagementError("No current encryption key available")
        
        return base64.urlsafe_b64decode(self.current_key["key"])
    
    def get_key_by_id(self, key_id: str) -> Optional[bytes]:
        """
        Get a specific key by its ID.
        
        Args:
            key_id: The ID of the key to retrieve
            
        Returns:
            The encryption key as bytes, or None if not found
        """
        # Check if it's the current key
        if self.current_key and self.current_key["id"] == key_id:
            return base64.urlsafe_b64decode(self.current_key["key"])
        
        # Check old keys
        if key_id in self.old_keys:
            return base64.urlsafe_b64decode(self.old_keys[key_id]["key"])
        
        # Try to load from file
        key_path = self.key_dir / f"{KEY_PREFIX}{key_id}.json"
        if key_path.exists():
            try:
                with open(key_path, "r") as f:
                    key_data = json.load(f)
                return base64.urlsafe_b64decode(key_data["key"])
            except Exception as e:
                logger.error(f"Failed to load key {key_id}: {str(e)}")
        
        return None
    
    def rotate_key(self) -> Tuple[str, str]:
        """
        Rotate the encryption key by generating a new one and archiving the old one.
        
        Returns:
            Tuple of (old_key_id, new_key_id)
            
        Raises:
            KeyManagementError: If key rotation fails
        """
        try:
            if not self.current_key:
                self.initialize()
                return ("none", self.current_key["id"])
            
            old_key_id = self.current_key["id"]
            
            # Archive the current key
            if old_key_id not in self.old_keys:
                self.old_keys[old_key_id] = self.current_key
            
            # Generate a new key
            self._generate_new_key()
            
            logger.info(f"Encryption key rotated: {old_key_id} -> {self.current_key['id']}")
            return (old_key_id, self.current_key["id"])
            
        except Exception as e:
            logger.error(f"Failed to rotate encryption key: {str(e)}")
            raise KeyManagementError(f"Key rotation failed: {str(e)}")
    
    def _generate_new_key(self) -> None:
        """Generate a new encryption key and save it as the current key."""
        # Generate a new Fernet key
        key = Fernet.generate_key()
        key_id = secrets.token_hex(8)
        
        # Create key metadata
        key_data = {
            "id": key_id,
            "key": key.decode("ascii"),  # Store as string
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=KEY_ROTATION_DAYS)).isoformat()
        }
        
        # Save as current key
        self.current_key = key_data
        
        # Save to file
        current_key_path = self.key_dir / CURRENT_KEY_FILE
        with open(current_key_path, "w") as f:
            json.dump(key_data, f)
        os.chmod(current_key_path, 0o600)
        
        # Also save to individual key file
        key_path = self.key_dir / f"{KEY_PREFIX}{key_id}.json"
        with open(key_path, "w") as f:
            json.dump(key_data, f)
        os.chmod(key_path, 0o600)
    
    def _load_current_key(self) -> bool:
        """
        Load the current encryption key from file.
        
        Returns:
            True if key was loaded successfully, False otherwise
        """
        current_key_path = self.key_dir / CURRENT_KEY_FILE
        if not current_key_path.exists():
            return False
        
        try:
            with open(current_key_path, "r") as f:
                self.current_key = json.load(f)
            return True
        except Exception as e:
            logger.error(f"Failed to load current key: {str(e)}")
            return False
    
    def _load_old_keys(self) -> None:
        """Load all old encryption keys from files."""
        self.old_keys = {}
        
        for key_file in self.key_dir.glob(f"{KEY_PREFIX}*.json"):
            try:
                with open(key_file, "r") as f:
                    key_data = json.load(f)
                
                key_id = key_data["id"]
                if not self.current_key or key_id != self.current_key["id"]:
                    self.old_keys[key_id] = key_data
            except Exception as e:
                logger.warning(f"Failed to load key file {key_file.name}: {str(e)}")
    
    def _check_key_rotation(self) -> None:
        """Check if the current key needs rotation based on its age."""
        if not self.current_key:
            return
        
        try:
            created_at = datetime.fromisoformat(self.current_key["created_at"])
            expires_at = datetime.fromisoformat(self.current_key["expires_at"])
            
            # Rotate if the key has expired
            if datetime.now(timezone.utc) >= expires_at:
                logger.info("Encryption key has expired, rotating...")
                self.rotate_key()
        except Exception as e:
            logger.error(f"Failed to check key rotation: {str(e)}")


class EncryptionService:
    """
    Service for encrypting and decrypting data using Fernet symmetric encryption.
    """
    
    def __init__(self, key_manager: Optional[KeyManager] = None):
        """
        Initialize the encryption service.
        
        Args:
            key_manager: Key manager instance (creates a new one if not provided)
        """
        self.key_manager = key_manager or KeyManager()
        self.key_manager.initialize()
    
    def encrypt(self, data: Union[str, bytes]) -> Dict[str, str]:
        """
        Encrypt data using the current key.
        
        Args:
            data: Data to encrypt (string or bytes)
            
        Returns:
            Dictionary containing the encrypted data and metadata
            {
                "encrypted": base64-encoded encrypted data,
                "key_id": ID of the key used for encryption
            }
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            # Get the current key
            key = self.key_manager.get_current_key()
            key_id = self.key_manager.current_key["id"]
            
            # Convert data to bytes if it's a string
            if isinstance(data, str):
                data_bytes = data.encode("utf-8")
            else:
                data_bytes = data
            
            # Encrypt the data
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(data_bytes)
            
            # Return the encrypted data and metadata
            return {
                "encrypted": base64.b64encode(encrypted_data).decode("ascii"),
                "key_id": key_id
            }
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise EncryptionError(f"Failed to encrypt data: {str(e)}")
    
    def decrypt(self, encrypted_data: Dict[str, str]) -> bytes:
        """
        Decrypt data using the specified key.
        
        Args:
            encrypted_data: Dictionary containing the encrypted data and metadata
            {
                "encrypted": base64-encoded encrypted data,
                "key_id": ID of the key used for encryption
            }
            
        Returns:
            Decrypted data as bytes
            
        Raises:
            EncryptionError: If decryption fails
        """
        try:
            # Get the key ID and encrypted data
            key_id = encrypted_data.get("key_id")
            encrypted = encrypted_data.get("encrypted")
            
            if not key_id or not encrypted:
                raise EncryptionError("Missing key_id or encrypted data")
            
            # Get the key
            key = self.key_manager.get_key_by_id(key_id)
            if not key:
                raise EncryptionError(f"Key not found: {key_id}")
            
            # Decrypt the data
            fernet = Fernet(key)
            decrypted_data = fernet.decrypt(base64.b64decode(encrypted))
            
            return decrypted_data
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise EncryptionError(f"Failed to decrypt data: {str(e)}")
    
    def decrypt_to_string(self, encrypted_data: Dict[str, str]) -> str:
        """
        Decrypt data and return as a string.
        
        Args:
            encrypted_data: Dictionary containing the encrypted data and metadata
            
        Returns:
            Decrypted data as a string
            
        Raises:
            EncryptionError: If decryption fails
        """
        decrypted = self.decrypt(encrypted_data)
        return decrypted.decode("utf-8")


# Create global instances for convenience
key_manager = KeyManager()
encryption_service = EncryptionService(key_manager)


def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Derive an encryption key from a password using PBKDF2.
    
    Args:
        password: Password to derive key from
        salt: Salt for key derivation (generates a new one if not provided)
        
    Returns:
        Tuple of (key, salt)
    """
    if not salt:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt


def get_encryption_service() -> EncryptionService:
    """
    Get the global encryption service instance.
    
    Returns:
        EncryptionService instance
    """
    return encryption_service 