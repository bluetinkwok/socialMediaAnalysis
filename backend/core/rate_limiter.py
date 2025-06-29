"""
Rate limiting middleware for FastAPI application.

This module provides a rate limiting middleware to protect the API from abuse.
It implements both IP-based and API key-based rate limiting.
"""

import time
from typing import Dict, Tuple, Callable, Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging
from collections import defaultdict

from core.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)
settings = get_settings()

class RateLimiter:
    """
    Rate limiter implementation using the token bucket algorithm.
    """
    
    def __init__(self, rate_limit: int, time_window: int):
        """
        Initialize the rate limiter.
        
        Args:
            rate_limit: Maximum number of requests allowed in the time window
            time_window: Time window in seconds
        """
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.tokens: Dict[str, Tuple[int, float]] = {}
        
    def is_allowed(self, key: str) -> Tuple[bool, int, int]:
        """
        Check if a request is allowed based on the rate limit.
        
        Args:
            key: The identifier for the client (IP address or API key)
            
        Returns:
            Tuple of (is_allowed, remaining_tokens, retry_after)
        """
        current_time = time.time()
        
        # If key doesn't exist, create a new entry
        if key not in self.tokens:
            self.tokens[key] = (self.rate_limit - 1, current_time)
            return True, self.rate_limit - 1, 0
            
        tokens_remaining, last_request_time = self.tokens[key]
        
        # Calculate time passed since last request
        time_passed = current_time - last_request_time
        
        # Calculate token refill based on time passed
        token_refill = int(time_passed * self.rate_limit / self.time_window)
        
        # Update tokens remaining, but don't exceed the rate limit
        tokens_remaining = min(self.rate_limit, tokens_remaining + token_refill)
        
        # If no tokens remaining, calculate retry after time
        if tokens_remaining <= 0:
            retry_after = int(self.time_window - time_passed)
            retry_after = max(0, retry_after)  # Ensure non-negative
            self.tokens[key] = (0, current_time)
            return False, 0, retry_after
            
        # Consume a token and update the last request time
        self.tokens[key] = (tokens_remaining - 1, current_time)
        return True, tokens_remaining - 1, 0
        
    def cleanup(self, max_age: int = 3600):
        """
        Remove old entries from the tokens dictionary.
        
        Args:
            max_age: Maximum age of entries in seconds (default: 1 hour)
        """
        current_time = time.time()
        keys_to_remove = []
        
        for key, (_, last_request_time) in self.tokens.items():
            if current_time - last_request_time > max_age:
                keys_to_remove.append(key)
                
        for key in keys_to_remove:
            del self.tokens[key]


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting requests to the API.
    
    This middleware implements:
    - IP-based rate limiting for public endpoints
    - API key-based rate limiting for authenticated endpoints
    - Different rate limits for different endpoints
    """
    
    def __init__(
        self,
        app: ASGIApp,
        default_rate_limit: int = 60,
        default_time_window: int = 60,
        api_key_rate_limit: int = 300,
        api_key_time_window: int = 60,
    ):
        """
        Initialize the middleware.
        
        Args:
            app: The ASGI application
            default_rate_limit: Default rate limit for IP-based limiting (requests per time window)
            default_time_window: Default time window for IP-based limiting (in seconds)
            api_key_rate_limit: Rate limit for API key-based limiting (requests per time window)
            api_key_time_window: Time window for API key-based limiting (in seconds)
        """
        super().__init__(app)
        
        # Create rate limiters
        self.ip_limiter = RateLimiter(default_rate_limit, default_time_window)
        self.api_key_limiter = RateLimiter(api_key_rate_limit, api_key_time_window)
        
        # Path-specific rate limiters
        self.path_limiters = {
            # Limit login attempts more strictly
            "/api/v1/auth/login": RateLimiter(10, 60),
            # Limit registration attempts
            "/api/v1/auth/register": RateLimiter(5, 60),
            # Limit password reset requests
            "/api/v1/auth/password-reset": RateLimiter(3, 60),
            # Limit security endpoints
            "/api/v1/security": RateLimiter(20, 60),
        }
        
        # Schedule periodic cleanup
        self._setup_cleanup()
        
    def _setup_cleanup(self):
        """Set up periodic cleanup of the rate limiters."""
        import threading
        
        def cleanup():
            while True:
                time.sleep(3600)  # Run cleanup every hour
                self.ip_limiter.cleanup()
                self.api_key_limiter.cleanup()
                for limiter in self.path_limiters.values():
                    limiter.cleanup()
                
        # Start cleanup thread
        cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        cleanup_thread.start()
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request, applying rate limiting before it reaches route handlers.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            The response from the next middleware or route handler
        """
        # Get client IP address
        client_ip = self._get_client_ip(request)
        
        # Get API key if present
        api_key = self._get_api_key(request)
        
        # Check if path has specific rate limit
        path = request.url.path
        path_limiter = self._get_path_limiter(path)
        
        # Apply rate limiting
        is_allowed, remaining, retry_after = self._check_rate_limit(
            client_ip, api_key, path_limiter
        )
        
        if not is_allowed:
            # Log rate limit exceeded
            logger.warning(f"Rate limit exceeded for {client_ip or api_key} on {path}")
            
            # Return 429 Too Many Requests
            return Response(
                content=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after),
                },
            )
            
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
        
    def _get_client_ip(self, request: Request) -> str:
        """
        Get the client IP address from the request.
        
        Args:
            request: The incoming request
            
        Returns:
            The client IP address
        """
        # Try to get the real IP from X-Forwarded-For header
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get the first IP in the list (client IP)
            return forwarded_for.split(",")[0].strip()
            
        # Fall back to client host
        return request.client.host if request.client else "unknown"
        
    def _get_api_key(self, request: Request) -> Optional[str]:
        """
        Get the API key from the request headers or query parameters.
        
        Args:
            request: The incoming request
            
        Returns:
            The API key if present, None otherwise
        """
        # Try to get from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header.split("Bearer ")[1].strip()
            
        # Try to get from X-API-Key header
        api_key_header = request.headers.get("X-API-Key")
        if api_key_header:
            return api_key_header
            
        # Try to get from query parameters
        api_key_query = request.query_params.get("api_key")
        if api_key_query:
            return api_key_query
            
        return None
        
    def _get_path_limiter(self, path: str) -> Optional[RateLimiter]:
        """
        Get the rate limiter for a specific path.
        
        Args:
            path: The request path
            
        Returns:
            The rate limiter for the path if exists, None otherwise
        """
        # Check for exact path match
        if path in self.path_limiters:
            return self.path_limiters[path]
            
        # Check for path prefix match
        for prefix, limiter in self.path_limiters.items():
            if path.startswith(prefix):
                return limiter
                
        return None
        
    def _check_rate_limit(
        self, client_ip: str, api_key: Optional[str], path_limiter: Optional[RateLimiter]
    ) -> Tuple[bool, int, int]:
        """
        Check if the request is allowed based on rate limits.
        
        Args:
            client_ip: The client IP address
            api_key: The API key if present
            path_limiter: The path-specific rate limiter if applicable
            
        Returns:
            Tuple of (is_allowed, remaining_tokens, retry_after)
        """
        # If path has specific rate limiter, use it with IP
        if path_limiter:
            return path_limiter.is_allowed(client_ip)
            
        # If API key is present, use API key rate limiter
        if api_key:
            return self.api_key_limiter.is_allowed(api_key)
            
        # Otherwise use IP-based rate limiter
        return self.ip_limiter.is_allowed(client_ip) 