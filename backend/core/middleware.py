"""
Middleware for FastAPI application.
"""
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.input_sanitizer import InputSanitizer

class SanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for sanitizing request inputs to prevent security vulnerabilities.
    
    This middleware sanitizes:
    - Query parameters
    - Path parameters
    - Request body JSON data
    """
    
    def __init__(self, app: ASGIApp):
        """Initialize the middleware."""
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request, sanitizing inputs before they reach route handlers.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            The response from the next middleware or route handler
        """
        # Create a copy of the request to modify
        request = await self._sanitize_request(request)
        
        # Call the next middleware or route handler
        response = await call_next(request)
        
        return response
    
    async def _sanitize_request(self, request: Request) -> Request:
        """
        Sanitize the request inputs.
        
        Args:
            request: The incoming request
            
        Returns:
            The sanitized request
        """
        # Sanitize query parameters
        if request.query_params:
            # FastAPI's query_params are immutable, so we need to access the underlying scope
            query_params = dict(request.query_params)
            sanitized_query = {k: InputSanitizer.sanitize_string(v) for k, v in query_params.items()}
            
            # Update the request's query parameters in the scope
            request.scope["query_string"] = "&".join(f"{k}={v}" for k, v in sanitized_query.items()).encode()
        
        # Sanitize path parameters
        if request.path_params:
            # Path parameters are mutable
            for key, value in request.path_params.items():
                if isinstance(value, str):
                    request.path_params[key] = InputSanitizer.sanitize_string(value)
        
        # Sanitize request body if it's JSON
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                # Read the request body
                body = await request.body()
                if body:
                    # Parse the JSON body
                    json_body = json.loads(body)
                    
                    # Sanitize the JSON body
                    if isinstance(json_body, dict):
                        sanitized_body = InputSanitizer.sanitize_dict(json_body)
                    elif isinstance(json_body, list):
                        sanitized_body = InputSanitizer.sanitize_list(json_body)
                    else:
                        # If it's a primitive type, just convert it back to JSON
                        sanitized_body = json_body
                    
                    # Replace the request body with the sanitized version
                    # We need to modify the request's _receive method to return the sanitized body
                    body = json.dumps(sanitized_body).encode()
                    
                    # Create a new receive function that returns the sanitized body
                    old_receive = request.scope.get("receive", None)
                    
                    async def new_receive():
                        """Return the sanitized body instead of the original."""
                        data = await old_receive()
                        if data["type"] == "http.request":
                            data["body"] = body
                        return data
                    
                    request.scope["receive"] = new_receive
            except json.JSONDecodeError:
                # If the body is not valid JSON, just leave it as is
                pass
        
        return request 