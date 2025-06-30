"""
File Encryption Utilities

This module provides utilities for encrypting and decrypting files on disk.
"""

import base64
import hashlib
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, BinaryIO

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

from core.encryption import encryption_service, key_manager, EncryptionError
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Constants
CHUNK_SIZE = 64 * 1024  # 64KB chunks for streaming encryption/decryption
METADATA_SUFFIX = ".meta"  # Suffix for metadata files


class FileEncryptionError(EncryptionError):
    """Exception for file encryption errors."""
    pass


class FileEncryptor:
    """
    Handles encryption and decryption of files on disk.
    """
    
    def __init__(self):
        """Initialize the file encryptor."""
        pass
    
    def encrypt_file(
        self, 
        source_path: Union[str, Path], 
        target_path: Optional[Union[str, Path]] = None
    ) -> Tuple[Path, Dict]:
        """
        Encrypt a file and save the encrypted version.
        
        Args:
            source_path: Path to the file to encrypt
            target_path: Path where to save the encrypted file (defaults to source_path + '.enc')
            
        Returns:
            Tuple of (encrypted_file_path, metadata)
            
        Raises:
            FileEncryptionError: If encryption fails
        """
        try:
            source_path = Path(source_path)
            if not source_path.exists():
                raise FileEncryptionError(f"Source file not found: {source_path}")
            
            if target_path is None:
                target_path = Path(str(source_path) + '.enc')
            else:
                target_path = Path(target_path)
            
            # Create target directory if it doesn't exist
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Get file info
            file_size = source_path.stat().st_size
            file_hash = self._calculate_file_hash(source_path)
            
            # Generate a unique file key for this file
            file_key = Fernet.generate_key()
            
            # Encrypt the file key with our master key
            encrypted_key_data = encryption_service.encrypt(file_key)
            
            # Create metadata
            metadata = {
                "original_filename": source_path.name,
                "original_size": file_size,
                "original_hash": file_hash,
                "encryption_method": "AES-256-CBC",
                "encrypted_key": encrypted_key_data,
                "encrypted_at": str(Path.now().timestamp())
            }
            
            # Save metadata
            metadata_path = Path(str(target_path) + METADATA_SUFFIX)
            with open(metadata_path, "w") as f:
                json.dump(metadata, f)
            
            # Encrypt the file
            self._encrypt_file_with_key(source_path, target_path, file_key)
            
            logger.info(f"File encrypted: {source_path} -> {target_path}")
            return target_path, metadata
            
        except Exception as e:
            logger.error(f"Failed to encrypt file {source_path}: {str(e)}")
            # Clean up any partial files
            if target_path and Path(target_path).exists():
                Path(target_path).unlink(missing_ok=True)
            if metadata_path and Path(metadata_path).exists():
                Path(metadata_path).unlink(missing_ok=True)
            raise FileEncryptionError(f"Failed to encrypt file: {str(e)}")
    
    def decrypt_file(
        self, 
        source_path: Union[str, Path], 
        target_path: Optional[Union[str, Path]] = None
    ) -> Path:
        """
        Decrypt a file and save the decrypted version.
        
        Args:
            source_path: Path to the encrypted file
            target_path: Path where to save the decrypted file
            
        Returns:
            Path to the decrypted file
            
        Raises:
            FileEncryptionError: If decryption fails
        """
        try:
            source_path = Path(source_path)
            if not source_path.exists():
                raise FileEncryptionError(f"Source file not found: {source_path}")
            
            # Load metadata
            metadata_path = Path(str(source_path) + METADATA_SUFFIX)
            if not metadata_path.exists():
                raise FileEncryptionError(f"Metadata file not found: {metadata_path}")
            
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            
            # Determine target path
            if target_path is None:
                # Use original filename in the same directory as the encrypted file
                target_path = source_path.parent / metadata["original_filename"]
            else:
                target_path = Path(target_path)
            
            # Create target directory if it doesn't exist
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Decrypt the file key
            encrypted_key_data = metadata["encrypted_key"]
            file_key = encryption_service.decrypt(encrypted_key_data)
            
            # Decrypt the file
            self._decrypt_file_with_key(source_path, target_path, file_key)
            
            # Verify the decrypted file
            if target_path.stat().st_size != metadata["original_size"]:
                logger.warning(f"Decrypted file size mismatch: {target_path.stat().st_size} != {metadata['original_size']}")
            
            decrypted_hash = self._calculate_file_hash(target_path)
            if decrypted_hash != metadata["original_hash"]:
                logger.warning(f"Decrypted file hash mismatch: {decrypted_hash} != {metadata['original_hash']}")
            
            logger.info(f"File decrypted: {source_path} -> {target_path}")
            return target_path
            
        except Exception as e:
            logger.error(f"Failed to decrypt file {source_path}: {str(e)}")
            # Clean up any partial files
            if target_path and Path(target_path).exists():
                Path(target_path).unlink(missing_ok=True)
            raise FileEncryptionError(f"Failed to decrypt file: {str(e)}")
    
    def _encrypt_file_with_key(
        self, 
        source_path: Path, 
        target_path: Path, 
        key: bytes
    ) -> None:
        """
        Encrypt a file using the provided key.
        
        Args:
            source_path: Path to the file to encrypt
            target_path: Path where to save the encrypted file
            key: Encryption key
            
        Raises:
            FileEncryptionError: If encryption fails
        """
        try:
            # Generate IV
            iv = os.urandom(16)
            
            # Create cipher
            cipher = Cipher(algorithms.AES(key[:32]), modes.CBC(iv))
            encryptor = cipher.encryptor()
            padder = padding.PKCS7(algorithms.AES.block_size).padder()
            
            with open(source_path, "rb") as src, open(target_path, "wb") as dst:
                # Write IV at the beginning of the file
                dst.write(iv)
                
                while True:
                    chunk = src.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    
                    # Pad the last chunk
                    if len(chunk) < CHUNK_SIZE:
                        chunk = padder.update(chunk) + padder.finalize()
                    
                    # Encrypt and write
                    encrypted_chunk = encryptor.update(chunk)
                    dst.write(encrypted_chunk)
                
                # Write the final block
                final_block = encryptor.finalize()
                if final_block:
                    dst.write(final_block)
                
        except Exception as e:
            logger.error(f"Failed to encrypt file with key: {str(e)}")
            raise FileEncryptionError(f"Failed to encrypt file with key: {str(e)}")
    
    def _decrypt_file_with_key(
        self, 
        source_path: Path, 
        target_path: Path, 
        key: bytes
    ) -> None:
        """
        Decrypt a file using the provided key.
        
        Args:
            source_path: Path to the encrypted file
            target_path: Path where to save the decrypted file
            key: Decryption key
            
        Raises:
            FileEncryptionError: If decryption fails
        """
        try:
            with open(source_path, "rb") as src, open(target_path, "wb") as dst:
                # Read IV from the beginning of the file
                iv = src.read(16)
                
                # Create cipher
                cipher = Cipher(algorithms.AES(key[:32]), modes.CBC(iv))
                decryptor = cipher.decryptor()
                unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
                
                # Read and decrypt the file in chunks
                encrypted_data = src.read()
                decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
                
                # Remove padding
                unpadded_data = unpadder.update(decrypted_data) + unpadder.finalize()
                
                # Write the decrypted data
                dst.write(unpadded_data)
                
        except Exception as e:
            logger.error(f"Failed to decrypt file with key: {str(e)}")
            raise FileEncryptionError(f"Failed to decrypt file with key: {str(e)}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA-256 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hex digest of the file hash
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


# Create global instance
file_encryptor = FileEncryptor()


def encrypt_file(
    source_path: Union[str, Path], 
    target_path: Optional[Union[str, Path]] = None
) -> Tuple[Path, Dict]:
    """
    Encrypt a file using the global file encryptor.
    
    Args:
        source_path: Path to the file to encrypt
        target_path: Path where to save the encrypted file
        
    Returns:
        Tuple of (encrypted_file_path, metadata)
    """
    return file_encryptor.encrypt_file(source_path, target_path)


def decrypt_file(
    source_path: Union[str, Path], 
    target_path: Optional[Union[str, Path]] = None
) -> Path:
    """
    Decrypt a file using the global file encryptor.
    
    Args:
        source_path: Path to the encrypted file
        target_path: Path where to save the decrypted file
        
    Returns:
        Path to the decrypted file
    """
    return file_encryptor.decrypt_file(source_path, target_path) 