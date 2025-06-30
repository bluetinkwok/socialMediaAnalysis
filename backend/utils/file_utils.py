"""
File Utilities

This module provides utility functions for file operations.
"""

import os
import hashlib
import uuid
import mimetypes
from typing import Optional, Set
import magic  # python-magic for MIME type detection
from pathlib import Path

from core.config import get_settings

settings = get_settings()

def validate_file_extension(filename: str) -> bool:
    """
    Validate if the file extension is allowed.
    
    Args:
        filename: Name of the file to validate
        
    Returns:
        bool: True if the file extension is allowed, False otherwise
    """
    if not filename:
        return False
        
    allowed_extensions = settings.allowed_file_extensions
    ext = os.path.splitext(filename)[1].lower()
    
    # Remove the dot from the extension
    if ext.startswith('.'):
        ext = ext[1:]
    
    return ext in allowed_extensions

def generate_secure_filename(original_filename: str) -> str:
    """
    Generate a secure filename for storage.
    
    Args:
        original_filename: Original filename
        
    Returns:
        str: Secure filename
    """
    # Get the file extension
    _, ext = os.path.splitext(original_filename)
    
    # Generate a UUID for the filename
    secure_name = f"{uuid.uuid4().hex}{ext}"
    
    return secure_name

def get_file_hash(file_path: str) -> str:
    """
    Calculate SHA-256 hash of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        str: SHA-256 hash of the file
    """
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        # Read the file in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()

def get_mime_type(file_path: str) -> str:
    """
    Get the MIME type of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        str: MIME type of the file
    """
    try:
        # Use python-magic for more accurate MIME type detection
        mime_type = magic.from_file(file_path, mime=True)
        return mime_type
    except Exception:
        # Fallback to mimetypes module
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"

def is_mime_type_allowed(mime_type: str) -> bool:
    """
    Check if the MIME type is allowed.
    
    Args:
        mime_type: MIME type to check
        
    Returns:
        bool: True if the MIME type is allowed, False otherwise
    """
    allowed_mime_types = settings.allowed_mime_types
    return mime_type in allowed_mime_types

def validate_file_size(file_path: str, max_size_mb: Optional[int] = None) -> bool:
    """
    Validate if the file size is within limits.
    
    Args:
        file_path: Path to the file
        max_size_mb: Maximum allowed size in MB (defaults to settings value)
        
    Returns:
        bool: True if the file size is within limits, False otherwise
    """
    if max_size_mb is None:
        max_size_mb = settings.max_file_size_mb
        
    max_size_bytes = max_size_mb * 1024 * 1024
    file_size = os.path.getsize(file_path)
    
    return file_size <= max_size_bytes

def get_file_info(file_path: str) -> dict:
    """
    Get comprehensive information about a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        dict: File information
    """
    file_stat = os.stat(file_path)
    file_hash = get_file_hash(file_path)
    mime_type = get_mime_type(file_path)
    
    return {
        "filename": os.path.basename(file_path),
        "path": file_path,
        "size_bytes": file_stat.st_size,
        "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
        "created": file_stat.st_ctime,
        "modified": file_stat.st_mtime,
        "mime_type": mime_type,
        "hash": file_hash,
        "extension": os.path.splitext(file_path)[1].lower(),
    }

def create_temp_copy(file_path: str) -> str:
    """
    Create a temporary copy of a file for processing.
    
    Args:
        file_path: Path to the original file
        
    Returns:
        str: Path to the temporary copy
    """
    import shutil
    import tempfile
    
    # Create a temporary file with the same extension
    _, ext = os.path.splitext(file_path)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    temp_file.close()
    
    # Copy the file
    shutil.copy2(file_path, temp_file.name)
    
    return temp_file.name
