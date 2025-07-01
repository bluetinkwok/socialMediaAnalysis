"""
Security Middleware Module

This module provides middleware components for security logging and metrics
collection in FastAPI applications. It integrates with the security_logger
and security metrics modules to track security-related events.
"""

import time
from typing import Callable, Dict, List, Optional

from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.security_logger import security_logger
from models.security import SecurityMetrics


class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging security-related HTTP requests and responses.
    
    This middleware logs information about incoming requests and outgoing responses,
    focusing on security-relevant details such as IP addresses, authentication status,
    and response status codes.
    """
    
    def __init__(self, app: ASGIApp, exclude_paths: Optional[List[str]] = None):
        """
        Initialize the security logging middleware.
        
        Args:
            app: The ASGI application
            exclude_paths: List of paths to exclude from logging
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and log security-relevant information.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler
            
        Returns:
            The HTTP response
        """
        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Get request details
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        method = request.method
        path = request.url.path
        
        # Extract security-relevant headers
        user_agent = request.headers.get("user-agent", "")
        referer = request.headers.get("referer", "")
        origin = request.headers.get("origin", "")
        
        # Check for required security headers
        missing_headers = self._check_security_headers(request)
        
        # Log request
        security_logger.info(
            "HTTP request received",
            ip_address=client_ip,
            method=method,
            path=path,
            user_agent=user_agent,
            referer=referer,
            origin=origin
        )
        
        # Track missing security headers
        for header in missing_headers:
            SecurityMetrics.track_missing_security_header(header)
            security_logger.medium(
                "Missing security header",
                header=header,
                ip_address=client_ip,
                method=method,
                path=path
            )
        
        # Process the request
        try:
            response = await call_next(request)
            
            # Calculate request duration
            duration = time.time() - start_time
            
            # Log response
            status_code = response.status_code
            security_logger.info(
                "HTTP response sent",
                ip_address=client_ip,
                method=method,
                path=path,
                status_code=status_code,
                duration=duration
            )
            
            # Log security-relevant status codes
            if 400 <= status_code < 500:
                security_logger.low(
                    "Client error response",
                    ip_address=client_ip,
                    method=method,
                    path=path,
                    status_code=status_code
                )
            elif status_code >= 500:
                security_logger.medium(
                    "Server error response",
                    ip_address=client_ip,
                    method=method,
                    path=path,
                    status_code=status_code
                )
            
            return response
            
        except Exception as e:
            # Log exceptions
            security_logger.high(
                "Exception during request processing",
                ip_address=client_ip,
                method=method,
                path=path,
                exception=str(e),
                exception_type=type(e).__name__
            )
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract the client IP address from the request.
        
        Args:
            request: The HTTP request
            
        Returns:
            The client IP address
        """
        # Try X-Forwarded-For header first (if behind proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Get the original client IP (first in the list)
            return forwarded_for.split(",")[0].strip()
        
        # Fall back to direct client address
        return request.client.host if request.client else "unknown"
    
    def _check_security_headers(self, request: Request) -> List[str]:
        """
        Check for required security headers in the request.
        
        Args:
            request: The HTTP request
            
        Returns:
            List of missing security headers
        """
        # Define required security headers for different request types
        required_headers = []
        
        # For API requests
        if request.url.path.startswith("/api/"):
            # API key or authorization for authenticated endpoints
            if not request.url.path.startswith("/api/public/"):
                required_headers.append("authorization")
        
        # For form submissions
        if request.method == "POST" and "content-type" in request.headers:
            content_type = request.headers["content-type"]
            if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                required_headers.append("x-csrf-token")
        
        # Check which required headers are missing
        missing_headers = [header for header in required_headers 
                          if header not in request.headers]
        
        return missing_headers


class SecurityMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting security metrics from HTTP requests and responses.
    
    This middleware tracks metrics such as request counts, response status codes,
    and request durations for security monitoring purposes.
    """
    
    def __init__(self, app: ASGIApp, exclude_paths: Optional[List[str]] = None):
        """
        Initialize the security metrics middleware.
        
        Args:
            app: The ASGI application
            exclude_paths: List of paths to exclude from metrics collection
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and collect security metrics.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler
            
        Returns:
            The HTTP response
        """
        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Start timing
        start_time = time.time()
        
        # Process the request
        response = await call_next(request)
        
        # Calculate request duration
        duration = time.time() - start_time
        
        # Track metrics based on response
        status_code = response.status_code
        path = request.url.path
        
        # Track rate limiting if applicable
        if status_code == 429:  # Too Many Requests
            SecurityMetrics.track_rate_limit(
                endpoint=path,
                limit_type="requests_per_minute",
                exceeded=True,
                current_usage=1.0  # 100% of limit
            )
        
        # Track authentication failures
        if path.startswith("/api/auth") and status_code == 401:
            SecurityMetrics.track_auth_attempt(
                auth_method="password",
                success=False,
                failure_reason="invalid_credentials"
            )
        
        # Track access denied
        if status_code == 403:
            SecurityMetrics.track_access_control(
                resource_type="api",
                action=request.method.lower(),
                allowed=False,
                latency=duration
            )
        
        # Track input validation failures
        if status_code == 400 and "validation" in response.headers.get("x-error-type", ""):
            SecurityMetrics.track_input_validation(
                validation_type="schema",
                endpoint=path,
                passed=False
            )
        
        return response


def setup_security_middleware(app: FastAPI) -> None:
    """
    Set up security middleware for a FastAPI application.
    
    Args:
        app: The FastAPI application
    """
    # Add security logging middleware
    app.add_middleware(SecurityLoggingMiddleware)
    
    # Add security metrics middleware
    app.add_middleware(SecurityMetricsMiddleware) 