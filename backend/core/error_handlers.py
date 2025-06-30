"""
Secure Error Handling

This module provides custom exception handlers to prevent sensitive information
leakage while still providing useful error messages and logging detailed errors.
"""

import logging
import traceback
import uuid
from typing import Any, Dict, Optional, Union

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)
settings = get_settings()


class APIError(Exception):
    """Base class for API errors with secure error handling."""
    
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        message: str = "An unexpected error occurred",
        internal_code: str = "ERR_SERVER",
        details: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.message = message
        self.internal_code = internal_code
        self.details = details or {}
        super().__init__(self.message)


class BadRequestError(APIError):
    """400 Bad Request error."""
    
    def __init__(
        self,
        message: str = "Bad request",
        details: Optional[Dict[str, Any]] = None,
        internal_code: str = "ERR_BAD_REQUEST"
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=message,
            internal_code=internal_code,
            details=details
        )


class UnauthorizedError(APIError):
    """401 Unauthorized error."""
    
    def __init__(
        self,
        message: str = "Authentication required",
        details: Optional[Dict[str, Any]] = None,
        internal_code: str = "ERR_UNAUTHORIZED"
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=message,
            internal_code=internal_code,
            details=details
        )


class ForbiddenError(APIError):
    """403 Forbidden error."""
    
    def __init__(
        self,
        message: str = "Permission denied",
        details: Optional[Dict[str, Any]] = None,
        internal_code: str = "ERR_FORBIDDEN"
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message=message,
            internal_code=internal_code,
            details=details
        )


class NotFoundError(APIError):
    """404 Not Found error."""
    
    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[Dict[str, Any]] = None,
        internal_code: str = "ERR_NOT_FOUND"
    ):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            message=message,
            internal_code=internal_code,
            details=details
        )


class ConflictError(APIError):
    """409 Conflict error."""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[Dict[str, Any]] = None,
        internal_code: str = "ERR_CONFLICT"
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            message=message,
            internal_code=internal_code,
            details=details
        )


class RateLimitError(APIError):
    """429 Too Many Requests error."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        details: Optional[Dict[str, Any]] = None,
        internal_code: str = "ERR_RATE_LIMIT"
    ):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            message=message,
            internal_code=internal_code,
            details=details
        )


class ServerError(APIError):
    """500 Internal Server Error."""
    
    def __init__(
        self,
        message: str = "Internal server error",
        details: Optional[Dict[str, Any]] = None,
        internal_code: str = "ERR_SERVER"
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=message,
            internal_code=internal_code,
            details=details
        )


def _build_error_response(
    status_code: int,
    message: str,
    code: str,
    details: Optional[Dict[str, Any]] = None,
    error_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build a standardized error response.
    
    Args:
        status_code: HTTP status code
        message: Human-readable error message
        code: Error code for clients to use for handling
        details: Additional details about the error (only included in debug mode)
        error_id: Unique ID for tracking the error (only for 500 errors)
        
    Returns:
        Standardized error response dictionary
    """
    error_response = {
        "error": {
            "code": code,
            "message": message
        }
    }
    
    # Only include error_id for 500 errors
    if error_id and status_code >= 500:
        error_response["error"]["error_id"] = error_id
    
    # Only include details in debug mode
    if details and settings.debug:
        error_response["error"]["details"] = details
    
    return error_response


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """
    Handle custom API errors.
    
    Args:
        request: FastAPI request object
        exc: APIError exception
        
    Returns:
        JSONResponse with standardized error format
    """
    # Generate error ID for 500 errors
    error_id = str(uuid.uuid4()) if exc.status_code >= 500 else None
    
    # Log the error with appropriate severity
    log_method = logger.error if exc.status_code >= 500 else logger.warning
    log_message = f"API Error {exc.status_code}: {exc.message}"
    
    if error_id:
        log_message += f" (Error ID: {error_id})"
    
    log_method(log_message, extra={
        "status_code": exc.status_code,
        "error_code": exc.internal_code,
        "details": exc.details,
        "path": request.url.path,
        "method": request.method,
        "client_ip": request.client.host if request.client else None,
        "error_id": error_id
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(
            status_code=exc.status_code,
            message=exc.message,
            code=exc.internal_code,
            details=exc.details,
            error_id=error_id
        )
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle FastAPI/Starlette HTTP exceptions.
    
    Args:
        request: FastAPI request object
        exc: HTTPException
        
    Returns:
        JSONResponse with standardized error format
    """
    # Generate error ID for 500 errors
    error_id = str(uuid.uuid4()) if exc.status_code >= 500 else None
    
    # Create error code from status code
    error_code = f"ERR_{exc.status_code}"
    
    # Log the error with appropriate severity
    log_method = logger.error if exc.status_code >= 500 else logger.warning
    log_message = f"HTTP Exception {exc.status_code}: {exc.detail}"
    
    if error_id:
        log_message += f" (Error ID: {error_id})"
    
    log_method(log_message, extra={
        "status_code": exc.status_code,
        "error_code": error_code,
        "path": request.url.path,
        "method": request.method,
        "client_ip": request.client.host if request.client else None,
        "error_id": error_id
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(
            status_code=exc.status_code,
            message=str(exc.detail),
            code=error_code,
            error_id=error_id
        )
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors.
    
    Args:
        request: FastAPI request object
        exc: RequestValidationError
        
    Returns:
        JSONResponse with standardized error format
    """
    # Extract validation error details
    details = {"errors": []}
    for error in exc.errors():
        details["errors"].append({
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        })
    
    # Log the validation error
    logger.warning(
        f"Validation Error: {exc}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
            "details": details
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_build_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Validation error",
            code="ERR_VALIDATION",
            details=details
        )
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all other unhandled exceptions.
    
    Args:
        request: FastAPI request object
        exc: Any unhandled exception
        
    Returns:
        JSONResponse with standardized error format
    """
    # Generate error ID for tracking
    error_id = str(uuid.uuid4())
    
    # Get exception details
    exc_type = type(exc).__name__
    exc_msg = str(exc)
    stack_trace = traceback.format_exc()
    
    # Create detailed error information for logging
    details = {
        "type": exc_type,
        "message": exc_msg,
        "stack_trace": stack_trace
    }
    
    # Log the error
    logger.error(
        f"Unhandled Exception: {exc_type}: {exc_msg} (Error ID: {error_id})",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
            "error_id": error_id
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_build_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred",
            code="ERR_SERVER",
            details=details if settings.debug else None,
            error_id=error_id
        )
    )


def add_error_handlers(app: FastAPI) -> None:
    """
    Add all error handlers to the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler) 