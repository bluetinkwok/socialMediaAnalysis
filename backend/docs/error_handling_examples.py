"""
Examples of using secure error handling in API endpoints.

This file is for documentation purposes only and is not meant to be imported.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional

from core.error_handlers import (
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ConflictError,
    ServerError
)
from core.auth import get_current_user
from db.models import User

router = APIRouter()

# Example 1: Basic error handling
@router.get("/users/{user_id}")
async def get_user(user_id: int, current_user: User = Depends(get_current_user)):
    """Example of handling not found errors."""
    # Check if user exists
    user = await get_user_from_db(user_id)
    if not user:
        # Return a standardized 404 error
        raise NotFoundError(
            message=f"User with ID {user_id} not found",
            details={"user_id": user_id}
        )
    
    # Check permissions
    if user.id != current_user.id and not current_user.is_admin:
        # Return a standardized 403 error
        raise ForbiddenError(
            message="You don't have permission to access this user",
            details={
                "required_role": "admin",
                "user_id": user_id
            }
        )
    
    return user

# Example 2: Handling business logic errors
@router.post("/users/")
async def create_user(user_data: dict):
    """Example of handling conflict errors."""
    # Check if username already exists
    existing_user = await get_user_by_username(user_data["username"])
    if existing_user:
        # Return a standardized 409 error
        raise ConflictError(
            message="Username already exists",
            details={"field": "username"}
        )
    
    # Validate password strength
    if len(user_data["password"]) < 8:
        # Return a standardized 400 error
        raise BadRequestError(
            message="Password is too weak",
            details={
                "field": "password",
                "reason": "Password must be at least 8 characters long"
            }
        )
    
    # Create user
    try:
        new_user = await create_user_in_db(user_data)
        return new_user
    except Exception as e:
        # Log the detailed error but return a generic 500 error
        # The error_handlers will log the full exception details
        raise ServerError(
            message="Failed to create user",
            details={"error": str(e)}
        )

# Example 3: Authentication errors
@router.get("/secure-resource")
async def get_secure_resource(token: str):
    """Example of handling authentication errors."""
    if not token:
        # Return a standardized 401 error
        raise UnauthorizedError(
            message="Authentication required",
            details={"header": "Authorization"}
        )
    
    try:
        # Validate token
        user = await validate_token(token)
        if not user:
            raise UnauthorizedError(
                message="Invalid or expired token",
                details={"reason": "token_invalid"}
            )
        
        # Check if user has required permissions
        if not user.has_permission("read:secure-resource"):
            raise ForbiddenError(
                message="Insufficient permissions",
                details={"required_permission": "read:secure-resource"}
            )
        
        return {"data": "This is a secure resource"}
    except Exception as e:
        # The generic exception handler will handle unexpected errors
        # and log them appropriately without leaking details to the client
        raise

# These functions are placeholders and would be implemented elsewhere
async def get_user_from_db(user_id: int):
    """Placeholder for database query."""
    pass

async def get_user_by_username(username: str):
    """Placeholder for database query."""
    pass

async def create_user_in_db(user_data: dict):
    """Placeholder for database operation."""
    pass

async def validate_token(token: str):
    """Placeholder for token validation."""
    pass
