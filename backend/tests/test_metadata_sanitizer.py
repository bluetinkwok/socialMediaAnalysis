"""
Tests for the metadata sanitizer module.
"""
import os
import io
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from fastapi import UploadFile

from core.metadata_sanitizer import MetadataSanitizer

@pytest.fixture
def metadata_sanitizer():
    """Create a MetadataSanitizer instance for testing."""
    return MetadataSanitizer()

@pytest.fixture
def mock_pil():
    """Mock the PIL library."""
    with patch('core.metadata_sanitizer.HAS_PIL', True), \
         patch('core.metadata_sanitizer.Image') as mock_image, \
         patch('core.metadata_sanitizer.TAGS', {1: 'Make', 2: 'Model', 36867: 'DateTimeOriginal'}):
        
        # Mock image instance
        mock_img = MagicMock()
        mock_img.mode = 'RGB'
        mock_img.size = (100, 100)
        mock_img.format = 'JPEG'
        
        # Mock getdata method
        mock_img.getdata.return_value = [(0, 0, 0)] * 10000  # 100x100 black pixels
        
        # Mock _getexif method
        mock_img._getexif.return_value = {
            1: 'Canon',
            2: 'EOS 5D',
            36867: '2023:01:01 12:00:00'
        }
        
        # Configure open method to return the mock image
        mock_image.open.return_value.__enter__.return_value = mock_img
        
        # Mock Image.new
        mock_image.new.return_value = mock_img
        
        yield mock_image

@pytest.fixture
def test_upload_file():
    """Create a test upload file."""
    file_content = b"test image content"
    file = io.BytesIO(file_content)
    
    # Create an UploadFile with async methods
    upload_file = UploadFile(
        filename="test.jpg",
        file=file,
    )
    
    # Replace methods with async versions
    async def async_read():
        return file.getvalue()
        
    async def async_seek(position):
        file.seek(position)
        
    upload_file.read = async_read
    upload_file.seek = async_seek
    
    return upload_file

@pytest.mark.asyncio
async def test_sanitizer_initialization():
    """Test sanitizer initialization."""
    # Test with PIL available
    with patch('core.metadata_sanitizer.HAS_PIL', True):
        sanitizer = MetadataSanitizer()
        # No warning should be logged
    
    # Test with PIL not available
    with patch('core.metadata_sanitizer.HAS_PIL', False), \
         patch('core.metadata_sanitizer.logger.warning') as mock_warning:
        sanitizer = MetadataSanitizer()
        mock_warning.assert_called_once()
        assert "Pillow library not installed" in mock_warning.call_args[0][0]

@pytest.mark.asyncio
async def test_sanitize_image_success(metadata_sanitizer, mock_pil, tmp_path):
    """Test successful image metadata sanitization."""
    # Create a test image file
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b"test image content")
    
    # Mock tempfile and shutil
    with patch('tempfile.NamedTemporaryFile') as mock_temp_file, \
         patch('shutil.move') as mock_move:
        
        # Configure the mock temporary file
        mock_temp = MagicMock()
        mock_temp.name = str(tmp_path / "temp.jpg")
        mock_temp_file.return_value.__enter__.return_value = mock_temp
        
        # Sanitize the image
        success, message = await metadata_sanitizer.sanitize_image(test_file)
        
        # Verify the result
        assert success is True
        assert "successfully" in message
        mock_pil.open.assert_called_once_with(test_file)
        mock_pil.new.assert_called_once()
        mock_move.assert_called_once()

@pytest.mark.asyncio
async def test_sanitize_image_no_pil(metadata_sanitizer):
    """Test image sanitization when PIL is not available."""
    with patch('core.metadata_sanitizer.HAS_PIL', False):
        success, message = await metadata_sanitizer.sanitize_image("test.jpg")
        assert success is False
        assert "Pillow library not installed" in message

@pytest.mark.asyncio
async def test_sanitize_image_error(metadata_sanitizer, mock_pil, tmp_path):
    """Test image sanitization with an error."""
    # Create a test image file
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b"test image content")
    
    # Mock PIL to raise an exception
    mock_pil.open.side_effect = Exception("Test error")
    
    # Sanitize the image
    success, message = await metadata_sanitizer.sanitize_image(test_file)
    
    # Verify the result
    assert success is False
    assert "Failed to sanitize" in message
    assert "Test error" in message

@pytest.mark.asyncio
async def test_get_image_metadata_success(metadata_sanitizer, mock_pil, tmp_path):
    """Test successful image metadata extraction."""
    # Create a test image file
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b"test image content")
    
    # Extract metadata
    metadata = await metadata_sanitizer.get_image_metadata(test_file)
    
    # Verify the result
    assert isinstance(metadata, dict)
    assert metadata["Make"] == "Canon"
    assert metadata["Model"] == "EOS 5D"
    assert metadata["DateTimeOriginal"] == "2023:01:01 12:00:00"
    assert metadata["format"] == "JPEG"
    assert metadata["mode"] == "RGB"
    assert metadata["size"] == (100, 100)

@pytest.mark.asyncio
async def test_get_image_metadata_no_pil(metadata_sanitizer):
    """Test image metadata extraction when PIL is not available."""
    with patch('core.metadata_sanitizer.HAS_PIL', False):
        metadata = await metadata_sanitizer.get_image_metadata("test.jpg")
        assert "error" in metadata
        assert "Pillow library not installed" in metadata["error"]

@pytest.mark.asyncio
async def test_get_image_metadata_error(metadata_sanitizer, mock_pil, tmp_path):
    """Test image metadata extraction with an error."""
    # Create a test image file
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b"test image content")
    
    # Mock PIL to raise an exception
    mock_pil.open.side_effect = Exception("Test error")
    
    # Extract metadata
    metadata = await metadata_sanitizer.get_image_metadata(test_file)
    
    # Verify the result
    assert "error" in metadata
    assert "Failed to extract" in metadata["error"]
    assert "Test error" in metadata["error"]

@pytest.mark.asyncio
async def test_sanitize_pdf(metadata_sanitizer):
    """Test PDF metadata sanitization."""
    # This is currently just a placeholder
    success, message = await metadata_sanitizer.sanitize_pdf("test.pdf")
    assert success is False
    assert "not implemented yet" in message

@pytest.mark.asyncio
async def test_sanitize_office_document(metadata_sanitizer):
    """Test Office document metadata sanitization."""
    # This is currently just a placeholder
    success, message = await metadata_sanitizer.sanitize_office_document("test.docx")
    assert success is False
    assert "not implemented yet" in message

@pytest.mark.asyncio
async def test_sanitize_upload_file_image(metadata_sanitizer, test_upload_file, tmp_path):
    """Test sanitizing an uploaded image file."""
    # Mock the file operations
    with patch('os.makedirs') as mock_makedirs, \
         patch('builtins.open', mock_open()) as mock_file, \
         patch.object(metadata_sanitizer, 'sanitize_image', return_value=(True, "Image sanitized")):
        
        # Sanitize the uploaded file
        success, message, file_path = await metadata_sanitizer.sanitize_upload_file(
            test_upload_file, str(tmp_path)
        )
        
        # Verify the result
        assert success is True
        assert message == "Image sanitized"
        assert file_path == os.path.join(str(tmp_path), "test.jpg")
        mock_makedirs.assert_called_once_with(str(tmp_path), exist_ok=True)
        mock_file.assert_called_once()
        metadata_sanitizer.sanitize_image.assert_called_once()

@pytest.mark.asyncio
async def test_sanitize_upload_file_pdf(metadata_sanitizer, tmp_path):
    """Test sanitizing an uploaded PDF file."""
    # Create a PDF upload file
    file_content = b"test PDF content"
    file = io.BytesIO(file_content)
    upload_file = UploadFile(filename="test.pdf", file=file)
    
    # Replace methods with async versions
    async def async_read():
        return file.getvalue()
        
    async def async_seek(position):
        file.seek(position)
        
    upload_file.read = async_read
    upload_file.seek = async_seek
    
    # Mock the file operations
    with patch('os.makedirs') as mock_makedirs, \
         patch('builtins.open', mock_open()) as mock_file, \
         patch.object(metadata_sanitizer, 'sanitize_pdf', return_value=(False, "PDF sanitization not implemented")):
        
        # Sanitize the uploaded file
        success, message, file_path = await metadata_sanitizer.sanitize_upload_file(
            upload_file, str(tmp_path)
        )
        
        # Verify the result
        assert success is False
        assert message == "PDF sanitization not implemented"
        assert file_path == os.path.join(str(tmp_path), "test.pdf")
        mock_makedirs.assert_called_once_with(str(tmp_path), exist_ok=True)
        mock_file.assert_called_once()
        metadata_sanitizer.sanitize_pdf.assert_called_once()

@pytest.mark.asyncio
async def test_sanitize_upload_file_unsupported(metadata_sanitizer, tmp_path):
    """Test sanitizing an unsupported file type."""
    # Create an unsupported upload file
    file_content = b"test text content"
    file = io.BytesIO(file_content)
    upload_file = UploadFile(filename="test.txt", file=file)
    
    # Replace methods with async versions
    async def async_read():
        return file.getvalue()
        
    async def async_seek(position):
        file.seek(position)
        
    upload_file.read = async_read
    upload_file.seek = async_seek
    
    # Mock the file operations
    with patch('os.makedirs') as mock_makedirs, \
         patch('builtins.open', mock_open()) as mock_file:
        
        # Sanitize the uploaded file
        success, message, file_path = await metadata_sanitizer.sanitize_upload_file(
            upload_file, str(tmp_path)
        )
        
        # Verify the result
        assert success is False
        assert "Unsupported file type" in message
        assert file_path == os.path.join(str(tmp_path), "test.txt")
        mock_makedirs.assert_called_once_with(str(tmp_path), exist_ok=True)
        mock_file.assert_called_once()

@pytest.mark.asyncio
async def test_sanitize_upload_file_error(metadata_sanitizer, test_upload_file):
    """Test sanitizing an uploaded file with an error."""
    # Mock os.makedirs to raise an exception
    with patch('os.makedirs', side_effect=Exception("Test error")):
        # Sanitize the uploaded file
        success, message, file_path = await metadata_sanitizer.sanitize_upload_file(
            test_upload_file, "/nonexistent/dir"
        )
        
        # Verify the result
        assert success is False
        assert "Failed to sanitize uploaded file" in message
        assert "Test error" in message
        assert file_path == "" 