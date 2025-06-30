"""
Migration Script: Add Encryption and Privacy Models

This script adds tables and columns for encryption and privacy features.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func

from db.database import Base, engine, SessionLocal
from db.privacy_models import (
    UserConsent, ConsentType, DataSubjectRequest, DataSubjectRequestType,
    DataSubjectRequestStatus, DataProcessingLog, DataBreachLog, PrivacySettings,
    DataRetentionPolicy
)
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def add_privacy_columns_to_users():
    """Add privacy-related columns to the users table."""
    try:
        conn = engine.connect()
        
        # Check if columns already exist
        result = conn.execute("PRAGMA table_info(users)")
        columns = {row[1] for row in result.fetchall()}
        
        # Add columns if they don't exist
        if "anonymized" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN anonymized BOOLEAN DEFAULT 0")
            logger.info("Added 'anonymized' column to users table")
        
        if "anonymized_at" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN anonymized_at TIMESTAMP")
            logger.info("Added 'anonymized_at' column to users table")
        
        if "data_export_requested_at" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN data_export_requested_at TIMESTAMP")
            logger.info("Added 'data_export_requested_at' column to users table")
        
        if "data_export_completed_at" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN data_export_completed_at TIMESTAMP")
            logger.info("Added 'data_export_completed_at' column to users table")
        
        if "deletion_requested_at" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN deletion_requested_at TIMESTAMP")
            logger.info("Added 'deletion_requested_at' column to users table")
        
        if "processing_restricted" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN processing_restricted BOOLEAN DEFAULT 0")
            logger.info("Added 'processing_restricted' column to users table")
        
        if "processing_restricted_at" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN processing_restricted_at TIMESTAMP")
            logger.info("Added 'processing_restricted_at' column to users table")
        
        conn.close()
        logger.info("Successfully added privacy columns to users table")
        
    except Exception as e:
        logger.error(f"Failed to add privacy columns to users table: {str(e)}")
        raise


def create_default_retention_policies():
    """Create default data retention policies."""
    try:
        db = SessionLocal()
        
        # Define default policies
        default_policies = [
            {"data_type": "user_data", "retention_period_days": 730, "legal_basis": "Legitimate interest", 
             "description": "User account data including profile information"},
            {"data_type": "analytics_data", "retention_period_days": 90, "legal_basis": "Consent", 
             "description": "Analytics data about user behavior and content performance"},
            {"data_type": "log_data", "retention_period_days": 30, "legal_basis": "Legal obligation", 
             "description": "System and security logs"},
            {"data_type": "temporary_files", "retention_period_days": 7, "legal_basis": "Legitimate interest", 
             "description": "Temporary files created during processing"},
            {"data_type": "marketing_data", "retention_period_days": 365, "legal_basis": "Consent", 
             "description": "Marketing preferences and campaign data"},
        ]
        
        # Add policies if they don't exist
        for policy_data in default_policies:
            existing = db.query(DataRetentionPolicy).filter_by(data_type=policy_data["data_type"]).first()
            if not existing:
                policy = DataRetentionPolicy(**policy_data)
                db.add(policy)
                logger.info(f"Added data retention policy for {policy_data['data_type']}")
        
        db.commit()
        db.close()
        logger.info("Successfully created default data retention policies")
        
    except Exception as e:
        logger.error(f"Failed to create default data retention policies: {str(e)}")
        raise


def run_migration():
    """Run the migration to add encryption and privacy features."""
    try:
        logger.info("Starting encryption and privacy migration...")
        
        # Create all privacy-related tables
        Base.metadata.create_all(engine, tables=[
            UserConsent.__table__,
            DataSubjectRequest.__table__,
            DataProcessingLog.__table__,
            DataBreachLog.__table__,
            PrivacySettings.__table__,
            DataRetentionPolicy.__table__,
        ])
        logger.info("Created privacy tables")
        
        # Add privacy columns to users table
        add_privacy_columns_to_users()
        
        # Create default retention policies
        create_default_retention_policies()
        
        logger.info("Encryption and privacy migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    success = run_migration()
    sys.exit(0 if success else 1) 