"""
Tests for the file validation module.
"""
import os
import io
import pytest
import tempfile
from fastapi import UploadFile
from unittest.mock import MagicMock, patch, AsyncMock

from core.file_validator import FileValidator

# Helper function to create a test file with specific content
def create_test_file(content: bytes, filename: str) -> UploadFile:
    """Create a test file with specific content."""
    file_like = io.BytesIO(content)
    
    # Create an UploadFile with AsyncMock methods
    upload_file = UploadFile(
        filename=filename,
        file=file_like,
    )
    
    # Replace methods with AsyncMock
    async def async_read(size: int = -1):
        return file_like.read(size)
        
    async def async_seek(offset: int, whence: int = 0):
        return file_like.seek(offset, whence)
        
    async def async_tell():
        return file_like.tell()
        
    upload_file.read = async_read
    upload_file.seek = async_seek
    upload_file.tell = async_tell
    
    return upload_file

# Test data
JPEG_HEADER = bytes.fromhex('FFD8FFE000104A46494600010100000100010000')
PNG_HEADER = bytes.fromhex('89504E470D0A1A0A0000000D49484452')
PDF_HEADER = bytes.fromhex('255044462D312E350D0A')
INVALID_HEADER = bytes.fromhex('00000000000000000000')

@pytest.fixture
def file_validator():
    """Create a FileValidator instance for testing."""
    return FileValidator(
        allowed_mime_types={'image/jpeg', 'image/png', 'application/pdf'},
        max_file_size=1024 * 1024,  # 1 MB
        enforce_signature_check=True,
    )

@pytest.mark.asyncio
async def test_validate_file_size_valid(file_validator):
    """Test that a file with valid size passes validation."""
    # Create a small file (100 bytes)
    file = create_test_file(b'0' * 100, "small_file.txt")
    
    # Validate file size
    is_valid, error = await file_validator._validate_file_size(file)
    
    assert is_valid is True
    assert error is None

@pytest.mark.asyncio
async def test_validate_file_size_invalid(file_validator):
    """Test that a file exceeding the size limit fails validation."""
    # Create a file larger than the limit (2 MB)
    file = create_test_file(b'0' * (2 * 1024 * 1024), "large_file.txt")
    
    # Validate file size
    is_valid, error = await file_validator._validate_file_size(file)
    
    assert is_valid is False
    assert "exceeds the maximum allowed size" in error

@pytest.mark.asyncio
async def test_validate_mime_type_valid(file_validator):
    """Test that a file with valid MIME type passes validation."""
    # Create a JPEG file
    file = create_test_file(JPEG_HEADER + b'0' * 100, "image.jpg")
    
    # Mock the magic library to return a valid MIME type
    with patch.object(file_validator.mime_magic, 'from_file', return_value='image/jpeg'):
        is_valid, error = await file_validator._validate_mime_type(file)
        
    assert is_valid is True
    assert error is None

@pytest.mark.asyncio
async def test_validate_mime_type_invalid(file_validator):
    """Test that a file with invalid MIME type fails validation."""
    # Create a file with invalid MIME type
    file = create_test_file(b'0' * 100, "document.docx")
    
    # Mock the magic library to return an invalid MIME type
    with patch.object(file_validator.mime_magic, 'from_file', return_value='application/msword'):
        is_valid, error = await file_validator._validate_mime_type(file)
        
    assert is_valid is False
    assert "not allowed" in error

@pytest.mark.asyncio
async def test_validate_file_signature_valid(file_validator):
    """Test that a file with valid signature passes validation."""
    # Create a JPEG file
    file = create_test_file(JPEG_HEADER + b'0' * 100, "image.jpg")
    
    # Validate file signature
    is_valid, error = await file_validator._validate_file_signature(file)
    
    assert is_valid is True
    assert error is None

@pytest.mark.asyncio
async def test_validate_file_signature_invalid(file_validator):
    """Test that a file with invalid signature fails validation."""
    # Create a file with invalid signature but correct extension
    file = create_test_file(INVALID_HEADER + b'0' * 100, "image.jpg")
    
    # Validate file signature
    is_valid, error = await file_validator._validate_file_signature(file)
    
    assert is_valid is False
    assert "signature does not match" in error

@pytest.mark.asyncio
async def test_validate_file_all_valid(file_validator):
    """Test that a file passing all validations is considered valid."""
    # Create a valid JPEG file
    file = create_test_file(JPEG_HEADER + b'0' * 100, "image.jpg")
    
    # Mock the magic library to return a valid MIME type
    with patch.object(file_validator.mime_magic, 'from_file', return_value='image/jpeg'):
        is_valid, error = await file_validator.validate_file(file)
        
    assert is_valid is True
    assert error is None

@pytest.mark.asyncio
async def test_validate_file_invalid_size(file_validator):
    """Test that a file failing size validation is considered invalid."""
    # Create a file larger than the limit
    file = create_test_file(b'0' * (2 * 1024 * 1024), "large_image.jpg")
    
    # Validate file
    is_valid, error = await file_validator.validate_file(file)
    
    assert is_valid is False
    assert "exceeds the maximum allowed size" in error

@pytest.mark.asyncio
async def test_validate_file_invalid_mime(file_validator):
    """Test that a file failing MIME type validation is considered invalid."""
    # Create a file with valid size but invalid MIME type
    file = create_test_file(JPEG_HEADER + b'0' * 100, "image.jpg")
    
    # Mock the magic library to return an invalid MIME type
    with patch.object(file_validator.mime_magic, 'from_file', return_value='application/octet-stream'):
        is_valid, error = await file_validator.validate_file(file)
        
    assert is_valid is False
    assert "not allowed" in error

@pytest.mark.asyncio
async def test_validate_file_invalid_signature(file_validator):
    """Test that a file failing signature validation is considered invalid."""
    # Create a file with valid size and MIME type but invalid signature
    file = create_test_file(INVALID_HEADER + b'0' * 100, "image.jpg")
    
    # Mock the magic library to return a valid MIME type
    with patch.object(file_validator.mime_magic, 'from_file', return_value='image/jpeg'):
        is_valid, error = await file_validator.validate_file(file)
        
    assert is_valid is False
    assert "signature does not match" in error

@pytest.mark.asyncio
async def test_validate_file_without_signature_check(file_validator):
    """Test that a file with invalid signature passes if signature check is disabled."""
    # Disable signature check
    file_validator.enforce_signature_check = False
    
    # Create a file with valid size and MIME type but invalid signature
    file = create_test_file(INVALID_HEADER + b'0' * 100, "image.jpg")
    
    # Mock the magic library to return a valid MIME type
    with patch.object(file_validator.mime_magic, 'from_file', return_value='image/jpeg'):
        is_valid, error = await file_validator.validate_file(file)
        
    assert is_valid is True
    assert error is None

@pytest.mark.asyncio
async def test_pattern_signature_matching():
    """Test the pattern signature matching functionality."""
    validator = FileValidator()
    
    # Test RIFF....WAVE pattern (WAV file)
    header = bytes.fromhex('52494646') + b'1234WAVE' + b'0' * 20
    pattern = bytes.fromhex('52494646') + b'....WAVE'
    
    assert validator._check_pattern_signature(header, pattern) is True
    
    # Test with non-matching pattern
    header = bytes.fromhex('52494646') + b'1234FILE' + b'0' * 20
    pattern = bytes.fromhex('52494646') + b'....WAVE'
    
    assert validator._check_pattern_signature(header, pattern) is False 