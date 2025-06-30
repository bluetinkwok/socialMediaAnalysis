"""
User Models

This module defines user-related models.
"""

from typing import Optional, List
from pydantic import BaseModel, EmailStr, validator, Field
import re

# Common password patterns to check against
COMMON_PATTERNS = [
    "password", "123456", "qwerty", "admin", "welcome", 
    "letmein", "abc123", "monkey", "1234", "12345"
]

class User(BaseModel):
    """Base user model"""
    id: int
    username: str
    email: EmailStr
    is_active: bool = True
    is_admin: bool = False
    role: str = "user"  # Added role field

class UserCreate(BaseModel):
    """Model for user creation"""
    username: str
    email: EmailStr
    password: str
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username must be alphanumeric')
        return v
    
    @validator('password')
    def password_strength(cls, v):
        # Check minimum length
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        
        # Check for uppercase letter
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain an uppercase letter')
        
        # Check for lowercase letter
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain a lowercase letter')
        
        # Check for digit
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain a digit')
        
        # Check for special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain a special character')
        
        # Check for common patterns
        v_lower = v.lower()
        for pattern in COMMON_PATTERNS:
            if pattern in v_lower:
                raise ValueError(f'Password contains a common pattern: {pattern}')
        
        # Check for repeating characters (more than 3 in a row)
        if re.search(r'(.)\1{3,}', v):
            raise ValueError('Password contains too many repeating characters')
        
        # Check for sequential characters
        if any(seq in v_lower for seq in ['1234', 'abcd', 'qwerty', 'asdf']):
            raise ValueError('Password contains sequential characters')
            
        return v

class UserUpdate(BaseModel):
    """Model for user updates"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if v is not None and not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username must be alphanumeric')
        return v
    
    @validator('password')
    def password_strength(cls, v):
        if v is None:
            return v
            
        # Check minimum length
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        
        # Check for uppercase letter
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain an uppercase letter')
        
        # Check for lowercase letter
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain a lowercase letter')
        
        # Check for digit
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain a digit')
        
        # Check for special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain a special character')
        
        # Check for common patterns
        v_lower = v.lower()
        for pattern in COMMON_PATTERNS:
            if pattern in v_lower:
                raise ValueError(f'Password contains a common pattern: {pattern}')
        
        # Check for repeating characters (more than 3 in a row)
        if re.search(r'(.)\1{3,}', v):
            raise ValueError('Password contains too many repeating characters')
        
        # Check for sequential characters
        if any(seq in v_lower for seq in ['1234', 'abcd', 'qwerty', 'asdf']):
            raise ValueError('Password contains sequential characters')
            
        return v

class UserInDB(User):
    """User model with hashed password for database storage"""
    hashed_password: str
