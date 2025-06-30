#!/usr/bin/env python3
"""
Run Database Migrations

This script runs all database migrations in the correct order.
"""

import argparse
import importlib.util
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

# Migration scripts in order of execution
MIGRATIONS = [
    "add_encryption_and_privacy.py",
    # Add more migration scripts here as they are created
]


def run_migration(migration_file: str) -> bool:
    """
    Run a specific migration script.
    
    Args:
        migration_file: Name of the migration file
        
    Returns:
        True if migration was successful, False otherwise
    """
    try:
        migration_path = Path(__file__).parent.parent / "migrations" / migration_file
        
        if not migration_path.exists():
            logger.error(f"Migration file not found: {migration_path}")
            return False
        
        logger.info(f"Running migration: {migration_file}")
        
        # Load the migration module
        spec = importlib.util.spec_from_file_location("migration", migration_path)
        migration_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration_module)
        
        # Run the migration
        if hasattr(migration_module, "run_migration"):
            result = migration_module.run_migration()
            
            if result:
                logger.info(f"Migration {migration_file} completed successfully")
                return True
            else:
                logger.error(f"Migration {migration_file} failed")
                return False
        else:
            logger.error(f"Migration {migration_file} does not have a run_migration function")
            return False
            
    except Exception as e:
        logger.error(f"Error running migration {migration_file}: {str(e)}")
        return False


def run_migrations(specific_migration: str = None) -> bool:
    """
    Run all migrations or a specific one.
    
    Args:
        specific_migration: Name of a specific migration to run (optional)
        
    Returns:
        True if all migrations were successful, False otherwise
    """
    if specific_migration:
        return run_migration(specific_migration)
    
    # Run all migrations in order
    for migration in MIGRATIONS:
        if not run_migration(migration):
            return False
    
    return True


if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument(
        "--migration", "-m",
        help="Run a specific migration file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run migrations
    success = run_migrations(args.migration)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1) 