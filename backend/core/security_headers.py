"""
Security Headers Middleware

This module provides middleware for adding security headers, enforcing HTTPS,
and validating trusted hosts.
"""

from typing import Callable, List
from fastapi import FastAPI, Request, Response
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.config import get_settings

settings = get_settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers to all responses."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        
        return response


def add_security_middleware(app: FastAPI) -> None:
    """Add all security middleware to the FastAPI application."""
    
    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Add HTTPS redirect middleware in production
    if not settings.debug:
        app.add_middleware(HTTPSRedirectMiddleware)
    
    # Add trusted host middleware with allowed hosts
    trusted_hosts = settings.trusted_hosts.split(",") if settings.trusted_hosts else ["localhost", "127.0.0.1"]
    if not settings.debug:
        # In production, only allow specified hosts
        app.add_middleware(
            TrustedHostMiddleware, 
            allowed_hosts=trusted_hosts
        ) 