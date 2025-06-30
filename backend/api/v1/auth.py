"""
Authentication API

This module provides API endpoints for user authentication and authorization.
"""

from datetime import timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from core.auth import (
    authenticate_user, create_token_response, get_password_hash, 
    get_current_active_user, get_admin_user, verify_refresh_token,
    get_user, get_user_by_email, user_to_model
)
from core.config import get_settings
from core.session import SessionManager, TwoFactorAuth, get_session_from_request
from db.database import get_database
from db.models import User, Role
from models.user import UserCreate, UserUpdate, User as UserModel

# Get settings
settings = get_settings()

# Create router
router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={401: {"description": "Unauthorized"}},
)

# Define additional models
class Token(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: str
    token_type: str

class TokenRefresh(BaseModel):
    """Token refresh request model"""
    refresh_token: str

class PasswordReset(BaseModel):
    """Password reset request model"""
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    """Password reset confirmation model"""
    token: str
    new_password: str

class UserResponse(BaseModel):
    """User response model"""
    user: UserModel
    access_token: str
    refresh_token: str
    token_type: str

class TwoFactorSetupResponse(BaseModel):
    """2FA setup response model"""
    secret: str
    qr_code_uri: str

class TwoFactorVerifyRequest(BaseModel):
    """2FA verification request model"""
    code: str

class TwoFactorStatusResponse(BaseModel):
    """2FA status response model"""
    enabled: bool

@router.post("/token", response_model=Token)
async def login_for_access_token(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_database)
):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login time
    user.last_login = timedelta(seconds=0)
    db.commit()
    
    # Create session
    session_id = SessionManager.create_session(
        user_id=user.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent", "")
    )
    
    # Set session cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=not settings.debug,  # Secure in production
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60
    )
    
    # Create and return tokens
    return create_token_response(user)

@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_database)
):
    """
    Refresh access token using a refresh token
    """
    user = verify_refresh_token(token_data.refresh_token, db)
    return create_token_response(user)

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_database)
):
    """
    Register a new user
    """
    # Check if username already exists
    if get_user(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    
    # First user is admin, others are regular users
    is_first_user = db.query(User).count() == 0
    role = Role.ADMIN if is_first_user else Role.USER
    is_admin = is_first_user
    
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        is_active=True,
        is_admin=is_admin,
        role=role
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create tokens
    tokens = create_token_response(db_user)
    
    # Return user and tokens
    return {
        "user": user_to_model(db_user),
        **tokens
    }

@router.post("/password-reset/request")
async def request_password_reset(
    reset_data: PasswordReset,
    db: Session = Depends(get_database)
):
    """
    Request a password reset
    """
    # Find user by email
    user = get_user_by_email(db, reset_data.email)
    
    # Always return success to prevent email enumeration
    if not user:
        return {"message": "If your email is registered, you will receive a password reset link"}
    
    # In a real application, you would:
    # 1. Generate a password reset token
    # 2. Store it in the database with an expiration
    # 3. Send an email with a link containing the token
    
    # For now, we'll just return a success message
    return {"message": "If your email is registered, you will receive a password reset link"}

@router.post("/password-reset/confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_database)
):
    """
    Confirm a password reset
    """
    # In a real application, you would:
    # 1. Verify the token
    # 2. Check if it's expired
    # 3. Update the user's password
    
    # For now, we'll just return a success message
    return {"message": "Password has been reset successfully"}

@router.get("/me", response_model=UserModel)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information
    """
    return user_to_model(current_user)

@router.put("/me", response_model=UserModel)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """
    Update current user information
    """
    # Update user fields
    if user_update.username is not None:
        # Check if username is taken
        existing_user = get_user(db, user_update.username)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        current_user.username = user_update.username
    
    if user_update.email is not None:
        # Check if email is taken
        existing_user = get_user_by_email(db, user_update.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        current_user.email = user_update.email
    
    if user_update.password is not None:
        current_user.hashed_password = get_password_hash(user_update.password)
    
    db.commit()
    db.refresh(current_user)
    
    return user_to_model(current_user)

@router.get("/users", response_model=List[UserModel])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_database)
):
    """
    Get all users (admin only)
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return [user_to_model(user) for user in users]

@router.get("/users/{user_id}", response_model=UserModel)
async def read_user(
    user_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_database)
):
    """
    Get a specific user by ID (admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user_to_model(user)

@router.put("/users/{user_id}", response_model=UserModel)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_database)
):
    """
    Update a specific user by ID (admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user fields
    if user_update.username is not None:
        # Check if username is taken
        existing_user = get_user(db, user_update.username)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        user.username = user_update.username
    
    if user_update.email is not None:
        # Check if email is taken
        existing_user = get_user_by_email(db, user_update.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        user.email = user_update.email
    
    if user_update.password is not None:
        user.hashed_password = get_password_hash(user_update.password)
    
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    
    db.commit()
    db.refresh(user)
    
    return user_to_model(user)

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_database)
):
    """
    Delete a specific user by ID (admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own user account"
        )
    
    db.delete(user)
    db.commit()
    
    return None

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session: Dict[str, Any] = Depends(get_session_from_request)
):
    """
    Logout and invalidate session
    """
    # Get session ID from cookie or header
    session_id = request.cookies.get("session_id") or request.headers.get("X-Session-ID")
    
    if session_id:
        # Invalidate session
        SessionManager.invalidate_session(session_id)
        
        # Clear session cookie
        response.delete_cookie(key="session_id")
    
    return {"message": "Successfully logged out"}

@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """
    Set up 2FA for the current user
    """
    # Generate a new TOTP secret
    secret = TwoFactorAuth.generate_secret()
    
    # In a real application, you would:
    # 1. Store the secret in the database
    # 2. Associate it with the user
    
    # For now, we'll just return the secret and QR code URI
    qr_code_uri = TwoFactorAuth.get_totp_uri(
        secret=secret,
        username=current_user.username,
        issuer="SocialMediaAnalysis"
    )
    
    return {
        "secret": secret,
        "qr_code_uri": qr_code_uri
    }

@router.post("/2fa/verify")
async def verify_2fa(
    request: Request,
    verify_data: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """
    Verify a 2FA code
    """
    # In a real application, you would:
    # 1. Get the user's TOTP secret from the database
    # 2. Verify the code against the secret
    
    # For demo purposes, we'll use a hardcoded secret
    # DO NOT DO THIS IN PRODUCTION
    demo_secret = "JBSWY3DPEHPK3PXP"
    
    # Verify the code
    if not TwoFactorAuth.verify_totp(demo_secret, verify_data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code"
        )
    
    # Get session ID from cookie or header
    session_id = request.cookies.get("session_id") or request.headers.get("X-Session-ID")
    
    if session_id:
        # Mark session as 2FA verified
        SessionManager.set_2fa_verified(session_id, True)
    
    return {"message": "2FA verification successful"}

@router.get("/2fa/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """
    Get 2FA status for the current user
    """
    # In a real application, you would:
    # 1. Check if the user has 2FA enabled in the database
    
    # For now, we'll just return a hardcoded value
    return {"enabled": False} 