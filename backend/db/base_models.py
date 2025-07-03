"""
Base models for SQLAlchemy

This module defines the Base class for SQLAlchemy models and other shared components.
"""

from sqlalchemy.ext.declarative import declarative_base

# Create the Base class that all models will inherit from
Base = declarative_base() 