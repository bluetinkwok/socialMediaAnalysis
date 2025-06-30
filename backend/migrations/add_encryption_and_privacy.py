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

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, Enum, ForeignKey, MetaData, Table
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


def create_privacy_tables():
    """Create all privacy-related tables."""
    try:
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
        return True
    except Exception as e:
        logger.error(f"Failed to create privacy tables: {str(e)}")
        raise


def update_user_model():
    """Update the User model with privacy fields."""
    try:
        # Create a session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Add columns to users table if it exists
        try:
            # Check if users table exists
            metadata = MetaData()
            metadata.reflect(bind=engine, only=['users'])
            
            if 'users' in metadata.tables:
                users_table = metadata.tables['users']
                columns = users_table.columns.keys()
                
                # Add columns if they don't exist
                columns_to_add = {
                    "anonymized": "ALTER TABLE users ADD COLUMN anonymized BOOLEAN DEFAULT 0",
                    "anonymized_at": "ALTER TABLE users ADD COLUMN anonymized_at TIMESTAMP",
                    "data_export_requested_at": "ALTER TABLE users ADD COLUMN data_export_requested_at TIMESTAMP",
                    "data_export_completed_at": "ALTER TABLE users ADD COLUMN data_export_completed_at TIMESTAMP",
                    "deletion_requested_at": "ALTER TABLE users ADD COLUMN deletion_requested_at TIMESTAMP",
                    "processing_restricted": "ALTER TABLE users ADD COLUMN processing_restricted BOOLEAN DEFAULT 0",
                    "processing_restricted_at": "ALTER TABLE users ADD COLUMN processing_restricted_at TIMESTAMP"
                }
                
                for column_name, sql in columns_to_add.items():
                    if column_name not in columns:
                        session.execute(sql)
                        logger.info(f"Added '{column_name}' column to users table")
                
                logger.info("Successfully updated User model with privacy fields")
            else:
                logger.warning("Users table not found, skipping privacy columns")
        except Exception as e:
            logger.warning(f"Could not update users table: {str(e)}")
        
        session.commit()
        session.close()
        return True
    except Exception as e:
        logger.error(f"Failed to update User model: {str(e)}")
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
        return True
    except Exception as e:
        logger.error(f"Failed to create default data retention policies: {str(e)}")
        raise


def run_migration():
    """Run the migration to add encryption and privacy features."""
    try:
        logger.info("Starting encryption and privacy migration...")
        
        # Create privacy tables
        create_privacy_tables()
        
        # Update User model with privacy fields
        update_user_model()
        
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