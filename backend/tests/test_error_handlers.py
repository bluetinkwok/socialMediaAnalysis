"""
Unit tests for secure error handling.
"""

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from core.error_handlers import (
    add_error_handlers,
    APIError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ServerError
)


@pytest.fixture
def app_with_error_handlers():
    """Create a FastAPI app with error handlers for testing."""
    app = FastAPI()
    add_error_handlers(app)
    
    # Add test endpoints that raise different errors
    @app.get("/api_error")
    async def api_error_endpoint():
        raise APIError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Test API error",
            internal_code="TEST_ERROR",
            details={"test": "details"}
        )
    
    @app.get("/bad_request")
    async def bad_request_endpoint():
        raise BadRequestError(message="Test bad request", details={"field": "invalid"})
    
    @app.get("/unauthorized")
    async def unauthorized_endpoint():
        raise UnauthorizedError(message="Test unauthorized", details={"reason": "token_expired"})
    
    @app.get("/forbidden")
    async def forbidden_endpoint():
        raise ForbiddenError(message="Test forbidden", details={"required_role": "admin"})
    
    @app.get("/not_found")
    async def not_found_endpoint():
        raise NotFoundError(message="Test not found", details={"id": "123"})
    
    @app.get("/http_exception")
    async def http_exception_endpoint():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Test HTTP exception")
    
    @app.get("/server_error")
    async def server_error_endpoint():
        raise ServerError(message="Test server error", details={"critical": True})
    
    @app.get("/generic_exception")
    async def generic_exception_endpoint():
        # Raise a standard Python exception
        raise ValueError("Test generic exception")
    
    @app.get("/validation_error")
    async def validation_error_endpoint(q: int):
        # This will cause a validation error if q is not an integer
        return {"q": q}
    
    return app


@pytest.fixture
def client(app_with_error_handlers):
    """Create a test client for the app."""
    return TestClient(app_with_error_handlers)


def test_api_error_handler(client, monkeypatch):
    """Test the API error handler."""
    # Set debug mode to True to test details inclusion
    monkeypatch.setenv("DEBUG", "True")
    
    response = client.get("/api_error")
    assert response.status_code == 500
    data = response.json()
    assert data["error"]["code"] == "TEST_ERROR"
    assert data["error"]["message"] == "Test API error"
    assert "details" in data["error"]
    
    # Set debug mode to False to test details exclusion
    monkeypatch.setenv("DEBUG", "False")
    response = client.get("/api_error")
    data = response.json()
    assert "details" not in data["error"]


def test_bad_request_error(client):
    """Test the bad request error handler."""
    response = client.get("/bad_request")
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "ERR_BAD_REQUEST"
    assert data["error"]["message"] == "Test bad request"


def test_unauthorized_error(client):
    """Test the unauthorized error handler."""
    response = client.get("/unauthorized")
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "ERR_UNAUTHORIZED"
    assert data["error"]["message"] == "Test unauthorized"


def test_forbidden_error(client):
    """Test the forbidden error handler."""
    response = client.get("/forbidden")
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "ERR_FORBIDDEN"
    assert data["error"]["message"] == "Test forbidden"


def test_not_found_error(client):
    """Test the not found error handler."""
    response = client.get("/not_found")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "ERR_NOT_FOUND"
    assert data["error"]["message"] == "Test not found"


def test_http_exception_handler(client):
    """Test the HTTP exception handler."""
    response = client.get("/http_exception")
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "ERR_400"
    assert data["error"]["message"] == "Test HTTP exception"


def test_server_error(client):
    """Test the server error handler."""
    response = client.get("/server_error")
    assert response.status_code == 500
    data = response.json()
    assert data["error"]["code"] == "ERR_SERVER"
    assert data["error"]["message"] == "Test server error"


def test_generic_exception_handler(client, monkeypatch):
    """Test the generic exception handler."""
    # Set debug mode to True to test details inclusion
    monkeypatch.setenv("DEBUG", "True")
    
    response = client.get("/generic_exception")
    assert response.status_code == 500
    data = response.json()
    assert data["error"]["code"] == "ERR_SERVER"
    assert data["error"]["message"] == "An unexpected error occurred"
    assert "error_id" in data["error"]
    assert "details" in data["error"]
    assert data["error"]["details"]["type"] == "ValueError"
    
    # Set debug mode to False to test details exclusion
    monkeypatch.setenv("DEBUG", "False")
    response = client.get("/generic_exception")
    data = response.json()
    assert "details" not in data["error"]


def test_validation_error_handler(client, monkeypatch):
    """Test the validation error handler."""
    # Set debug mode to True to test details inclusion
    monkeypatch.setenv("DEBUG", "True")
    
    response = client.get("/validation_error?q=not_an_integer")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "ERR_VALIDATION"
    assert data["error"]["message"] == "Validation error"
    assert "details" in data["error"]
    
    # Set debug mode to False to test details exclusion
    monkeypatch.setenv("DEBUG", "False")
    response = client.get("/validation_error?q=not_an_integer")
    data = response.json()
    assert "details" not in data["error"]
