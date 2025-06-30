"""
Password Utilities

This module provides utilities for password hashing, verification, and generation.
"""

import secrets
import string
from passlib.context import CryptContext
import re
from typing import Tuple, List, Optional

# Password context for hashing and verification
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Common password patterns to check against
COMMON_PATTERNS = [
    "password", "123456", "qwerty", "admin", "welcome", 
    "letmein", "abc123", "monkey", "1234", "12345"
]

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)

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

def check_password_strength(password: str) -> Tuple[bool, List[str]]:
    """
    Check password strength against various criteria.
    
    Args:
        password: Password to check
        
    Returns:
        Tuple[bool, List[str]]: (is_strong, list_of_issues)
    """
    issues = []
    
    # Check minimum length
    if len(password) < 8:
        issues.append("Password must be at least 8 characters")
    
    # Check for uppercase letter
    if not re.search(r'[A-Z]', password):
        issues.append("Password must contain an uppercase letter")
    
    # Check for lowercase letter
    if not re.search(r'[a-z]', password):
        issues.append("Password must contain a lowercase letter")
    
    # Check for digit
    if not re.search(r'[0-9]', password):
        issues.append("Password must contain a digit")
    
    # Check for special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        issues.append("Password must contain a special character")
    
    # Check for common patterns
    password_lower = password.lower()
    for pattern in COMMON_PATTERNS:
        if pattern in password_lower:
            issues.append(f"Password contains a common pattern: {pattern}")
            break
    
    # Check for repeating characters (more than 3 in a row)
    if re.search(r'(.)\1{3,}', password):
        issues.append("Password contains too many repeating characters")
    
    # Check for sequential characters
    if any(seq in password_lower for seq in ['1234', 'abcd', 'qwerty', 'asdf']):
        issues.append("Password contains sequential characters")
    
    return (len(issues) == 0, issues)

def generate_password(length: int = 16, include_special: bool = True) -> str:
    """
    Generate a secure random password.
    
    Args:
        length: Length of the password (default: 16)
        include_special: Whether to include special characters (default: True)
        
    Returns:
        str: Secure random password
    """
    if length < 8:
        length = 8  # Minimum length for security
    
    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = string.punctuation if include_special else ""
    
    # Ensure at least one of each required character type
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits)
    ]
    
    if include_special:
        password.append(secrets.choice(special))
    
    # Fill the rest with random characters
    all_chars = lowercase + uppercase + digits + special
    password.extend(secrets.choice(all_chars) for _ in range(length - len(password)))
    
    # Shuffle the password
    secrets.SystemRandom().shuffle(password)
    
    return ''.join(password)

def get_password_reset_token() -> str:
    """
    Generate a secure token for password reset.
    
    Returns:
        str: Secure token
    """
    return secrets.token_urlsafe(32)

def is_password_compromised(password: str, api_client=None) -> Tuple[bool, Optional[int]]:
    """
    Check if a password has been compromised using the HaveIBeenPwned API.
    This uses k-anonymity to check without sending the full password.
    
    Args:
        password: Password to check
        api_client: Optional API client for testing
        
    Returns:
        Tuple[bool, Optional[int]]: (is_compromised, count_if_compromised)
    """
    # Note: In a real implementation, you would use a library like 'pwnedpasswords'
    # or implement the k-anonymity API call to HaveIBeenPwned
    # For now, we'll just return a placeholder
    
    # Placeholder implementation
    return (False, None) 