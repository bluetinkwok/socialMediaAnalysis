"""
Tests for the file uploads API endpoints.
"""
import io
import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from api.v1.uploads import router as uploads_router
from core.file_validator import FileValidator
from db.models import MediaFile

# Create a test FastAPI app
app = FastAPI()
app.include_router(uploads_router)

# Create a test client
client = TestClient(app)

@pytest.fixture
def mock_file_validator():
    """Mock the file validator to always return valid."""
    with patch('api.v1.uploads.file_validator') as mock_validator:
        # Configure the mock to return valid for any file
        mock_validator.validate_file.return_value = (True, None)
        mock_validator.mime_magic.from_file.return_value = "image/jpeg"
        yield mock_validator

@pytest.fixture
def mock_db_session():
    """Mock the database session."""
    mock_session = MagicMock()
    
    # Configure the mock to return a MediaFile with an ID
    mock_media_file = MagicMock()
    mock_media_file.id = 1
    mock_media_file.filename = "test.jpg"
    mock_media_file.file_size = 1024
    mock_media_file.mime_type = "image/jpeg"
    
    # Configure the mock session
    mock_session.add.return_value = None
    mock_session.commit.return_value = None
    mock_session.refresh.side_effect = lambda x: setattr(x, 'id', 1)
    
    with patch('api.v1.uploads.get_database', return_value=mock_session):
        yield mock_session

@pytest.fixture
def test_file():
    """Create a test file for upload."""
    return {
        "file": ("test.jpg", io.BytesIO(b"test file content"), "image/jpeg")
    }

@pytest.fixture
def test_files():
    """Create multiple test files for upload."""
    return [
        ("files", ("test1.jpg", io.BytesIO(b"test file 1 content"), "image/jpeg")),
        ("files", ("test2.png", io.BytesIO(b"test file 2 content"), "image/png"))
    ]

@pytest.mark.asyncio
async def test_upload_file_success(mock_file_validator, mock_db_session, test_file):
    """Test successful file upload."""
    # Mock the file path operations
    with patch('os.urandom', return_value=b'12345678'), \
         patch('pathlib.Path.mkdir'), \
         patch('builtins.open', create=True), \
         patch('pathlib.Path.stat') as mock_stat:
        
        # Configure mock_stat to return a file size
        mock_stat_result = MagicMock()
        mock_stat_result.st_size = 1024
        mock_stat.return_value = mock_stat_result
        
        # Make the request
        response = client.post(
            "/",
            files=test_file,
            data={"description": "Test file", "category": "test"}
        )
        
        # Check response
        assert response.status_code == 201
        assert response.json()["success"] is True
        assert "File uploaded successfully" in response.json()["message"]
        assert response.json()["data"]["id"] == 1
        assert response.json()["data"]["filename"] == "test.jpg"
        
        # Verify validator was called
        mock_file_validator.validate_file.assert_called_once()
        
        # Verify DB operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

@pytest.mark.asyncio
async def test_upload_file_invalid(mock_db_session, test_file):
    """Test file upload with invalid file."""
    # Mock the validator to reject the file
    with patch('api.v1.uploads.file_validator') as mock_validator:
        mock_validator.validate_file.return_value = (False, "Invalid file type")
        
        # Make the request
        response = client.post(
            "/",
            files=test_file,
            data={"description": "Test file", "category": "test"}
        )
        
        # Check response
        assert response.status_code == 400
        assert "Invalid file: Invalid file type" in response.json()["detail"]
        
        # Verify DB operations were not called
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()

@pytest.mark.asyncio
async def test_upload_multiple_files_success(mock_file_validator, mock_db_session, test_files):
    """Test successful multiple file upload."""
    # Mock the file path operations
    with patch('os.urandom', return_value=b'12345678'), \
         patch('pathlib.Path.mkdir'), \
         patch('builtins.open', create=True), \
         patch('pathlib.Path.stat') as mock_stat:
        
        # Configure mock_stat to return a file size
        mock_stat_result = MagicMock()
        mock_stat_result.st_size = 1024
        mock_stat.return_value = mock_stat_result
        
        # Make the request
        response = client.post(
            "/multiple",
            files=test_files,
            data={"description": "Test files", "category": "test"}
        )
        
        # Check response
        assert response.status_code == 201
        assert response.json()["success"] is True
        assert "Successfully uploaded 2 files" in response.json()["message"]
        assert response.json()["data"]["uploaded_count"] == 2
        assert len(response.json()["data"]["files"]) == 2
        
        # Verify validator was called twice (once for each file)
        assert mock_file_validator.validate_file.call_count == 2
        
        # Verify DB operations
        assert mock_db_session.add.call_count == 2
        mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_upload_multiple_files_some_invalid(mock_db_session, test_files):
    """Test multiple file upload with some invalid files."""
    # Mock the validator to reject one file but accept the other
    with patch('api.v1.uploads.file_validator') as mock_validator, \
         patch('os.urandom', return_value=b'12345678'), \
         patch('pathlib.Path.mkdir'), \
         patch('builtins.open', create=True), \
         patch('pathlib.Path.stat') as mock_stat:
        
        # Configure mock validator to accept first file but reject second
        mock_validator.validate_file.side_effect = [
            (True, None),
            (False, "Invalid file type")
        ]
        mock_validator.mime_magic.from_file.return_value = "image/jpeg"
        
        # Configure mock_stat to return a file size
        mock_stat_result = MagicMock()
        mock_stat_result.st_size = 1024
        mock_stat.return_value = mock_stat_result
        
        # Make the request
        response = client.post(
            "/multiple",
            files=test_files,
            data={"description": "Test files", "category": "test"}
        )
        
        # Check response
        assert response.status_code == 201
        assert response.json()["success"] is True
        assert "Successfully uploaded 1 files" in response.json()["message"]
        assert response.json()["data"]["uploaded_count"] == 1
        assert len(response.json()["data"]["files"]) == 1
        
        # Verify validator was called twice
        assert mock_validator.validate_file.call_count == 2
        
        # Verify DB operations
        assert mock_db_session.add.call_count == 1
        mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_upload_multiple_files_all_invalid(mock_db_session, test_files):
    """Test multiple file upload with all invalid files."""
    # Mock the validator to reject all files
    with patch('api.v1.uploads.file_validator') as mock_validator:
        mock_validator.validate_file.return_value = (False, "Invalid file type")
        
        # Make the request
        response = client.post(
            "/multiple",
            files=test_files,
            data={"description": "Test files", "category": "test"}
        )
        
        # Check response
        assert response.status_code == 200  # Still returns 200 but with success=False
        assert response.json()["success"] is False
        assert "No valid files were uploaded" in response.json()["message"]
        assert response.json()["data"]["uploaded_count"] == 0
        
        # Verify validator was called twice
        assert mock_validator.validate_file.call_count == 2
        
        # Verify DB operations
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_called_once()  # Still commits the transaction

@pytest.mark.asyncio
async def test_upload_multiple_files_no_files(mock_db_session):
    """Test multiple file upload with no files provided."""
    # Make the request with no files
    response = client.post(
        "/multiple",
        data={"description": "Test files", "category": "test"}
    )
    
    # Check response
    assert response.status_code == 400
    assert "No files provided" in response.json()["detail"]
    
    # Verify DB operations were not called
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_not_called() 