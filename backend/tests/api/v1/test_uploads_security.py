"""
Tests for security features in the uploads API endpoints.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile
from fastapi.testclient import TestClient
from pathlib import Path
import io

from main import app
from security.security_integrator import SecurityIntegrator


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def mock_security_integrator():
    """Mock security integrator for testing."""
    mock_integrator = MagicMock(spec=SecurityIntegrator)
    
    # Create async mock for secure_upload_processing
    mock_integrator.secure_upload_processing = AsyncMock()
    
    # Set default return values for the mock
    mock_integrator.secure_upload_processing.return_value = (
        True,  # is_safe
        None,  # security_error
        {      # security_results
            "malware_detected": False,
            "suspicious_patterns": [],
            "metadata_sanitized": True,
            "scan_id": "test-scan-123"
        }
    )
    
    return mock_integrator


@pytest.fixture
def mock_file():
    """Create a mock file for testing."""
    content = b"test file content"
    file = io.BytesIO(content)
    return UploadFile(filename="test.txt", file=file)


@pytest.fixture
def mock_get_security_integrator(mock_security_integrator):
    """Mock the get_security_integrator dependency."""
    with patch("api.v1.uploads.get_security_integrator", return_value=mock_security_integrator):
        yield mock_security_integrator


@pytest.fixture
def mock_file_validator():
    """Mock the FileValidator to always return valid."""
    with patch("api.v1.uploads.file_validator") as mock:
        mock.validate_file = AsyncMock(return_value=(True, None))
        mock.mime_magic.from_file.return_value = "text/plain"
        yield mock


@pytest.fixture
def mock_db():
    """Mock the database session."""
    with patch("api.v1.uploads.get_database") as mock:
        mock_session = MagicMock()
        mock.return_value = mock_session
        yield mock_session


@pytest.mark.asyncio
async def test_upload_file_with_security_success(
    test_client, mock_file, mock_get_security_integrator, 
    mock_file_validator, mock_db, tmp_path
):
    """Test successful file upload with security checks."""
    # Set up the mock file path
    with patch("api.v1.uploads.settings") as mock_settings:
        mock_settings.uploads_path = str(tmp_path)
        
        # Set up the mock to ensure file exists
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.stat") as mock_stat, \
             patch("builtins.open", create=True), \
             patch("os.urandom", return_value=b"12345678"):
            
            # Mock file size
            mock_stat_result = MagicMock()
            mock_stat_result.st_size = 100
            mock_stat.return_value = mock_stat_result
            
            # Make the request
            response = test_client.post(
                "/api/v1/uploads/",
                files={"file": ("test.txt", b"test content", "text/plain")},
                data={"description": "Test file"}
            )
            
            # Verify response
            assert response.status_code == 201
            assert response.json()["success"] is True
            assert "security_results" in response.json()["data"]
            assert response.json()["data"]["security_results"]["scan_status"] == "passed"
            
            # Verify security integrator was called
            mock_get_security_integrator.secure_upload_processing.assert_called_once()


@pytest.mark.asyncio
async def test_upload_file_with_security_failure(
    test_client, mock_file, mock_get_security_integrator, 
    mock_file_validator, mock_db, tmp_path
):
    """Test file upload with failed security check."""
    # Configure security integrator to fail
    mock_get_security_integrator.secure_upload_processing.return_value = (
        False,  # is_safe
        "Malware detected",  # security_error
        {      # security_results
            "malware_detected": True,
            "suspicious_patterns": ["suspicious_pattern"],
            "metadata_sanitized": False,
            "scan_id": "test-scan-123"
        }
    )
    
    # Set up the mock file path
    with patch("api.v1.uploads.settings") as mock_settings:
        mock_settings.uploads_path = str(tmp_path)
        
        # Set up the mock to ensure file exists and can be deleted
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.unlink") as mock_unlink, \
             patch("pathlib.Path.stat") as mock_stat, \
             patch("builtins.open", create=True), \
             patch("os.urandom", return_value=b"12345678"):
            
            # Mock file size
            mock_stat_result = MagicMock()
            mock_stat_result.st_size = 100
            mock_stat.return_value = mock_stat_result
            
            # Make the request
            response = test_client.post(
                "/api/v1/uploads/",
                files={"file": ("test.txt", b"test content", "text/plain")},
                data={"description": "Test file"}
            )
            
            # Verify response
            assert response.status_code == 400
            assert "Security check failed" in response.json()["detail"]
            
            # Verify the file was deleted
            mock_unlink.assert_called_once()


@pytest.mark.asyncio
async def test_upload_multiple_files_with_security(
    test_client, mock_file, mock_get_security_integrator, 
    mock_file_validator, mock_db, tmp_path
):
    """Test uploading multiple files with security checks."""
    # Set up the mock file path
    with patch("api.v1.uploads.settings") as mock_settings:
        mock_settings.uploads_path = str(tmp_path)
        
        # Set up the mock to ensure file exists
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.stat") as mock_stat, \
             patch("builtins.open", create=True), \
             patch("os.urandom", side_effect=[b"12345678", b"87654321"]):
            
            # Mock file size
            mock_stat_result = MagicMock()
            mock_stat_result.st_size = 100
            mock_stat.return_value = mock_stat_result
            
            # Make the request with two files
            response = test_client.post(
                "/api/v1/uploads/multiple",
                files=[
                    ("files", ("test1.txt", b"test content 1", "text/plain")),
                    ("files", ("test2.txt", b"test content 2", "text/plain"))
                ],
                data={"description": "Test files"}
            )
            
            # Verify response
            assert response.status_code == 201
            assert response.json()["success"] is True
            assert response.json()["data"]["uploaded_count"] == 2
            assert "security_results" in response.json()["data"]["files"][0]
            
            # Verify security integrator was called twice (once for each file)
            assert mock_get_security_integrator.secure_upload_processing.call_count == 2


@pytest.mark.asyncio
async def test_upload_multiple_files_with_mixed_security_results(
    test_client, mock_file, mock_get_security_integrator, 
    mock_file_validator, mock_db, tmp_path
):
    """Test uploading multiple files with mixed security results (one passes, one fails)."""
    # Configure security integrator to return different results for different calls
    mock_get_security_integrator.secure_upload_processing.side_effect = [
        # First file passes
        (True, None, {
            "malware_detected": False,
            "suspicious_patterns": [],
            "metadata_sanitized": True,
            "scan_id": "test-scan-123"
        }),
        # Second file fails
        (False, "Malware detected", {
            "malware_detected": True,
            "suspicious_patterns": ["suspicious_pattern"],
            "metadata_sanitized": False,
            "scan_id": "test-scan-456"
        })
    ]
    
    # Set up the mock file path
    with patch("api.v1.uploads.settings") as mock_settings:
        mock_settings.uploads_path = str(tmp_path)
        
        # Set up the mock to ensure file exists and can be deleted
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.unlink") as mock_unlink, \
             patch("pathlib.Path.stat") as mock_stat, \
             patch("builtins.open", create=True), \
             patch("os.urandom", side_effect=[b"12345678", b"87654321"]):
            
            # Mock file size
            mock_stat_result = MagicMock()
            mock_stat_result.st_size = 100
            mock_stat.return_value = mock_stat_result
            
            # Make the request with two files
            response = test_client.post(
                "/api/v1/uploads/multiple",
                files=[
                    ("files", ("test1.txt", b"test content 1", "text/plain")),
                    ("files", ("test2.txt", b"test content 2", "text/plain"))
                ],
                data={"description": "Test files"}
            )
            
            # Verify response
            assert response.status_code == 201
            assert response.json()["success"] is True
            assert response.json()["data"]["uploaded_count"] == 1
            assert response.json()["data"]["failed_count"] == 1
            assert "failed_files" in response.json()["data"]
            assert "Malware detected" in response.json()["data"]["failed_files"][0]["error"]
            
            # Verify the second file was deleted
            mock_unlink.assert_called_once() 