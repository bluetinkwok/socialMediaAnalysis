"""
Data Retention Module

This module provides utilities for managing data retention policies.
"""

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from db.privacy_models import DataRetentionPolicy
from db.database import SessionLocal

logger = logging.getLogger(__name__)


def get_retention_policy(data_type: str, db: Optional[Session] = None) -> Optional[DataRetentionPolicy]:
    """
    Get the retention policy for a specific data type.
    
    Args:
        data_type: Type of data (e.g., "user_data", "analytics_data")
        db: Database session (creates a new one if not provided)
        
    Returns:
        DataRetentionPolicy object or None if not found
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        policy = db.query(DataRetentionPolicy).filter_by(data_type=data_type).first()
        return policy
    except Exception as e:
        logger.error(f"Failed to get retention policy for {data_type}: {str(e)}")
        return None
    finally:
        if close_session:
            db.close()


def apply_retention_policy(
    data_type: str, 
    db: Optional[Session] = None,
    simulate: bool = False
) -> Dict[str, Any]:
    """
    Apply a retention policy to delete expired data.
    
    Args:
        data_type: Type of data (e.g., "user_data", "analytics_data")
        db: Database session (creates a new one if not provided)
        simulate: If True, only simulates deletion without actually deleting data
        
    Returns:
        Dictionary with results:
        {
            "data_type": Data type,
            "retention_days": Retention period in days,
            "cutoff_date": Cutoff date for deletion,
            "deleted_count": Number of records deleted,
            "success": Whether the operation was successful
        }
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    result = {
        "data_type": data_type,
        "retention_days": None,
        "cutoff_date": None,
        "deleted_count": 0,
        "success": False
    }
    
    try:
        # Get the retention policy
        policy = get_retention_policy(data_type, db)
        if not policy:
            logger.warning(f"No retention policy found for {data_type}")
            return result
        
        # Calculate cutoff date
        retention_days = policy.retention_period_days
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        result["retention_days"] = retention_days
        result["cutoff_date"] = cutoff_date.isoformat()
        
        # Apply policy based on data type
        if data_type == "user_data":
            count = _apply_user_data_retention(db, cutoff_date, simulate)
        elif data_type == "analytics_data":
            count = _apply_analytics_data_retention(db, cutoff_date, simulate)
        elif data_type == "log_data":
            count = _apply_log_data_retention(db, cutoff_date, simulate)
        elif data_type == "temporary_files":
            count = _apply_temporary_files_retention(cutoff_date, simulate)
        elif data_type == "marketing_data":
            count = _apply_marketing_data_retention(db, cutoff_date, simulate)
        else:
            logger.warning(f"Unknown data type for retention: {data_type}")
            count = 0
        
        result["deleted_count"] = count
        result["success"] = True
        
        if not simulate:
            db.commit()
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to apply retention policy for {data_type}: {str(e)}")
        if not simulate:
            db.rollback()
        result["error"] = str(e)
        return result
    finally:
        if close_session:
            db.close()


def apply_all_retention_policies(db: Optional[Session] = None, simulate: bool = False) -> List[Dict[str, Any]]:
    """
    Apply all retention policies.
    
    Args:
        db: Database session (creates a new one if not provided)
        simulate: If True, only simulates deletion without actually deleting data
        
    Returns:
        List of results for each policy
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    results = []
    
    try:
        # Get all retention policies
        policies = db.query(DataRetentionPolicy).all()
        
        for policy in policies:
            result = apply_retention_policy(policy.data_type, db, simulate)
            results.append(result)
        
        return results
    except Exception as e:
        logger.error(f"Failed to apply all retention policies: {str(e)}")
        return results
    finally:
        if close_session:
            db.close()


def _apply_user_data_retention(db: Session, cutoff_date: datetime, simulate: bool = False) -> int:
    """
    Apply retention policy to user data.
    
    Args:
        db: Database session
        cutoff_date: Date before which data should be deleted
        simulate: If True, only simulates deletion
        
    Returns:
        Number of records that would be/were deleted
    """
    # This would delete user data older than the cutoff date
    # In a real application, we might anonymize instead of delete
    if simulate:
        # Count users that would be deleted
        count = db.execute(
            text("SELECT COUNT(*) FROM users WHERE created_at < :cutoff AND deletion_requested_at IS NOT NULL"),
            {"cutoff": cutoff_date}
        ).scalar() or 0
    else:
        # Actually delete users
        # Note: In a real application, this would be more complex with proper anonymization
        count = db.execute(
            text("DELETE FROM users WHERE created_at < :cutoff AND deletion_requested_at IS NOT NULL"),
            {"cutoff": cutoff_date}
        ).rowcount
    
    action = "Would delete" if simulate else "Deleted"
    logger.info(f"{action} {count} user records older than {cutoff_date}")
    return count


def _apply_analytics_data_retention(db: Session, cutoff_date: datetime, simulate: bool = False) -> int:
    """
    Apply retention policy to analytics data.
    
    Args:
        db: Database session
        cutoff_date: Date before which data should be deleted
        simulate: If True, only simulates deletion
        
    Returns:
        Number of records that would be/were deleted
    """
    if simulate:
        # Count analytics records that would be deleted
        count = db.execute(
            text("SELECT COUNT(*) FROM analytics_data WHERE created_at < :cutoff"),
            {"cutoff": cutoff_date}
        ).scalar() or 0
    else:
        # Actually delete analytics data
        count = db.execute(
            text("DELETE FROM analytics_data WHERE created_at < :cutoff"),
            {"cutoff": cutoff_date}
        ).rowcount
    
    action = "Would delete" if simulate else "Deleted"
    logger.info(f"{action} {count} analytics records older than {cutoff_date}")
    return count


def _apply_log_data_retention(db: Session, cutoff_date: datetime, simulate: bool = False) -> int:
    """
    Apply retention policy to log data.
    
    Args:
        db: Database session
        cutoff_date: Date before which data should be deleted
        simulate: If True, only simulates deletion
        
    Returns:
        Number of records that would be/were deleted
    """
    # For system logs stored in database
    tables = ["data_processing_logs", "data_breach_logs"]
    total_count = 0
    
    for table in tables:
        if simulate:
            # Count log records that would be deleted
            count = db.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE timestamp < :cutoff"),
                {"cutoff": cutoff_date}
            ).scalar() or 0
        else:
            # Actually delete log data
            count = db.execute(
                text(f"DELETE FROM {table} WHERE timestamp < :cutoff"),
                {"cutoff": cutoff_date}
            ).rowcount
        
        total_count += count
    
    # For file-based logs
    log_dir = Path("logs")
    if log_dir.exists():
        for log_file in log_dir.glob("*.log*"):
            # Check file modification time
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff_date:
                if not simulate:
                    try:
                        log_file.unlink()
                        logger.info(f"Deleted log file: {log_file}")
                        total_count += 1
                    except Exception as e:
                        logger.error(f"Failed to delete log file {log_file}: {str(e)}")
                else:
                    logger.info(f"Would delete log file: {log_file}")
                    total_count += 1
    
    action = "Would delete" if simulate else "Deleted"
    logger.info(f"{action} {total_count} log records older than {cutoff_date}")
    return total_count


def _apply_temporary_files_retention(cutoff_date: datetime, simulate: bool = False) -> int:
    """
    Apply retention policy to temporary files.
    
    Args:
        cutoff_date: Date before which files should be deleted
        simulate: If True, only simulates deletion
        
    Returns:
        Number of files that would be/were deleted
    """
    temp_dirs = ["uploads/temp", "tmp", "cache"]
    total_count = 0
    
    for temp_dir_path in temp_dirs:
        temp_dir = Path(temp_dir_path)
        if not temp_dir.exists():
            continue
        
        for file_path in temp_dir.glob("**/*"):
            if file_path.is_file():
                # Check file modification time
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime < cutoff_date:
                    if not simulate:
                        try:
                            file_path.unlink()
                            logger.info(f"Deleted temporary file: {file_path}")
                            total_count += 1
                        except Exception as e:
                            logger.error(f"Failed to delete temporary file {file_path}: {str(e)}")
                    else:
                        logger.info(f"Would delete temporary file: {file_path}")
                        total_count += 1
    
    action = "Would delete" if simulate else "Deleted"
    logger.info(f"{action} {total_count} temporary files older than {cutoff_date}")
    return total_count


def _apply_marketing_data_retention(db: Session, cutoff_date: datetime, simulate: bool = False) -> int:
    """
    Apply retention policy to marketing data.
    
    Args:
        db: Database session
        cutoff_date: Date before which data should be deleted
        simulate: If True, only simulates deletion
        
    Returns:
        Number of records that would be/were deleted
    """
    # For marketing-related consents that have been withdrawn
    if simulate:
        # Count marketing consents that would be deleted
        count = db.execute(
            text("SELECT COUNT(*) FROM user_consents WHERE consent_type = 'MARKETING' AND granted = 0 AND timestamp < :cutoff"),
            {"cutoff": cutoff_date}
        ).scalar() or 0
    else:
        # Actually delete marketing consents
        count = db.execute(
            text("DELETE FROM user_consents WHERE consent_type = 'MARKETING' AND granted = 0 AND timestamp < :cutoff"),
            {"cutoff": cutoff_date}
        ).rowcount
    
    action = "Would delete" if simulate else "Deleted"
    logger.info(f"{action} {count} marketing consent records older than {cutoff_date}")
    return count 