"""
Tests for the upload API
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import app
from security.security_integrator import SecurityIntegrator

client = TestClient(app)

# Mock JWT token for authentication
MOCK_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiaXNfYWRtaW4iOmZhbHNlLCJleHAiOjk5OTk5OTk5OTl9.mock_signature"

@pytest.fixture
def mock_security_integrator():
    """Mock the security integrator for testing"""
    with patch("security.security_integrator.get_security_integrator") as mock:
        integrator = MagicMock(spec=SecurityIntegrator)
        integrator.process_file.return_value = (True, {"status": "OK"})
        mock.return_value = integrator
        yield integrator

def test_upload_file_success(mock_security_integrator):
    """Test successful file upload"""
    # Create a test file
    test_file_path = "test_upload.txt"
    with open(test_file_path, "w") as f:
        f.write("Test file content")
    
    try:
        # Mock successful security check
        mock_security_integrator.process_file.return_value = (True, {"status": "OK"})
        
        # Send upload request
        with open(test_file_path, "rb") as f:
            response = client.post(
                "/api/v1/upload/",
                files={"file": ("test_file.txt", f, "text/plain")},
                data={"description": "Test file", "tags": "test,upload"},
                headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
            )
        
        # Check response
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["original_filename"] == "test_file.txt"
        assert response.json()["security_passed"] == True
        
    finally:
        # Clean up
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

def test_upload_file_security_fail(mock_security_integrator):
    """Test file upload with security failure"""
    # Create a test file
    test_file_path = "test_malicious.txt"
    with open(test_file_path, "w") as f:
        f.write("Malicious content")
    
    try:
        # Mock security failure
        mock_security_integrator.process_file.return_value = (
            False, 
            {
                "status": "INFECTED", 
                "details": "Malware detected"
            }
        )
        
        # Send upload request
        with open(test_file_path, "rb") as f:
            response = client.post(
                "/api/v1/upload/",
                files={"file": ("test_malicious.txt", f, "text/plain")},
                data={"description": "Malicious file", "tags": "test,malicious"},
                headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
            )
        
        # Check response
        assert response.status_code == 400
        assert response.json()["status"] == "rejected"
        assert "security_results" in response.json()
        
    finally:
        # Clean up
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

def test_upload_invalid_extension():
    """Test upload with invalid file extension"""
    # Create a test file
    test_file_path = "test_invalid.xyz"
    with open(test_file_path, "w") as f:
        f.write("Invalid extension")
    
    try:
        # Send upload request
        with open(test_file_path, "rb") as f:
            response = client.post(
                "/api/v1/upload/",
                files={"file": ("test_invalid.xyz", f, "text/plain")},
                data={"description": "Invalid file", "tags": "test,invalid"},
                headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
            )
        
        # Check response
        assert response.status_code == 400
        assert "File type not allowed" in response.json()["detail"]
        
    finally:
        # Clean up
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

def test_security_events_admin():
    """Test security events endpoint with admin user"""
    # Mock admin token
    admin_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiaXNfYWRtaW4iOnRydWUsImV4cCI6OTk5OTk5OTk5OX0.mock_admin_signature"
    
    # Mock security events
    with patch("security.security_integrator.get_security_integrator") as mock:
        integrator = MagicMock(spec=SecurityIntegrator)
        integrator.get_security_events.return_value = [
            {"event_type": "security_pass", "timestamp": "2023-01-01T00:00:00"}
        ]
        mock.return_value = integrator
        
        # Send request
        response = client.get(
            "/api/v1/upload/security-events",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Check response
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["event_type"] == "security_pass"

def test_security_events_non_admin():
    """Test security events endpoint with non-admin user"""
    # Send request with non-admin token
    response = client.get(
        "/api/v1/upload/security-events",
        headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
    )
    
    # Check response
    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]
