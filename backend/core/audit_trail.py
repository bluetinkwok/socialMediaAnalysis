"""
Audit Trail Module

This module provides functionality for creating and managing audit trails
for security-relevant actions in the application. It includes methods for
recording audit events, querying the audit trail, and generating reports.
"""

import datetime
import json
import uuid
from contextlib import contextmanager
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, Set, Tuple, Union

from sqlalchemy.orm import Session

from core.security_logger import security_logger
from db.audit_models import (
    AuditActionType, AuditChange, AuditLogView, AuditRecord, AuditResourceType
)
from db.database import get_db
from models.security import SecurityMetrics


class AuditTrailService:
    """
    Service for managing audit trails in the application.
    
    This class provides methods for recording audit events, querying
    the audit trail, and generating reports.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the audit trail service.
        
        Args:
            db: Database session
        """
        self.db = db
        self._sensitive_fields = {
            "password", "token", "secret", "key", "credential", "auth", "ssn", "credit_card",
            "card_number", "cvv", "pin", "social_security", "bank_account", "routing_number"
        }
    
    def add_sensitive_fields(self, fields: Set[str]) -> None:
        """
        Add fields to the sensitive fields set.
        
        Args:
            fields: Set of field names to mark as sensitive
        """
        self._sensitive_fields.update(fields)
    
    def is_sensitive_field(self, field_name: str) -> bool:
        """
        Check if a field is considered sensitive.
        
        Args:
            field_name: Name of the field to check
            
        Returns:
            True if the field is sensitive, False otherwise
        """
        field_lower = field_name.lower()
        return any(sensitive in field_lower for sensitive in self._sensitive_fields)
    
    def create_audit_record(
        self,
        action_type: Union[AuditActionType, str],
        resource_type: Union[AuditResourceType, str],
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        details: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        changes: Optional[List[Dict]] = None
    ) -> AuditRecord:
        """
        Create an audit record for a security-relevant action.
        
        Args:
            action_type: Type of action performed
            resource_type: Type of resource affected
            user_id: ID of the user who performed the action
            resource_id: ID of the resource affected
            ip_address: IP address of the client
            user_agent: User agent of the client
            status: Status of the action (success, failure, etc.)
            details: Additional details about the action
            metadata: Non-sensitive metadata
            request_id: ID of the HTTP request
            session_id: ID of the user session
            changes: List of changes made to the resource
            
        Returns:
            The created audit record
        """
        # Convert enum values to strings if needed
        if isinstance(action_type, AuditActionType):
            action_type = action_type.value
        if isinstance(resource_type, AuditResourceType):
            resource_type = resource_type.value
        
        # Create the audit record
        audit_record = AuditRecord(
            user_id=user_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            details=details,
            metadata=metadata,
            request_id=request_id,
            session_id=session_id
        )
        
        # Add changes if provided
        if changes:
            for change in changes:
                field_name = change.get("field_name")
                old_value = change.get("old_value")
                new_value = change.get("new_value")
                
                # Skip if field name is missing
                if not field_name:
                    continue
                
                # Check if the field is sensitive
                is_sensitive = self.is_sensitive_field(field_name)
                
                # Convert values to strings if needed
                old_value_str = self._value_to_string(old_value) if old_value is not None else None
                new_value_str = self._value_to_string(new_value) if new_value is not None else None
                
                # Create the audit change
                audit_change = AuditChange(
                    field_name=field_name,
                    old_value=old_value_str,
                    new_value=new_value_str,
                    is_sensitive=is_sensitive
                )
                
                audit_record.changes.append(audit_change)
        
        # Add to the database
        self.db.add(audit_record)
        self.db.commit()
        self.db.refresh(audit_record)
        
        # Log the audit record creation
        security_logger.info(
            "Audit record created",
            audit_record_id=str(audit_record.id),
            action_type=action_type,
            resource_type=resource_type,
            user_id=user_id,
            resource_id=resource_id,
            status=status
        )
        
        return audit_record
    
    def _value_to_string(self, value: Any) -> str:
        """
        Convert a value to a string representation.
        
        Args:
            value: Value to convert
            
        Returns:
            String representation of the value
        """
        if value is None:
            return None
        elif isinstance(value, (dict, list)):
            return json.dumps(value)
        else:
            return str(value)
    
    def get_audit_record(self, record_id: str) -> Optional[AuditRecord]:
        """
        Get an audit record by ID.
        
        Args:
            record_id: ID of the audit record
            
        Returns:
            The audit record, or None if not found
        """
        return self.db.query(AuditRecord).filter(AuditRecord.id == record_id).first()
    
    def get_audit_records(
        self,
        user_id: Optional[str] = None,
        action_type: Optional[Union[AuditActionType, str]] = None,
        resource_type: Optional[Union[AuditResourceType, str]] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        viewer_id: Optional[str] = None,
        viewer_ip: Optional[str] = None
    ) -> Tuple[List[AuditRecord], int]:
        """
        Get audit records matching the specified criteria.
        
        Args:
            user_id: Filter by user ID
            action_type: Filter by action type
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            start_time: Filter by start time
            end_time: Filter by end time
            status: Filter by status
            limit: Maximum number of records to return
            offset: Offset for pagination
            viewer_id: ID of the user viewing the audit records
            viewer_ip: IP address of the viewer
            
        Returns:
            Tuple of (list of audit records, total count)
        """
        # Convert enum values to strings if needed
        if isinstance(action_type, AuditActionType):
            action_type = action_type.value
        if isinstance(resource_type, AuditResourceType):
            resource_type = resource_type.value
        
        # Build the query
        query = self.db.query(AuditRecord)
        
        # Apply filters
        if user_id:
            query = query.filter(AuditRecord.user_id == user_id)
        if action_type:
            query = query.filter(AuditRecord.action_type == action_type)
        if resource_type:
            query = query.filter(AuditRecord.resource_type == resource_type)
        if resource_id:
            query = query.filter(AuditRecord.resource_id == resource_id)
        if start_time:
            query = query.filter(AuditRecord.timestamp >= start_time)
        if end_time:
            query = query.filter(AuditRecord.timestamp <= end_time)
        if status:
            query = query.filter(AuditRecord.status == status)
        
        # Get the total count
        total_count = query.count()
        
        # Apply pagination
        query = query.order_by(AuditRecord.timestamp.desc())
        query = query.limit(limit).offset(offset)
        
        # Execute the query
        records = query.all()
        
        # Log the audit log view
        if viewer_id:
            filters = {
                "user_id": user_id,
                "action_type": action_type,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "status": status,
                "limit": limit,
                "offset": offset
            }
            
            audit_log_view = AuditLogView(
                user_id=viewer_id,
                ip_address=viewer_ip,
                filters=filters,
                records_returned=len(records)
            )
            
            self.db.add(audit_log_view)
            self.db.commit()
        
        return records, total_count
    
    def get_audit_statistics(
        self,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about audit records.
        
        Args:
            start_time: Filter by start time
            end_time: Filter by end time
            
        Returns:
            Dictionary of statistics
        """
        # Build the base query
        query = self.db.query(AuditRecord)
        
        # Apply time filters
        if start_time:
            query = query.filter(AuditRecord.timestamp >= start_time)
        if end_time:
            query = query.filter(AuditRecord.timestamp <= end_time)
        
        # Get the total count
        total_count = query.count()
        
        # Get counts by action type
        action_type_counts = {}
        for action_type in AuditActionType:
            count = query.filter(AuditRecord.action_type == action_type.value).count()
            action_type_counts[action_type.value] = count
        
        # Get counts by resource type
        resource_type_counts = {}
        for resource_type in AuditResourceType:
            count = query.filter(AuditRecord.resource_type == resource_type.value).count()
            resource_type_counts[resource_type.value] = count
        
        # Get counts by status
        status_counts = {}
        for status in ["success", "failure", "error", "warning"]:
            count = query.filter(AuditRecord.status == status).count()
            status_counts[status] = count
        
        # Return the statistics
        return {
            "total_count": total_count,
            "action_type_counts": action_type_counts,
            "resource_type_counts": resource_type_counts,
            "status_counts": status_counts,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None
        }
    
    def export_audit_records(
        self,
        user_id: Optional[str] = None,
        action_type: Optional[Union[AuditActionType, str]] = None,
        resource_type: Optional[Union[AuditResourceType, str]] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
        status: Optional[str] = None,
        format: str = "json",
        exporter_id: Optional[str] = None,
        exporter_ip: Optional[str] = None
    ) -> str:
        """
        Export audit records to a specified format.
        
        Args:
            user_id: Filter by user ID
            action_type: Filter by action type
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            start_time: Filter by start time
            end_time: Filter by end time
            status: Filter by status
            format: Export format (json, csv)
            exporter_id: ID of the user exporting the records
            exporter_ip: IP address of the exporter
            
        Returns:
            Exported audit records as a string
        """
        # Get the audit records
        records, _ = self.get_audit_records(
            user_id=user_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            start_time=start_time,
            end_time=end_time,
            status=status,
            limit=10000,  # Limit to 10,000 records for export
            offset=0,
            viewer_id=exporter_id,
            viewer_ip=exporter_ip
        )
        
        # Convert records to dictionaries
        record_dicts = []
        for record in records:
            record_dict = {
                "id": str(record.id),
                "timestamp": record.timestamp.isoformat(),
                "user_id": record.user_id,
                "action_type": record.action_type,
                "resource_type": record.resource_type,
                "resource_id": record.resource_id,
                "status": record.status,
                "ip_address": record.ip_address,
                "user_agent": record.user_agent,
                "metadata": record.metadata
            }
            
            # Add changes
            changes = []
            for change in record.changes:
                # Skip sensitive fields for export
                if change.is_sensitive:
                    continue
                
                changes.append({
                    "field_name": change.field_name,
                    "old_value": change.old_value,
                    "new_value": change.new_value
                })
            
            record_dict["changes"] = changes
            record_dicts.append(record_dict)
        
        # Export in the requested format
        if format == "json":
            return json.dumps(record_dicts, indent=2)
        elif format == "csv":
            # Simple CSV export (could use csv module for more complex cases)
            csv_lines = ["id,timestamp,user_id,action_type,resource_type,resource_id,status,ip_address"]
            for record in record_dicts:
                csv_lines.append(
                    f"{record['id']},{record['timestamp']},{record['user_id']},"
                    f"{record['action_type']},{record['resource_type']},"
                    f"{record['resource_id']},{record['status']},{record['ip_address']}"
                )
            return "\n".join(csv_lines)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def log_data_access(
        self,
        user_id: str,
        resource_type: Union[AuditResourceType, str],
        resource_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AuditRecord:
        """
        Log a data access event.
        
        Args:
            user_id: ID of the user who accessed the data
            resource_type: Type of resource accessed
            resource_id: ID of the resource accessed
            ip_address: IP address of the client
            user_agent: User agent of the client
            details: Additional details about the access
            metadata: Non-sensitive metadata
            request_id: ID of the HTTP request
            session_id: ID of the user session
            
        Returns:
            The created audit record
        """
        return self.create_audit_record(
            action_type=AuditActionType.READ,
            resource_type=resource_type,
            user_id=user_id,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status="success",
            details=details,
            metadata=metadata,
            request_id=request_id,
            session_id=session_id
        )
    
    def log_data_modification(
        self,
        user_id: str,
        resource_type: Union[AuditResourceType, str],
        resource_id: str,
        action_type: Union[AuditActionType, str],
        changes: List[Dict],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AuditRecord:
        """
        Log a data modification event.
        
        Args:
            user_id: ID of the user who modified the data
            resource_type: Type of resource modified
            resource_id: ID of the resource modified
            action_type: Type of modification (create, update, delete)
            changes: List of changes made to the resource
            ip_address: IP address of the client
            user_agent: User agent of the client
            details: Additional details about the modification
            metadata: Non-sensitive metadata
            request_id: ID of the HTTP request
            session_id: ID of the user session
            
        Returns:
            The created audit record
        """
        return self.create_audit_record(
            action_type=action_type,
            resource_type=resource_type,
            user_id=user_id,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status="success",
            details=details,
            metadata=metadata,
            request_id=request_id,
            session_id=session_id,
            changes=changes
        )
    
    def log_authentication_event(
        self,
        user_id: Optional[str],
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AuditRecord:
        """
        Log an authentication event.
        
        Args:
            user_id: ID of the user who attempted authentication
            success: Whether authentication was successful
            ip_address: IP address of the client
            user_agent: User agent of the client
            details: Additional details about the authentication
            metadata: Non-sensitive metadata
            request_id: ID of the HTTP request
            session_id: ID of the user session
            
        Returns:
            The created audit record
        """
        action_type = AuditActionType.LOGIN
        status = "success" if success else "failure"
        
        return self.create_audit_record(
            action_type=action_type,
            resource_type=AuditResourceType.USER,
            user_id=user_id,
            resource_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            details=details,
            metadata=metadata,
            request_id=request_id,
            session_id=session_id
        )
    
    def log_permission_change(
        self,
        user_id: str,
        target_user_id: str,
        permission_changes: List[Dict],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AuditRecord:
        """
        Log a permission change event.
        
        Args:
            user_id: ID of the user who changed the permissions
            target_user_id: ID of the user whose permissions were changed
            permission_changes: List of permission changes
            ip_address: IP address of the client
            user_agent: User agent of the client
            details: Additional details about the permission change
            metadata: Non-sensitive metadata
            request_id: ID of the HTTP request
            session_id: ID of the user session
            
        Returns:
            The created audit record
        """
        return self.create_audit_record(
            action_type=AuditActionType.UPDATE,
            resource_type=AuditResourceType.PERMISSION,
            user_id=user_id,
            resource_id=target_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status="success",
            details=details,
            metadata=metadata,
            request_id=request_id,
            session_id=session_id,
            changes=permission_changes
        )


@contextmanager
def get_audit_service() -> Generator[AuditTrailService, None, None]:
    """
    Context manager for getting an audit trail service.
    
    Yields:
        AuditTrailService instance
    """
    db = next(get_db())
    try:
        yield AuditTrailService(db)
    finally:
        db.close()


def create_audit_record(
    action_type: Union[AuditActionType, str],
    resource_type: Union[AuditResourceType, str],
    user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = "success",
    details: Optional[Dict] = None,
    metadata: Optional[Dict] = None,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    changes: Optional[List[Dict]] = None
) -> AuditRecord:
    """
    Create an audit record for a security-relevant action.
    
    Args:
        action_type: Type of action performed
        resource_type: Type of resource affected
        user_id: ID of the user who performed the action
        resource_id: ID of the resource affected
        ip_address: IP address of the client
        user_agent: User agent of the client
        status: Status of the action (success, failure, etc.)
        details: Additional details about the action
        metadata: Non-sensitive metadata
        request_id: ID of the HTTP request
        session_id: ID of the user session
        changes: List of changes made to the resource
        
    Returns:
        The created audit record
    """
    with get_audit_service() as audit_service:
        return audit_service.create_audit_record(
            action_type=action_type,
            resource_type=resource_type,
            user_id=user_id,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            details=details,
            metadata=metadata,
            request_id=request_id,
            session_id=session_id,
            changes=changes
        ) 