"""
Encrypted Database Fields

This module provides encrypted field types for SQLAlchemy models.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast

from sqlalchemy import Column, TypeDecorator, String, Text, LargeBinary
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy_utils import EncryptedType, StringEncryptedType

from core.encryption import encryption_service, EncryptionError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CustomEncryptionEngine:
    """
    Custom encryption engine using our EncryptionService.
    This allows us to use our key rotation system with SQLAlchemy-Utils.
    """
    
    def encrypt(self, value: str) -> str:
        """
        Encrypt a value using our encryption service.
        
        Args:
            value: Value to encrypt
            
        Returns:
            JSON string containing encrypted data and metadata
        """
        try:
            encrypted_data = encryption_service.encrypt(value)
            return json.dumps(encrypted_data)
        except Exception as e:
            logger.error(f"Failed to encrypt value: {str(e)}")
            raise
    
    def decrypt(self, value: str) -> str:
        """
        Decrypt a value using our encryption service.
        
        Args:
            value: JSON string containing encrypted data and metadata
            
        Returns:
            Decrypted value
        """
        try:
            encrypted_data = json.loads(value)
            return encryption_service.decrypt_to_string(encrypted_data)
        except Exception as e:
            logger.error(f"Failed to decrypt value: {str(e)}")
            raise


# Create a global encryption engine instance
encryption_engine = CustomEncryptionEngine()


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy type for encrypted strings.
    Uses our custom encryption engine.
    """
    
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """Encrypt value before saving to database."""
        if value is None:
            return None
        return encryption_engine.encrypt(value)
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """Decrypt value when loading from database."""
        if value is None:
            return None
        return encryption_engine.decrypt(value)


class EncryptedJSON(TypeDecorator):
    """
    SQLAlchemy type for encrypted JSON data.
    Serializes to JSON before encryption and deserializes after decryption.
    """
    
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value: Optional[Union[Dict, List]], dialect) -> Optional[str]:
        """Convert to JSON and encrypt before saving to database."""
        if value is None:
            return None
        json_value = json.dumps(value)
        return encryption_engine.encrypt(json_value)
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[Union[Dict, List]]:
        """Decrypt and parse JSON when loading from database."""
        if value is None:
            return None
        json_value = encryption_engine.decrypt(value)
        return json.loads(json_value)


class EncryptedBinary(TypeDecorator):
    """
    SQLAlchemy type for encrypted binary data.
    """
    
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value: Optional[bytes], dialect) -> Optional[str]:
        """Encrypt binary data before saving to database."""
        if value is None:
            return None
        encrypted_data = encryption_service.encrypt(value)
        return json.dumps(encrypted_data)
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[bytes]:
        """Decrypt binary data when loading from database."""
        if value is None:
            return None
        encrypted_data = json.loads(value)
        return encryption_service.decrypt(encrypted_data)


# Create mutable dictionary and list types that work with encrypted JSON
class MutableEncryptedDict(MutableDict):
    """Mutable dictionary that automatically encrypts/decrypts."""
    
    @classmethod
    def coerce(cls, key, value):
        """Convert plain dictionaries to MutableEncryptedDict."""
        if value is None:
            return None
        return MutableDict.coerce(key, value)


class MutableEncryptedList(MutableList):
    """Mutable list that automatically encrypts/decrypts."""
    
    @classmethod
    def coerce(cls, key, value):
        """Convert plain lists to MutableEncryptedList."""
        if value is None:
            return None
        return MutableList.coerce(key, value)


# Helper functions to create encrypted columns
def encrypted_string_column(*args, **kwargs) -> Column:
    """
    Create an encrypted string column.
    
    Args:
        *args: Positional arguments for Column
        **kwargs: Keyword arguments for Column
        
    Returns:
        SQLAlchemy Column with encrypted string type
    """
    return Column(EncryptedString(), *args, **kwargs)


def encrypted_json_column(*args, **kwargs) -> Column:
    """
    Create an encrypted JSON column.
    
    Args:
        *args: Positional arguments for Column
        **kwargs: Keyword arguments for Column
        
    Returns:
        SQLAlchemy Column with encrypted JSON type
    """
    return Column(EncryptedJSON(), *args, **kwargs)


def encrypted_binary_column(*args, **kwargs) -> Column:
    """
    Create an encrypted binary column.
    
    Args:
        *args: Positional arguments for Column
        **kwargs: Keyword arguments for Column
        
    Returns:
        SQLAlchemy Column with encrypted binary type
    """
    return Column(EncryptedBinary(), *args, **kwargs) 