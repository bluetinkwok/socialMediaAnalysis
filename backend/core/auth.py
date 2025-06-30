"""
Authentication Module

This module provides authentication functionality including JWT token-based authentication,
password hashing, and role-based access control.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError
from sqlalchemy.orm import Session

from core.config import get_settings
from db.database import get_database
from db.models import User, Role
from models.user import UserInDB, User as UserModel

# Get settings
settings = get_settings()

# Password context for hashing and verification
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_prefix}/{settings.api_version}/auth/token",
    scopes={
        "admin": "Full access to all resources",
        "user": "Standard user access",
        "viewer": "Read-only access to resources"
    }
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        bool: True if password matches hash, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hash a password.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)

def get_user(db: Session, username: str) -> Optional[User]:
    """
    Get a user from the database by username.
    
    Args:
        db: Database session
        username: Username to look up
        
    Returns:
        Optional[User]: User if found, None otherwise
    """
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Get a user from the database by email.
    
    Args:
        db: Database session
        email: Email to look up
        
    Returns:
        Optional[User]: User if found, None otherwise
    """
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Authenticate a user by username and password.
    
    Args:
        db: Database session
        username: Username for authentication
        password: Password for authentication
        
    Returns:
        Optional[User]: User if authentication successful, None otherwise
    """
    user = get_user(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time
        
    Returns:
        str: JWT access token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token with longer expiration.
    
    Args:
        data: Data to encode in the token
        
    Returns:
        str: JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)  # Refresh tokens last 7 days
    to_encode.update({"exp": expire, "token_type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    return encoded_jwt

def create_token_response(user: User) -> Dict[str, str]:
    """
    Create access and refresh tokens for a user.
    
    Args:
        user: User to create tokens for
        
    Returns:
        Dict[str, str]: Dictionary with access_token and refresh_token
    """
    # Define token data
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.value,
        "scopes": get_scopes_for_role(user.role)
    }
    
    # Create tokens
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

def get_scopes_for_role(role: Role) -> List[str]:
    """
    Get OAuth2 scopes for a given role.
    
    Args:
        role: User role
        
    Returns:
        List[str]: List of scope strings
    """
    if role == Role.ADMIN:
        return ["admin", "user", "viewer"]
    elif role == Role.USER:
        return ["user", "viewer"]
    else:  # Role.VIEWER
        return ["viewer"]

async def get_current_user(
    security_scopes: SecurityScopes, 
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_database)
) -> User:
    """
    Get the current authenticated user.
    
    Args:
        security_scopes: Security scopes required for the endpoint
        token: JWT token
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
        
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    
    try:
        # Decode the JWT token
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        token_scopes = payload.get("scopes", [])
        
        if user_id is None:
            raise credentials_exception
        
        # Check token type - reject refresh tokens used for access
        if payload.get("token_type") == "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token cannot be used for access",
                headers={"WWW-Authenticate": authenticate_value},
            )
            
    except (JWTError, ValidationError):
        raise credentials_exception
    
    # Get the user from the database
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if user is None or not user.is_active:
        raise credentials_exception
    
    # Check for required scopes
    for scope in security_scopes.scopes:
        if scope not in token_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required scope: {scope}",
                headers={"WWW-Authenticate": authenticate_value},
            )
    
    # Update last login time
    user.last_login = datetime.utcnow()
    db.commit()
    
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current active user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_admin_user(
    current_user: User = Security(get_current_user, scopes=["admin"])
) -> User:
    """
    Get the current user with admin privileges.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current admin user
        
    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

def verify_refresh_token(refresh_token: str, db: Session) -> User:
    """
    Verify a refresh token and return the associated user.
    
    Args:
        refresh_token: JWT refresh token
        db: Database session
        
    Returns:
        User: User associated with the refresh token
        
    Raises:
        HTTPException: If token verification fails
    """
    try:
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        token_type = payload.get("token_type")
        
        if user_id is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
            
        user = db.query(User).filter(User.id == int(user_id)).first()
        
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
            
        return user
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

def user_to_model(user: User) -> UserModel:
    """
    Convert a database User to a Pydantic User model.
    
    Args:
        user: Database User object
        
    Returns:
        UserModel: Pydantic User model
    """
    return UserModel(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin
    )
