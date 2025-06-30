"""
Permissions Module

This module defines permissions for different roles and provides functions to check permissions.
"""

from enum import Enum, auto
from typing import List, Dict, Set, Optional, Union
from fastapi import Depends, HTTPException, status
from pydantic import BaseModel

from db.models import User, Role

class Permission(str, Enum):
    """Permissions enum for fine-grained access control"""
    # User management permissions
    VIEW_USERS = "view_users"
    CREATE_USER = "create_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    
    # Content management permissions
    VIEW_CONTENT = "view_content"
    CREATE_CONTENT = "create_content"
    UPDATE_CONTENT = "update_content"
    DELETE_CONTENT = "delete_content"
    
    # Analytics permissions
    VIEW_ANALYTICS = "view_analytics"
    EXPORT_ANALYTICS = "export_analytics"
    
    # System permissions
    MANAGE_SYSTEM = "manage_system"
    VIEW_LOGS = "view_logs"
    
    # Security permissions
    MANAGE_SECURITY = "manage_security"
    VIEW_SECURITY_LOGS = "view_security_logs"
    RELEASE_QUARANTINE = "release_quarantine"

# Define role-based permissions
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        # Admin has all permissions
        Permission.VIEW_USERS,
        Permission.CREATE_USER,
        Permission.UPDATE_USER,
        Permission.DELETE_USER,
        Permission.VIEW_CONTENT,
        Permission.CREATE_CONTENT,
        Permission.UPDATE_CONTENT,
        Permission.DELETE_CONTENT,
        Permission.VIEW_ANALYTICS,
        Permission.EXPORT_ANALYTICS,
        Permission.MANAGE_SYSTEM,
        Permission.VIEW_LOGS,
        Permission.MANAGE_SECURITY,
        Permission.VIEW_SECURITY_LOGS,
        Permission.RELEASE_QUARANTINE,
    },
    Role.USER: {
        # Regular user permissions
        Permission.VIEW_CONTENT,
        Permission.CREATE_CONTENT,
        Permission.UPDATE_CONTENT,  # Can only update own content, enforced in handlers
        Permission.DELETE_CONTENT,   # Can only delete own content, enforced in handlers
        Permission.VIEW_ANALYTICS,
        Permission.EXPORT_ANALYTICS,
    },
    Role.VIEWER: {
        # Viewer permissions (read-only)
        Permission.VIEW_CONTENT,
        Permission.VIEW_ANALYTICS,
    }
}

class PermissionChecker:
    """Permission checking utility"""
    
    def __init__(self, required_permissions: List[Permission]):
        """
        Initialize permission checker.
        
        Args:
            required_permissions: List of required permissions
        """
        self.required_permissions = required_permissions
    
    def __call__(self, user: User) -> bool:
        """
        Check if user has all required permissions.
        
        Args:
            user: User to check permissions for
            
        Returns:
            bool: True if user has all required permissions
            
        Raises:
            HTTPException: If user doesn't have required permissions
        """
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Get user's role permissions
        user_permissions = ROLE_PERMISSIONS.get(user.role, set())
        
        # Check if user has all required permissions
        missing_permissions = [
            p for p in self.required_permissions if p not in user_permissions
        ]
        
        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(p.value for p in missing_permissions)}"
            )
        
        return True

def has_permission(permission: Permission):
    """
    Dependency for checking a single permission.
    
    Args:
        permission: Required permission
        
    Returns:
        Callable: Dependency function
    """
    checker = PermissionChecker([permission])
    
    def check_permission(user: User = Depends(get_current_user)):
        return checker(user)
    
    return check_permission

def has_permissions(permissions: List[Permission]):
    """
    Dependency for checking multiple permissions.
    
    Args:
        permissions: List of required permissions
        
    Returns:
        Callable: Dependency function
    """
    checker = PermissionChecker(permissions)
    
    def check_permissions(user: User = Depends(get_current_user)):
        return checker(user)
    
    return check_permissions

# Import at the end to avoid circular imports
from core.auth import get_current_user 