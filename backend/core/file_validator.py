"""
File validation module for checking file types and sizes.

This module provides functionality to validate:
- File MIME types
- File signatures (magic bytes)
- File sizes
"""

import os
import logging
from typing import Dict, List, Optional, Set, Tuple, Union, BinaryIO
from pathlib import Path
import magic
from fastapi import UploadFile, HTTPException, status

from core.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)
settings = get_settings()

class FileValidator:
    """
    Validates uploaded files by checking MIME types, file signatures, and enforcing size limits.
    """
    
    # Default allowed MIME types
    DEFAULT_ALLOWED_MIME_TYPES = {
        # Images
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'image/svg+xml',
        
        # Documents
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # docx
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # xlsx
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # pptx
        'text/plain',
        'text/csv',
        
        # Audio
        'audio/mpeg',
        'audio/mp4',
        'audio/ogg',
        'audio/wav',
        
        # Video
        'video/mp4',
        'video/mpeg',
        'video/webm',
        'video/quicktime',
        
        # Archives
        'application/zip',
        'application/x-rar-compressed',
        'application/gzip',
        'application/x-tar',
    }
    
    # File signatures (magic bytes) for common file types
    FILE_SIGNATURES = {
        # Images
        'jpeg': [bytes.fromhex('FFD8FF')],
        'png': [bytes.fromhex('89504E470D0A1A0A')],
        'gif': [bytes.fromhex('474946383961'), bytes.fromhex('474946383761')],
        'webp': [bytes.fromhex('52494646') + b'....WEBP'],  # RIFF....WEBP
        
        # Documents
        'pdf': [bytes.fromhex('25504446')],  # %PDF
        'docx': [bytes.fromhex('504B0304')],  # PK.. (ZIP format)
        'xlsx': [bytes.fromhex('504B0304')],  # PK.. (ZIP format)
        'pptx': [bytes.fromhex('504B0304')],  # PK.. (ZIP format)
        
        # Audio/Video
        'mp3': [bytes.fromhex('494433')],  # ID3
        'mp4': [bytes.fromhex('00000020667479704D5034')],  # ....ftypMP4
        'wav': [bytes.fromhex('52494646') + b'....WAVE'],  # RIFF....WAVE
        
        # Archives
        'zip': [bytes.fromhex('504B0304')],  # PK..
        'rar': [bytes.fromhex('526172211A0700')],  # Rar!...
        'gzip': [bytes.fromhex('1F8B')],
    }
    
    # Default maximum file size (10 MB)
    DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024
    
    def __init__(
        self,
        allowed_mime_types: Optional[Set[str]] = None,
        max_file_size: Optional[int] = None,
        enforce_signature_check: bool = True,
    ):
        """
        Initialize the file validator.
        
        Args:
            allowed_mime_types: Set of allowed MIME types
            max_file_size: Maximum file size in bytes
            enforce_signature_check: Whether to enforce file signature checks
        """
        self.allowed_mime_types = allowed_mime_types or self.DEFAULT_ALLOWED_MIME_TYPES
        self.max_file_size = max_file_size or self.DEFAULT_MAX_FILE_SIZE
        self.enforce_signature_check = enforce_signature_check
        
        # Initialize magic
        self.mime_magic = magic.Magic(mime=True)
        
    async def validate_file(self, file: UploadFile) -> Tuple[bool, Optional[str]]:
        """
        Validate an uploaded file.
        
        Args:
            file: The uploaded file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        try:
            size_validation = await self._validate_file_size(file)
            if not size_validation[0]:
                return size_validation
                
            # Check MIME type
            mime_validation = await self._validate_mime_type(file)
            if not mime_validation[0]:
                return mime_validation
                
            # Check file signature
            if self.enforce_signature_check:
                signature_validation = await self._validate_file_signature(file)
                if not signature_validation[0]:
                    return signature_validation
                    
            # Reset file position for future reads
            await file.seek(0)
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating file {file.filename}: {str(e)}")
            return False, f"Error validating file: {str(e)}"
            
    async def _validate_file_size(self, file: UploadFile) -> Tuple[bool, Optional[str]]:
        """
        Validate the file size.
        
        Args:
            file: The uploaded file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Get file size
        await file.seek(0, os.SEEK_END)
        file_size = await file.tell()
        await file.seek(0)
        
        # Check if file size exceeds the maximum
        if file_size > self.max_file_size:
            max_size_mb = self.max_file_size / (1024 * 1024)
            return False, f"File size exceeds the maximum allowed size ({max_size_mb:.1f} MB)"
            
        return True, None
        
    async def _validate_mime_type(self, file: UploadFile) -> Tuple[bool, Optional[str]]:
        """
        Validate the file MIME type.
        
        Args:
            file: The uploaded file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Read a sample of the file to determine MIME type
        sample = await file.read(2048)
        await file.seek(0)
        
        # Create a temporary file to use with magic
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(sample)
            temp_file_path = temp_file.name
            
        try:
            # Get MIME type
            mime_type = self.mime_magic.from_file(temp_file_path)
            
            # Check if MIME type is allowed
            if mime_type not in self.allowed_mime_types:
                return False, f"File type '{mime_type}' is not allowed"
                
            return True, None
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    async def _validate_file_signature(self, file: UploadFile) -> Tuple[bool, Optional[str]]:
        """
        Validate the file signature (magic bytes).
        
        Args:
            file: The uploaded file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Read the first 32 bytes for signature checking
        header = await file.read(32)
        await file.seek(0)
        
        # Get file extension
        filename = file.filename or ""
        extension = Path(filename).suffix.lower().lstrip('.')
        
        # Check if extension has a known signature
        if extension in self.FILE_SIGNATURES:
            signatures = self.FILE_SIGNATURES[extension]
            
            # Check if file header matches any of the signatures
            is_valid = any(
                header.startswith(sig) or 
                (b'....' in sig and self._check_pattern_signature(header, sig))
                for sig in signatures
            )
            
            if not is_valid:
                return False, f"File signature does not match the expected format for .{extension} files"
                
        return True, None
        
    def _check_pattern_signature(self, header: bytes, pattern: bytes) -> bool:
        """
        Check if header matches a pattern with wildcards.
        
        Args:
            header: The file header bytes
            pattern: The pattern with wildcards
            
        Returns:
            True if the header matches the pattern, False otherwise
        """
        if len(header) < len(pattern):
            return False
            
        parts = pattern.split(b'....')
        if len(parts) != 2:
            return False
            
        prefix, suffix = parts
        
        return header.startswith(prefix) and suffix in header[len(prefix):]


# Create a global file validator instance
file_validator = FileValidator() 