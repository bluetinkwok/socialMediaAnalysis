"""
Audit Trail Models Module

This module defines database models for storing audit trail records.
It provides a comprehensive audit trail system to track all security-relevant
actions in the application.
"""

import datetime
import json
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from db.database import Base
from db.encrypted_fields import EncryptedJSON, EncryptedString


class AuditActionType(str, Enum):
    """Types of actions that can be audited."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    REJECT = "reject"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    SHARE = "share"
    REVOKE = "revoke"
    CONFIGURE = "configure"
    EXECUTE = "execute"
    OTHER = "other"


class AuditResourceType(str, Enum):
    """Types of resources that can be audited."""
    USER = "user"
    GROUP = "group"
    ROLE = "role"
    PERMISSION = "permission"
    CONTENT = "content"
    MEDIA = "media"
    REPORT = "report"
    SETTING = "setting"
    API_KEY = "api_key"
    SYSTEM = "system"
    FILE = "file"
    DATABASE = "database"
    OTHER = "other"


class AuditRecord(Base):
    """
    Audit record model for storing audit trail entries.
    
    This model stores detailed information about actions performed in the
    application, including who performed the action, what was done, and when.
    """
    __tablename__ = "audit_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    user_id = Column(String(36), nullable=True, index=True)
    action_type = Column(String(20), nullable=False, index=True)
    resource_type = Column(String(20), nullable=False, index=True)
    resource_id = Column(String(36), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 can be up to 45 chars
    user_agent = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="success")
    details = Column(EncryptedJSON, nullable=True)  # Encrypted JSON for sensitive details
    metadata = Column(JSON, nullable=True)  # Non-sensitive metadata
    request_id = Column(String(36), nullable=True, index=True)
    session_id = Column(String(36), nullable=True, index=True)
    
    # Relationships
    changes = relationship("AuditChange", back_populates="audit_record", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return (
            f"<AuditRecord(id='{self.id}', timestamp='{self.timestamp}', "
            f"user_id='{self.user_id}', action_type='{self.action_type}', "
            f"resource_type='{self.resource_type}', resource_id='{self.resource_id}')>"
        )


class AuditChange(Base):
    """
    Audit change model for storing detailed changes in audit records.
    
    This model stores information about specific changes made to resources,
    including the field that was changed, and the old and new values.
    """
    __tablename__ = "audit_changes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_record_id = Column(UUID(as_uuid=True), ForeignKey("audit_records.id"), nullable=False)
    field_name = Column(String(100), nullable=False)
    old_value = Column(EncryptedString(1024), nullable=True)  # Encrypted for sensitive data
    new_value = Column(EncryptedString(1024), nullable=True)  # Encrypted for sensitive data
    is_sensitive = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    audit_record = relationship("AuditRecord", back_populates="changes")
    
    def __repr__(self) -> str:
        return (
            f"<AuditChange(id='{self.id}', audit_record_id='{self.audit_record_id}', "
            f"field_name='{self.field_name}', is_sensitive={self.is_sensitive})>"
        )


class AuditLogView(Base):
    """
    Audit log view model for tracking who viewed audit logs.
    
    This model stores information about access to audit logs, including
    who viewed them, when, and what filters were applied.
    """
    __tablename__ = "audit_log_views"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    user_id = Column(String(36), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    filters = Column(JSON, nullable=True)  # Search/filter criteria used
    records_returned = Column(Integer, nullable=False, default=0)
    query_time_ms = Column(Integer, nullable=True)
    
    def __repr__(self) -> str:
        return (
            f"<AuditLogView(id='{self.id}', timestamp='{self.timestamp}', "
            f"user_id='{self.user_id}', records_returned={self.records_returned})>"
        )


class SecurityIncident(Base):
    """
    Security incident model for tracking security incidents.
    
    This model stores information about security incidents detected by
    the intrusion detection system or reported by users/administrators.
    """
    __tablename__ = "security_incidents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    incident_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="open", index=True)
    source = Column(String(50), nullable=False)  # IDS, manual, etc.
    description = Column(Text, nullable=False)
    details = Column(EncryptedJSON, nullable=True)  # Encrypted JSON for sensitive details
    affected_users = Column(JSON, nullable=True)  # List of affected user IDs
    affected_resources = Column(JSON, nullable=True)  # List of affected resources
    reported_by = Column(String(36), nullable=True)  # User ID who reported it
    assigned_to = Column(String(36), nullable=True)  # User ID assigned to handle it
    resolution = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    related_audit_records = relationship(
        "IncidentAuditRecord",
        back_populates="incident",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return (
            f"<SecurityIncident(id='{self.id}', timestamp='{self.timestamp}', "
            f"incident_type='{self.incident_type}', severity='{self.severity}', "
            f"status='{self.status}')>"
        )


class IncidentAuditRecord(Base):
    """
    Association model linking security incidents to audit records.
    
    This model establishes a many-to-many relationship between security
    incidents and audit records.
    """
    __tablename__ = "incident_audit_records"
    
    incident_id = Column(UUID(as_uuid=True), ForeignKey("security_incidents.id"), primary_key=True)
    audit_record_id = Column(UUID(as_uuid=True), ForeignKey("audit_records.id"), primary_key=True)
    relationship_type = Column(String(20), nullable=False, default="related")  # related, cause, effect
    
    # Relationships
    incident = relationship("SecurityIncident", back_populates="related_audit_records")
    
    def __repr__(self) -> str:
        return (
            f"<IncidentAuditRecord(incident_id='{self.incident_id}', "
            f"audit_record_id='{self.audit_record_id}', "
            f"relationship_type='{self.relationship_type}')>"
        ) 