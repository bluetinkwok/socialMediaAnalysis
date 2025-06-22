#!/usr/bin/env python3
"""
Database initialization script for Social Media Analysis Platform

This script creates the database tables and initializes default data.
"""

import sys
import os
import logging
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from db.database import (
    create_database, 
    check_database_connection, 
    get_database_info,
    reset_database,
    ensure_database_exists
)
from db.models import Base, Platform, PlatformType
from db.schemas import PlatformCreate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to initialize the database"""
    print("🚀 Social Media Analysis Platform - Database Initialization")
    print("=" * 60)
    
    try:
        # Check if database exists and is accessible
        print("📊 Checking database connection...")
        if check_database_connection():
            print("✅ Database connection successful")
            
            # Get current database info
            db_info = get_database_info()
            print(f"📈 Database URL: {db_info.get('database_url', 'Unknown')}")
            print(f"📊 Tables: {', '.join(db_info.get('tables', []))}")
            
            if db_info.get('record_counts'):
                print("📋 Current record counts:")
                for table, count in db_info['record_counts'].items():
                    print(f"  - {table}: {count}")
            
            # Ask if user wants to reset
            reset_choice = input("\n🔄 Do you want to reset the database? (y/N): ").lower()
            if reset_choice in ['y', 'yes']:
                print("🗑️  Resetting database...")
                reset_database()
                print("✅ Database reset completed")
            else:
                print("📦 Ensuring database is up to date...")
                ensure_database_exists()
                print("✅ Database verification completed")
        else:
            print("❌ Database connection failed, creating new database...")
            create_database()
            print("✅ Database created successfully")
        
        # Verify the final state
        print("\n🔍 Final verification...")
        final_info = get_database_info()
        
        if final_info.get('connection_status') == 'connected':
            print("✅ Database is ready!")
            print(f"📊 Total tables: {len(final_info.get('tables', []))}")
            
            if final_info.get('record_counts'):
                print("📋 Final record counts:")
                for table, count in final_info['record_counts'].items():
                    print(f"  - {table}: {count}")
            
            print("\n🎉 Database initialization completed successfully!")
            print("\n💡 You can now start the FastAPI server with:")
            print("   uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
            
        else:
            print("❌ Database verification failed")
            print(f"Error: {final_info.get('error', 'Unknown error')}")
            return 1
            
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        print(f"❌ Error: {e}")
        return 1
    
    return 0


def verify_schema():
    """Verify that all expected tables exist"""
    expected_tables = [
        'platforms',
        'posts', 
        'media_files',
        'download_jobs',
        'analytics_data',
        'trend_data',
        'user_sessions'
    ]
    
    try:
        db_info = get_database_info()
        existing_tables = db_info.get('tables', [])
        
        print("\n🔍 Schema verification:")
        all_good = True
        
        for table in expected_tables:
            if table in existing_tables:
                print(f"  ✅ {table}")
            else:
                print(f"  ❌ {table} (missing)")
                all_good = False
        
        if all_good:
            print("✅ All expected tables exist")
        else:
            print("❌ Some tables are missing")
            
        return all_good
        
    except Exception as e:
        logger.error(f"Schema verification failed: {e}")
        return False


def show_help():
    """Show help information"""
    print("Database Initialization Script")
    print("Usage: python scripts/init_db.py [options]")
    print("\nOptions:")
    print("  --help, -h     Show this help message")
    print("  --reset        Reset the database (drop and recreate all tables)")
    print("  --verify       Verify the database schema only")
    print("  --info         Show database information only")


if __name__ == "__main__":
    # Parse command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg in ['--help', '-h']:
            show_help()
            sys.exit(0)
        elif arg == '--reset':
            print("🔄 Resetting database...")
            try:
                reset_database()
                print("✅ Database reset completed")
                verify_schema()
            except Exception as e:
                print(f"❌ Reset failed: {e}")
                sys.exit(1)
        elif arg == '--verify':
            print("🔍 Verifying database schema...")
            if verify_schema():
                print("✅ Schema verification passed")
            else:
                print("❌ Schema verification failed")
                sys.exit(1)
        elif arg == '--info':
            print("📊 Database information:")
            info = get_database_info()
            print(f"URL: {info.get('database_url')}")
            print(f"Status: {info.get('connection_status')}")
            print(f"Tables: {', '.join(info.get('tables', []))}")
            if info.get('record_counts'):
                print("Record counts:")
                for table, count in info['record_counts'].items():
                    print(f"  {table}: {count}")
        else:
            print(f"Unknown option: {arg}")
            show_help()
            sys.exit(1)
    else:
        # Run main initialization
        sys.exit(main()) 