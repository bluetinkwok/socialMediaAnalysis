"""
Session Management Module

This module provides functionality for secure session management, including timeout and 2FA.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
import pyotp
import secrets
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from core.auth import get_current_user
from db.database import get_database
from db.models import User, Role

# Constants
SESSION_TIMEOUT_MINUTES = 30  # Default session timeout
SESSION_STORE: Dict[str, Dict[str, Any]] = {}  # In-memory session store (replace with Redis in production)
TOTP_SECRET_LENGTH = 32  # Length of TOTP secret
TOTP_DIGITS = 6  # Number of digits in TOTP code
TOTP_INTERVAL = 30  # TOTP interval in seconds

class SessionManager:
    """
    Session management utility for handling session timeouts and 2FA.
    """
    
    @staticmethod
    def create_session(user_id: int, ip_address: str, user_agent: str) -> str:
        """
        Create a new session for a user.
        
        Args:
            user_id: User ID
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            str: Session ID
        """
        session_id = secrets.token_urlsafe(32)
        
        # Create session data
        SESSION_STORE[session_id] = {
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "is_2fa_verified": False,  # 2FA verification status
        }
        
        return session_id
    
    @staticmethod
    def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by session ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Optional[Dict[str, Any]]: Session data if found, None otherwise
        """
        return SESSION_STORE.get(session_id)
    
    @staticmethod
    def update_session_activity(session_id: str) -> bool:
        """
        Update session last activity timestamp.
        
        Args:
            session_id: Session ID
            
        Returns:
            bool: True if session was updated, False otherwise
        """
        session = SESSION_STORE.get(session_id)
        if session:
            session["last_activity"] = datetime.utcnow()
            return True
        return False
    
    @staticmethod
    def is_session_valid(session_id: str, timeout_minutes: int = SESSION_TIMEOUT_MINUTES) -> bool:
        """
        Check if a session is valid and not timed out.
        
        Args:
            session_id: Session ID
            timeout_minutes: Session timeout in minutes
            
        Returns:
            bool: True if session is valid, False otherwise
        """
        session = SESSION_STORE.get(session_id)
        if not session:
            return False
        
        # Check if session has timed out
        last_activity = session["last_activity"]
        timeout = timedelta(minutes=timeout_minutes)
        
        return datetime.utcnow() - last_activity <= timeout
    
    @staticmethod
    def invalidate_session(session_id: str) -> bool:
        """
        Invalidate a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            bool: True if session was invalidated, False otherwise
        """
        if session_id in SESSION_STORE:
            del SESSION_STORE[session_id]
            return True
        return False
    
    @staticmethod
    def invalidate_user_sessions(user_id: int) -> int:
        """
        Invalidate all sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            int: Number of sessions invalidated
        """
        session_ids = [
            sid for sid, data in SESSION_STORE.items()
            if data.get("user_id") == user_id
        ]
        
        for session_id in session_ids:
            SessionManager.invalidate_session(session_id)
        
        return len(session_ids)
    
    @staticmethod
    def cleanup_expired_sessions(timeout_minutes: int = SESSION_TIMEOUT_MINUTES) -> int:
        """
        Clean up expired sessions.
        
        Args:
            timeout_minutes: Session timeout in minutes
            
        Returns:
            int: Number of sessions cleaned up
        """
        now = datetime.utcnow()
        timeout = timedelta(minutes=timeout_minutes)
        
        expired_sessions = [
            sid for sid, data in SESSION_STORE.items()
            if now - data["last_activity"] > timeout
        ]
        
        for session_id in expired_sessions:
            SessionManager.invalidate_session(session_id)
        
        return len(expired_sessions)
    
    @staticmethod
    def set_2fa_verified(session_id: str, verified: bool = True) -> bool:
        """
        Set 2FA verification status for a session.
        
        Args:
            session_id: Session ID
            verified: Verification status
            
        Returns:
            bool: True if session was updated, False otherwise
        """
        session = SESSION_STORE.get(session_id)
        if session:
            session["is_2fa_verified"] = verified
            return True
        return False
    
    @staticmethod
    def is_2fa_verified(session_id: str) -> bool:
        """
        Check if 2FA is verified for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            bool: True if 2FA is verified, False otherwise
        """
        session = SESSION_STORE.get(session_id)
        return session and session.get("is_2fa_verified", False)


class TwoFactorAuth:
    """
    Two-factor authentication utility using TOTP.
    """
    
    @staticmethod
    def generate_secret() -> str:
        """
        Generate a new TOTP secret.
        
        Returns:
            str: Base32 encoded secret
        """
        return pyotp.random_base32()
    
    @staticmethod
    def get_totp_uri(secret: str, username: str, issuer: str = "SocialMediaAnalysis") -> str:
        """
        Get TOTP URI for QR code generation.
        
        Args:
            secret: TOTP secret
            username: Username
            issuer: Issuer name
            
        Returns:
            str: TOTP URI
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=username, issuer_name=issuer)
    
    @staticmethod
    def verify_totp(secret: str, code: str) -> bool:
        """
        Verify a TOTP code.
        
        Args:
            secret: TOTP secret
            code: TOTP code
            
        Returns:
            bool: True if code is valid, False otherwise
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(code)


async def get_session_from_request(
    request: Request,
    db: Session = Depends(get_database)
) -> Dict[str, Any]:
    """
    Get session data from request.
    
    Args:
        request: FastAPI request
        db: Database session
        
    Returns:
        Dict[str, Any]: Session data
        
    Raises:
        HTTPException: If session is not found or invalid
    """
    # Get session ID from cookie or header
    session_id = request.cookies.get("session_id") or request.headers.get("X-Session-ID")
    
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session ID not found"
        )
    
    # Get session data
    session = SessionManager.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found"
        )
    
    # Check if session is valid
    if not SessionManager.is_session_valid(session_id):
        SessionManager.invalidate_session(session_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired"
        )
    
    # Update session activity
    SessionManager.update_session_activity(session_id)
    
    return session


async def require_2fa(
    session: Dict[str, Any] = Depends(get_session_from_request),
) -> Dict[str, Any]:
    """
    Require 2FA verification for a session.
    
    Args:
        session: Session data
        
    Returns:
        Dict[str, Any]: Session data
        
    Raises:
        HTTPException: If 2FA is not verified
    """
    if not session.get("is_2fa_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="2FA verification required"
        )
    
    return session 