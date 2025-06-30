"""
Data Retention Policies

This module provides utilities for managing data retention, deletion, and privacy controls.
"""

import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from sqlalchemy import and_, or_, func, select, delete
from sqlalchemy.orm import Session

from core.config import get_settings
from db.database import get_db

logger = logging.getLogger(__name__)
settings = get_settings()

# Constants
DEFAULT_RETENTION_DAYS = 365  # Default retention period (1 year)
RETENTION_POLICY_CONFIG = {
    "user_data": 365 * 2,  # 2 years for user data
    "analytics_data": 90,   # 90 days for analytics data
    "log_data": 30,         # 30 days for logs
    "temporary_files": 7,   # 7 days for temporary files
}


class DataRetentionError(Exception):
    """Exception for data retention errors."""
    pass


class DataRetentionService:
    """
    Service for managing data retention policies and data deletion.
    """
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize the data retention service.
        
        Args:
            db: Database session (optional)
        """
        self.db = db
    
    def apply_retention_policy(
        self, 
        model_class: type, 
        policy_type: str = "user_data", 
        date_column: str = "created_at",
        extra_conditions: Optional[List] = None
    ) -> int:
        """
        Apply retention policy to a database model.
        
        Args:
            model_class: SQLAlchemy model class
            policy_type: Type of retention policy to apply
            date_column: Name of the date column to check
            extra_conditions: Additional conditions for the query
            
        Returns:
            Number of records deleted
            
        Raises:
            DataRetentionError: If policy application fails
        """
        try:
            # Get retention period
            retention_days = RETENTION_POLICY_CONFIG.get(policy_type, DEFAULT_RETENTION_DAYS)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            # Prepare conditions
            conditions = [getattr(model_class, date_column) < cutoff_date]
            if extra_conditions:
                conditions.extend(extra_conditions)
            
            # Use provided DB session or get a new one
            db_to_use = self.db or next(get_db())
            try:
                # Count records to be deleted
                count_query = select(func.count()).select_from(model_class).where(and_(*conditions))
                count = db_to_use.execute(count_query).scalar() or 0
                
                if count > 0:
                    # Delete records
                    delete_query = delete(model_class).where(and_(*conditions))
                    db_to_use.execute(delete_query)
                    
                    if not self.db:  # Only commit if we created the session
                        db_to_use.commit()
                    
                    logger.info(f"Applied {policy_type} retention policy to {model_class.__name__}: deleted {count} records")
                    return count
                
                return 0
                
            finally:
                if not self.db:  # Only close if we created the session
                    db_to_use.close()
                    
        except Exception as e:
            logger.error(f"Failed to apply retention policy to {model_class.__name__}: {str(e)}")
            raise DataRetentionError(f"Failed to apply retention policy: {str(e)}")
    
    def delete_expired_files(
        self, 
        directory: Union[str, Path], 
        policy_type: str = "temporary_files",
        file_pattern: str = "*",
        recursive: bool = False
    ) -> int:
        """
        Delete expired files from a directory.
        
        Args:
            directory: Directory to clean up
            policy_type: Type of retention policy to apply
            file_pattern: Pattern for matching files
            recursive: Whether to search recursively
            
        Returns:
            Number of files deleted
            
        Raises:
            DataRetentionError: If file deletion fails
        """
        try:
            directory = Path(directory)
            if not directory.exists():
                logger.warning(f"Directory does not exist: {directory}")
                return 0
            
            # Get retention period
            retention_days = RETENTION_POLICY_CONFIG.get(policy_type, DEFAULT_RETENTION_DAYS)
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=retention_days)
            cutoff_timestamp = cutoff_time.timestamp()
            
            # Find and delete expired files
            deleted_count = 0
            
            if recursive:
                # Recursive search
                for path in directory.rglob(file_pattern):
                    if path.is_file() and path.stat().st_mtime < cutoff_timestamp:
                        path.unlink()
                        deleted_count += 1
            else:
                # Non-recursive search
                for path in directory.glob(file_pattern):
                    if path.is_file() and path.stat().st_mtime < cutoff_timestamp:
                        path.unlink()
                        deleted_count += 1
            
            logger.info(f"Deleted {deleted_count} expired files from {directory}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete expired files from {directory}: {str(e)}")
            raise DataRetentionError(f"Failed to delete expired files: {str(e)}")
    
    def anonymize_user_data(self, user_id: int, db: Optional[Session] = None) -> bool:
        """
        Anonymize user data for GDPR/CCPA compliance.
        
        Args:
            user_id: ID of the user to anonymize
            db: Database session (optional)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            DataRetentionError: If anonymization fails
        """
        try:
            # Use provided DB session or get a new one
            db_to_use = db or self.db or next(get_db())
            try:
                # Get the user
                from models.user import User
                user = db_to_use.query(User).filter(User.id == user_id).first()
                
                if not user:
                    logger.warning(f"User not found for anonymization: {user_id}")
                    return False
                
                # Anonymize user data
                user.email = f"anonymized_{user_id}@deleted.user"
                user.full_name = f"Anonymized User {user_id}"
                user.is_active = False
                user.anonymized = True
                user.anonymized_at = datetime.now(timezone.utc)
                
                # Additional anonymization logic can be added here
                # For example, anonymizing related data, etc.
                
                if not (db or self.db):  # Only commit if we created the session
                    db_to_use.commit()
                
                logger.info(f"Anonymized user data: {user_id}")
                return True
                
            finally:
                if not (db or self.db):  # Only close if we created the session
                    db_to_use.close()
                    
        except Exception as e:
            logger.error(f"Failed to anonymize user data: {str(e)}")
            raise DataRetentionError(f"Failed to anonymize user data: {str(e)}")
    
    def delete_user_data(self, user_id: int, db: Optional[Session] = None) -> bool:
        """
        Delete all user data for GDPR/CCPA compliance.
        
        Args:
            user_id: ID of the user to delete data for
            db: Database session (optional)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            DataRetentionError: If deletion fails
        """
        try:
            # Use provided DB session or get a new one
            db_to_use = db or self.db or next(get_db())
            try:
                # Delete user-related data from various tables
                # This is a simplified example, you would need to add all relevant tables
                
                # Delete user's files
                from models.file import File
                db_to_use.query(File).filter(File.user_id == user_id).delete()
                
                # Delete user's analyses
                from models.analysis import Analysis
                db_to_use.query(Analysis).filter(Analysis.user_id == user_id).delete()
                
                # Delete user's reports
                from models.report import Report
                db_to_use.query(Report).filter(Report.user_id == user_id).delete()
                
                # Finally, delete the user
                from models.user import User
                db_to_use.query(User).filter(User.id == user_id).delete()
                
                if not (db or self.db):  # Only commit if we created the session
                    db_to_use.commit()
                
                logger.info(f"Deleted all data for user: {user_id}")
                return True
                
            finally:
                if not (db or self.db):  # Only close if we created the session
                    db_to_use.close()
                    
        except Exception as e:
            logger.error(f"Failed to delete user data: {str(e)}")
            raise DataRetentionError(f"Failed to delete user data: {str(e)}")
    
    def export_user_data(self, user_id: int, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Export all user data for GDPR/CCPA compliance.
        
        Args:
            user_id: ID of the user to export data for
            db: Database session (optional)
            
        Returns:
            Dictionary containing all user data
            
        Raises:
            DataRetentionError: If export fails
        """
        try:
            # Use provided DB session or get a new one
            db_to_use = db or self.db or next(get_db())
            try:
                # Get user data
                from models.user import User
                user = db_to_use.query(User).filter(User.id == user_id).first()
                
                if not user:
                    logger.warning(f"User not found for data export: {user_id}")
                    return {}
                
                # Create export data structure
                export_data = {
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "full_name": user.full_name,
                        "created_at": user.created_at.isoformat() if user.created_at else None,
                        "is_active": user.is_active,
                        "is_superuser": user.is_superuser,
                    },
                    "files": [],
                    "analyses": [],
                    "reports": [],
                    "export_date": datetime.now(timezone.utc).isoformat(),
                }
                
                # Get user's files
                from models.file import File
                files = db_to_use.query(File).filter(File.user_id == user_id).all()
                for file in files:
                    export_data["files"].append({
                        "id": file.id,
                        "filename": file.filename,
                        "content_type": file.content_type,
                        "created_at": file.created_at.isoformat() if file.created_at else None,
                    })
                
                # Get user's analyses
                from models.analysis import Analysis
                analyses = db_to_use.query(Analysis).filter(Analysis.user_id == user_id).all()
                for analysis in analyses:
                    export_data["analyses"].append({
                        "id": analysis.id,
                        "title": analysis.title,
                        "description": analysis.description,
                        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                    })
                
                # Get user's reports
                from models.report import Report
                reports = db_to_use.query(Report).filter(Report.user_id == user_id).all()
                for report in reports:
                    export_data["reports"].append({
                        "id": report.id,
                        "title": report.title,
                        "created_at": report.created_at.isoformat() if report.created_at else None,
                    })
                
                logger.info(f"Exported data for user: {user_id}")
                return export_data
                
            finally:
                if not (db or self.db):  # Only close if we created the session
                    db_to_use.close()
                    
        except Exception as e:
            logger.error(f"Failed to export user data: {str(e)}")
            raise DataRetentionError(f"Failed to export user data: {str(e)}")


# Create global instance
data_retention_service = DataRetentionService()


def apply_retention_policy(
    model_class: type, 
    policy_type: str = "user_data", 
    date_column: str = "created_at",
    extra_conditions: Optional[List] = None
) -> int:
    """
    Apply retention policy to a database model.
    
    Args:
        model_class: SQLAlchemy model class
        policy_type: Type of retention policy to apply
        date_column: Name of the date column to check
        extra_conditions: Additional conditions for the query
        
    Returns:
        Number of records deleted
    """
    return data_retention_service.apply_retention_policy(
        model_class, policy_type, date_column, extra_conditions
    )


def delete_expired_files(
    directory: Union[str, Path], 
    policy_type: str = "temporary_files",
    file_pattern: str = "*",
    recursive: bool = False
) -> int:
    """
    Delete expired files from a directory.
    
    Args:
        directory: Directory to clean up
        policy_type: Type of retention policy to apply
        file_pattern: Pattern for matching files
        recursive: Whether to search recursively
        
    Returns:
        Number of files deleted
    """
    return data_retention_service.delete_expired_files(
        directory, policy_type, file_pattern, recursive
    )


def anonymize_user_data(user_id: int, db: Optional[Session] = None) -> bool:
    """
    Anonymize user data for GDPR/CCPA compliance.
    
    Args:
        user_id: ID of the user to anonymize
        db: Database session (optional)
        
    Returns:
        True if successful, False otherwise
    """
    return data_retention_service.anonymize_user_data(user_id, db)


def delete_user_data(user_id: int, db: Optional[Session] = None) -> bool:
    """
    Delete all user data for GDPR/CCPA compliance.
    
    Args:
        user_id: ID of the user to delete data for
        db: Database session (optional)
        
    Returns:
        True if successful, False otherwise
    """
    return data_retention_service.delete_user_data(user_id, db)


def export_user_data(user_id: int, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Export all user data for GDPR/CCPA compliance.
    
    Args:
        user_id: ID of the user to export data for
        db: Database session (optional)
        
    Returns:
        Dictionary containing all user data
    """
    return data_retention_service.export_user_data(user_id, db) 