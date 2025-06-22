"""
Database configuration and session management for Social Media Analysis Platform
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
import logging

from .models import Base, Platform, PlatformType

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./social_media_analysis.db")

# Create SQLAlchemy engine
if DATABASE_URL.startswith("sqlite"):
    # SQLite specific configuration
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=os.getenv("DATABASE_ECHO", "false").lower() == "true"
    )
    
    # Enable foreign key constraints for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=1000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()
else:
    # PostgreSQL or other database configuration
    engine = create_engine(
        DATABASE_URL,
        echo=os.getenv("DATABASE_ECHO", "false").lower() == "true"
    )

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_database():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Initialize default platforms
        init_default_platforms()
        
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def init_default_platforms():
    """Initialize default platform configurations"""
    try:
        db = SessionLocal()
        
        # Check if platforms already exist
        existing_platforms = db.query(Platform).count()
        if existing_platforms > 0:
            logger.info("Platforms already initialized")
            db.close()
            return
        
        # Default platform configurations
        default_platforms = [
            {
                "name": "youtube",
                "display_name": "YouTube",
                "base_url": "https://www.youtube.com",
                "is_active": True
            },
            {
                "name": "instagram",
                "display_name": "Instagram",
                "base_url": "https://www.instagram.com",
                "is_active": True
            },
            {
                "name": "threads",
                "display_name": "Threads",
                "base_url": "https://www.threads.net",
                "is_active": True
            },
            {
                "name": "rednote",
                "display_name": "RedNote",
                "base_url": "https://www.xiaohongshu.com",
                "is_active": True
            }
        ]
        
        # Create platform records
        for platform_data in default_platforms:
            platform = Platform(**platform_data)
            db.add(platform)
        
        db.commit()
        logger.info("Default platforms initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing default platforms: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def get_database():
    """Get database session dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        db.close()


def reset_database():
    """Reset database - DROP all tables and recreate them"""
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped")
        
        create_database()
        logger.info("Database reset completed")
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        raise


def check_database_connection():
    """Check if database connection is working"""
    try:
        db = SessionLocal()
        # Try to execute a simple query
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def get_database_info():
    """Get database information"""
    try:
        db = SessionLocal()
        
        # Get table information
        tables = Base.metadata.tables.keys()
        
        # Get record counts
        info = {
            "database_url": DATABASE_URL,
            "tables": list(tables),
            "connection_status": "connected"
        }
        
        # Try to get record counts for main tables
        try:
            from .models import Post, MediaFile, DownloadJob, AnalyticsData
            
            info["record_counts"] = {
                "platforms": db.query(Platform).count(),
                "posts": db.query(Post).count(),
                "media_files": db.query(MediaFile).count(),
                "download_jobs": db.query(DownloadJob).count(),
                "analytics_data": db.query(AnalyticsData).count(),
            }
        except Exception as e:
            logger.warning(f"Could not get record counts: {e}")
            info["record_counts"] = {}
        
        db.close()
        return info
        
    except Exception as e:
        logger.error(f"Error getting database info: {e}")
        return {
            "database_url": DATABASE_URL,
            "connection_status": "failed",
            "error": str(e)
        }


# Database utility functions
def ensure_database_exists():
    """Ensure database and tables exist"""
    try:
        if not check_database_connection():
            logger.info("Database not accessible, creating...")
            create_database()
        else:
            # Check if tables exist
            db = SessionLocal()
            try:
                db.query(Platform).first()
                logger.info("Database tables exist and accessible")
            except Exception:
                logger.info("Database tables missing, creating...")
                create_database()
            finally:
                db.close()
                
    except Exception as e:
        logger.error(f"Error ensuring database exists: {e}")
        raise


# Export commonly used items
__all__ = [
    "engine",
    "SessionLocal", 
    "get_database",
    "get_db_session",
    "create_database",
    "reset_database",
    "check_database_connection",
    "get_database_info",
    "ensure_database_exists"
] 