"""
Unit tests for security headers middleware.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.security_headers import SecurityHeadersMiddleware, add_security_middleware


def test_security_headers_middleware():
    """Test that security headers are added to responses."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    
    @app.get("/test")
    def test_endpoint():
        return {"message": "test"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    # Check that security headers are present
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers["Permissions-Policy"]


def test_add_security_middleware(monkeypatch):
    """Test that add_security_middleware adds all middleware in production mode."""
    # Mock settings to simulate production mode
    class MockSettings:
        debug = False
        trusted_hosts = "example.com,test.com"
    
    monkeypatch.setattr("core.security_headers.settings", MockSettings())
    
    app = FastAPI()
    add_security_middleware(app)
    
    # Check that middleware were added (indirectly by checking app.middleware)
    middleware_stack = app.middleware_stack
    assert middleware_stack is not None
    
    # In production mode, we should have SecurityHeadersMiddleware, 
    # HTTPSRedirectMiddleware, and TrustedHostMiddleware
    middleware_types = [type(m).__name__ for m in app.user_middleware]
    assert "SecurityHeadersMiddleware" in str(middleware_types)
    assert "HTTPSRedirectMiddleware" in str(middleware_types)
    assert "TrustedHostMiddleware" in str(middleware_types)


def test_add_security_middleware_debug_mode(monkeypatch):
    """Test that add_security_middleware only adds SecurityHeadersMiddleware in debug mode."""
    # Mock settings to simulate debug mode
    class MockSettings:
        debug = True
        trusted_hosts = "localhost,127.0.0.1"
    
    monkeypatch.setattr("core.security_headers.settings", MockSettings())
    
    app = FastAPI()
    add_security_middleware(app)
    
    # Check that only SecurityHeadersMiddleware was added
    middleware_types = [type(m).__name__ for m in app.user_middleware]
    assert "SecurityHeadersMiddleware" in str(middleware_types)
    assert "HTTPSRedirectMiddleware" not in str(middleware_types)
    assert "TrustedHostMiddleware" not in str(middleware_types)
