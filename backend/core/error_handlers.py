"""
Secure Error Handling

This module provides custom exception handlers to prevent sensitive information
leakage while still providing useful error messages and logging detailed errors.
"""

import logging
import traceback
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
        internal_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.message = message
        self.internal_code = internal_code or f"ERR_{status_code}"
        self.details = details
        super().__init__(message)


class BadRequestError(APIError):
    """Bad request error."""
    
    def __init__(
        self,
        message: str = "Invalid request",
        internal_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=message,
            internal_code=internal_code or "ERR_BAD_REQUEST",
            details=details
        )


class UnauthorizedError(APIError):
    """Unauthorized error."""
    
    def __init__(
        self,
        message: str = "Authentication required",
        internal_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=message,
            internal_code=internal_code or "ERR_UNAUTHORIZED",
            details=details
        )


class ForbiddenError(APIError):
    """Forbidden error."""
    
    def __init__(
        self,
        message: str = "You don't have permission to access this resource",
        internal_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message=message,
            internal_code=internal_code or "ERR_FORBIDDEN",
            details=details
        )


class NotFoundError(APIError):
    """Not found error."""
    
    def __init__(
        self,
        message: str = "Resource not found",
        internal_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            message=message,
            internal_code=internal_code or "ERR_NOT_FOUND",
            details=details
        )


class ConflictError(APIError):
    """Conflict error."""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        internal_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            message=message,
            internal_code=internal_code or "ERR_CONFLICT",
            details=details
        )


class RateLimitError(APIError):
    """Rate limit exceeded error."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        internal_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            message=message,
            internal_code=internal_code or "ERR_RATE_LIMIT",
            details=details
        )


class ServerError(APIError):
    """Server error."""
    
    def __init__(
        self,
        message: str = "Internal server error",
        internal_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=message,
            internal_code=internal_code or "ERR_SERVER",
            details=details
        )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle API errors with secure error responses."""
    # Log detailed error information for debugging
    log_message = f"{exc.internal_code}: {exc.message}"
    if exc.status_code >= 500:
        logger.error(
            log_message,
            extra={
                "path": request.url.path,
                "method": request.method,
                "client_ip": request.client.host,
                "details": exc.details,
            },
        )
    else:
        logger.warning(
            log_message,
            extra={
                "path": request.url.path,
                "method": request.method,
                "client_ip": request.client.host,
                "details": exc.details,
            },
        )

    # Return a clean error response without sensitive details
    response = {
        "error": {
            "code": exc.internal_code,
            "message": exc.message,
        }
    }
    
    # Only include details in development mode
    if settings.debug and exc.details:
        response["error"]["details"] = exc.details
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions with secure error responses."""
    # Map HTTP exceptions to our custom error format
    error_code = f"ERR_{exc.status_code}"
    
    # Log the error
    log_level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
    logger.log(
        log_level,
        f"{error_code}: {exc.detail}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host,
            "status_code": exc.status_code,
        },
    )
    
    # Return a clean error response
    response = {
        "error": {
            "code": error_code,
            "message": exc.detail,
        }
    }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response,
    )


async def validation_exception_handler(request: Request, exc: Union[RequestValidationError, ValidationError]) -> JSONResponse:
    """Handle validation errors with secure error responses."""
    # Extract error details but sanitize them
    sanitized_errors = []
    for error in exc.errors():
        sanitized_errors.append({
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"],
        })
    
    # Log the validation error
    logger.warning(
        "Validation error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host,
            "errors": sanitized_errors,
        },
    )
    
    # Return a clean error response
    response = {
        "error": {
            "code": "ERR_VALIDATION",
            "message": "Validation error",
        }
    }
    
    # Only include error details in development mode
    if settings.debug:
        response["error"]["details"] = sanitized_errors
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions with secure error responses."""
    # Generate a unique error ID for tracking
    import uuid
    error_id = str(uuid.uuid4())
    
    # Log the detailed error for debugging
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "error_id": error_id,
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host,
            "exception_type": exc.__class__.__name__,
            "traceback": traceback.format_exc(),
        },
    )
    
    # Return a generic error message without leaking implementation details
    response = {
        "error": {
            "code": "ERR_SERVER",
            "message": "An unexpected error occurred",
            "error_id": error_id,  # Include the error ID for support reference
        }
    }
    
    # Only include exception details in development mode
    if settings.debug:
        response["error"]["details"] = {
            "exception": str(exc),
            "type": exc.__class__.__name__,
        }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response,
    )


def add_error_handlers(app: FastAPI) -> None:
    """Add all error handlers to the FastAPI application."""
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler) 