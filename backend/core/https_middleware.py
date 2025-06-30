"""
HTTPS Enforcement and Trusted Host Middleware

This module provides middleware for enforcing HTTPS and validating trusted hosts.
"""

from typing import List, Optional, Set
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.datastructures import URL
from starlette.types import ASGIApp
from starlette.responses import RedirectResponse

from core.config import get_settings

settings = get_settings()

class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware for redirecting HTTP requests to HTTPS.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        https_port: int = 443,
        status_code: int = 307,
    ):
        """
        Initialize the HTTPSRedirectMiddleware.
        
        Args:
            app: The ASGI application
            https_port: The HTTPS port to redirect to
            status_code: The HTTP status code for the redirect
        """
        super().__init__(app)
        self.https_port = https_port
        self.status_code = status_code
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Dispatch the request and redirect HTTP to HTTPS.
        
        Args:
            request: The FastAPI request
            call_next: The next endpoint to call
            
        Returns:
            Response: The response or redirect
        """
        # Skip HTTPS redirect in debug mode
        if settings.debug:
            return await call_next(request)
        
        # Skip HTTPS redirect for localhost
        host = request.headers.get("host", "").split(":")[0]
        if host in ("localhost", "127.0.0.1"):
            return await call_next(request)
        
        # Check if the request is already HTTPS
        if request.url.scheme == "https":
            return await call_next(request)
        
        # Redirect to HTTPS
        url = URL(str(request.url))
        url = url.replace(scheme="https")
        
        # Set the port if it's not the default HTTPS port
        if self.https_port != 443:
            url = url.replace(netloc=f"{url.netloc.split(':')[0]}:{self.https_port}")
        
        return RedirectResponse(url=str(url), status_code=self.status_code)


class TrustedHostMiddleware(BaseHTTPMiddleware):
    """
    Middleware for validating trusted hosts.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        allowed_hosts: List[str] = None,
        www_redirect: bool = True,
    ):
        """
        Initialize the TrustedHostMiddleware.
        
        Args:
            app: The ASGI application
            allowed_hosts: List of allowed hosts
            www_redirect: Whether to redirect www to non-www or vice versa
        """
        super().__init__(app)
        
        # Default allowed hosts
        if allowed_hosts is None:
            allowed_hosts = ["*"]
        
        self.allowed_hosts = set(allowed_hosts)
        self.www_redirect = www_redirect
        
        # Check if we need to allow all hosts
        self.allow_all = "*" in self.allowed_hosts
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Dispatch the request and validate the host.
        
        Args:
            request: The FastAPI request
            call_next: The next endpoint to call
            
        Returns:
            Response: The response or error
        """
        # Skip host validation in debug mode
        if settings.debug:
            return await call_next(request)
        
        # Get the host from the request
        host = request.headers.get("host", "").split(":")[0]
        
        # Allow all hosts if configured
        if self.allow_all:
            return await call_next(request)
        
        # Check if the host is allowed
        if host in self.allowed_hosts:
            return await call_next(request)
        
        # Check for www redirect
        if self.www_redirect:
            if host.startswith("www."):
                non_www_host = host[4:]
                if non_www_host in self.allowed_hosts:
                    # Redirect www to non-www
                    url = URL(str(request.url))
                    url = url.replace(netloc=url.netloc.replace(host, non_www_host))
                    return RedirectResponse(url=str(url), status_code=301)
            else:
                www_host = f"www.{host}"
                if www_host in self.allowed_hosts:
                    # Redirect non-www to www
                    url = URL(str(request.url))
                    url = url.replace(netloc=url.netloc.replace(host, www_host))
                    return RedirectResponse(url=str(url), status_code=301)
        
        # Host not allowed
        return Response(
            content="Invalid host header",
            status_code=400,
        )


def add_https_middleware(app: FastAPI) -> None:
    """
    Add HTTPS enforcement middleware to FastAPI application.
    
    Args:
        app: FastAPI application
    """
    # Add HTTPS redirect middleware
    app.add_middleware(HTTPSRedirectMiddleware)


def add_trusted_host_middleware(app: FastAPI, allowed_hosts: List[str] = None) -> None:
    """
    Add trusted host middleware to FastAPI application.
    
    Args:
        app: FastAPI application
        allowed_hosts: List of allowed hosts
    """
    # Get allowed hosts from settings if not provided
    if allowed_hosts is None:
        allowed_hosts = settings.allowed_hosts.split(",") if settings.allowed_hosts else ["*"]
    
    # Add trusted host middleware
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts) 