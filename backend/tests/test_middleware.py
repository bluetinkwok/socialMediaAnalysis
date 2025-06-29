"""
Tests for the FastAPI middleware.
"""
import json
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from core.middleware import SanitizationMiddleware

# Create a test FastAPI app
app = FastAPI()

# Add the sanitization middleware
app.add_middleware(SanitizationMiddleware)

# Test endpoints
@app.get("/test-query")
async def test_query(param: str = ""):
    """Test endpoint for query parameter sanitization."""
    return {"sanitized_param": param}

@app.get("/test-path/{path_param}")
async def test_path(path_param: str):
    """Test endpoint for path parameter sanitization."""
    return {"sanitized_path_param": path_param}

@app.post("/test-body")
async def test_body(request: Request):
    """Test endpoint for request body sanitization."""
    body = await request.json()
    return {"sanitized_body": body}

# Create a test client
client = TestClient(app)

def test_query_parameter_sanitization():
    """Test that query parameters are properly sanitized."""
    # Test with XSS payload
    response = client.get("/test-query?param=<script>alert('XSS')</script>")
    assert response.status_code == 200
    assert response.json()["sanitized_param"] == "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;"
    
    # Test with normal parameter
    response = client.get("/test-query?param=hello")
    assert response.status_code == 200
    assert response.json()["sanitized_param"] == "hello"

def test_path_parameter_sanitization():
    """Test that path parameters are properly sanitized."""
    # Test with XSS payload
    response = client.get("/test-path/<script>alert('XSS')</script>")
    assert response.status_code == 200
    assert response.json()["sanitized_path_param"] == "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;"
    
    # Test with normal parameter
    response = client.get("/test-path/hello")
    assert response.status_code == 200
    assert response.json()["sanitized_path_param"] == "hello"

def test_body_sanitization():
    """Test that request body is properly sanitized."""
    # Test with XSS payload in JSON body
    payload = {
        "name": "<script>alert('XSS')</script>",
        "nested": {
            "field": "<img src=x onerror=alert('XSS')>"
        },
        "list": ["normal", "<script>alert('XSS')</script>"]
    }
    
    response = client.post("/test-body", json=payload)
    assert response.status_code == 200
    
    sanitized_body = response.json()["sanitized_body"]
    assert sanitized_body["name"] == "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;"
    assert sanitized_body["nested"]["field"] == "&lt;img src=x onerror=alert(&#x27;XSS&#x27;)&gt;"
    assert sanitized_body["list"][0] == "normal"
    assert sanitized_body["list"][1] == "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;"
    
    # Test with normal JSON body
    payload = {"name": "John Doe", "age": 30}
    response = client.post("/test-body", json=payload)
    assert response.status_code == 200
    assert response.json()["sanitized_body"]["name"] == "John Doe"
    assert response.json()["sanitized_body"]["age"] == 30 