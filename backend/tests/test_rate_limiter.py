"""
Tests for the rate limiting middleware.
"""
import time
import unittest
from unittest.mock import MagicMock, patch
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from core.rate_limiter import RateLimiter, RateLimitingMiddleware

class TestRateLimiter(unittest.TestCase):
    """Test cases for RateLimiter class."""
    
    def test_is_allowed_first_request(self):
        """Test that the first request is allowed."""
        limiter = RateLimiter(rate_limit=5, time_window=60)
        is_allowed, remaining, retry_after = limiter.is_allowed("test_client")
        
        self.assertTrue(is_allowed)
        self.assertEqual(remaining, 4)
        self.assertEqual(retry_after, 0)
        
    def test_is_allowed_within_limit(self):
        """Test that requests within the rate limit are allowed."""
        limiter = RateLimiter(rate_limit=5, time_window=60)
        
        # Make 5 requests (first request consumes 1 token, 4 remaining)
        for i in range(5):
            is_allowed, remaining, retry_after = limiter.is_allowed("test_client")
            self.assertTrue(is_allowed)
            self.assertEqual(remaining, 4 - i)
            self.assertEqual(retry_after, 0)
            
    def test_is_allowed_exceeds_limit(self):
        """Test that requests exceeding the rate limit are rejected."""
        limiter = RateLimiter(rate_limit=5, time_window=60)
        
        # Make 5 requests (consuming all tokens)
        for _ in range(5):
            limiter.is_allowed("test_client")
            
        # The 6th request should be rejected
        is_allowed, remaining, retry_after = limiter.is_allowed("test_client")
        self.assertFalse(is_allowed)
        self.assertEqual(remaining, 0)
        self.assertGreater(retry_after, 0)
        
    def test_token_refill(self):
        """Test that tokens are refilled over time."""
        limiter = RateLimiter(rate_limit=5, time_window=60)
        
        # Make 3 requests (consuming 3 tokens)
        for _ in range(3):
            limiter.is_allowed("test_client")
            
        # Wait for tokens to refill (1 token per 12 seconds)
        with patch('time.time') as mock_time:
            # Set initial time
            mock_time.return_value = 100
            
            # Make a request to get current tokens (2 remaining)
            is_allowed, remaining, _ = limiter.is_allowed("test_client")
            self.assertTrue(is_allowed)
            self.assertEqual(remaining, 1)  # 2 - 1 = 1 remaining
            
            # Advance time by 24 seconds (should refill 2 tokens)
            mock_time.return_value = 124
            
            # Make another request
            is_allowed, remaining, _ = limiter.is_allowed("test_client")
            self.assertTrue(is_allowed)
            self.assertEqual(remaining, 2)  # 1 + 2 - 1 = 2 remaining
            
    def test_cleanup(self):
        """Test that old entries are cleaned up."""
        limiter = RateLimiter(rate_limit=5, time_window=60)
        
        # Add some entries
        limiter.is_allowed("client1")
        limiter.is_allowed("client2")
        limiter.is_allowed("client3")
        
        self.assertEqual(len(limiter.tokens), 3)
        
        # Make client1 old
        limiter.tokens["client1"] = (4, time.time() - 3601)  # 1 hour and 1 second ago
        
        # Run cleanup
        limiter.cleanup(max_age=3600)  # 1 hour
        
        # client1 should be removed
        self.assertEqual(len(limiter.tokens), 2)
        self.assertNotIn("client1", limiter.tokens)
        self.assertIn("client2", limiter.tokens)
        self.assertIn("client3", limiter.tokens)


# Create a test FastAPI app
app = FastAPI()

# Add test endpoints
@app.get("/test")
async def test_endpoint():
    """Test endpoint."""
    return {"message": "Test endpoint"}

@app.get("/api/v1/auth/login")
async def login_endpoint():
    """Login endpoint with stricter rate limiting."""
    return {"message": "Login endpoint"}


class TestRateLimitingMiddleware:
    """Test cases for RateLimitingMiddleware class."""
    
    @pytest.fixture
    def client(self):
        """Create a test client with rate limiting middleware."""
        app_with_middleware = FastAPI()
        app_with_middleware.add_middleware(
            RateLimitingMiddleware,
            default_rate_limit=5,
            default_time_window=60
        )
        
        @app_with_middleware.get("/test")
        async def test_endpoint():
            return {"message": "Test endpoint"}
            
        @app_with_middleware.get("/api/v1/auth/login")
        async def login_endpoint():
            return {"message": "Login endpoint"}
            
        return TestClient(app_with_middleware)
    
    def test_normal_request(self, client):
        """Test that normal requests are allowed."""
        response = client.get("/test")
        assert response.status_code == 200
        assert "X-RateLimit-Remaining" in response.headers
        
    def test_rate_limit_exceeded(self, client):
        """Test that exceeding the rate limit returns a 429 response."""
        # Make 5 requests (consuming all tokens)
        for _ in range(5):
            response = client.get("/test")
            assert response.status_code == 200
            
        # The 6th request should be rejected
        response = client.get("/test")
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"
        
    def test_path_specific_rate_limit(self, client):
        """Test that path-specific rate limits are applied."""
        # Login endpoint has a stricter rate limit (10 requests)
        # Make 10 requests to the login endpoint
        for _ in range(10):
            response = client.get("/api/v1/auth/login")
            assert response.status_code == 200
            
        # The 11th request should be rejected
        response = client.get("/api/v1/auth/login")
        assert response.status_code == 429
        
    def test_different_clients(self, client):
        """Test that different clients have separate rate limits."""
        # Make 5 requests from client1
        for _ in range(5):
            response = client.get("/test", headers={"X-Forwarded-For": "client1"})
            assert response.status_code == 200
            
        # The 6th request from client1 should be rejected
        response = client.get("/test", headers={"X-Forwarded-For": "client1"})
        assert response.status_code == 429
        
        # But client2 should still be allowed
        response = client.get("/test", headers={"X-Forwarded-For": "client2"})
        assert response.status_code == 200
        
    def test_api_key_rate_limit(self, client):
        """Test that API key-based rate limiting works."""
        # API key has a higher rate limit (300 requests)
        # Make 5 requests with API key
        for _ in range(5):
            response = client.get("/test", headers={"X-API-Key": "test_api_key"})
            assert response.status_code == 200
            
        # The 6th request should still be allowed (API key has higher limit)
        response = client.get("/test", headers={"X-API-Key": "test_api_key"})
        assert response.status_code == 200


if __name__ == "__main__":
    unittest.main() 