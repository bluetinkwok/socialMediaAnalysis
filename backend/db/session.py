"""
Database session management for Social Media Analysis Platform
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator

from backend.core.config import settings

# Create the SQLAlchemy engine
engine = create_engine(settings.DATABASE_URL)

# Create a sessionmaker factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator:
    """
    Get a database session.
    
    Yields:
        SQLAlchemy Session: A database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
