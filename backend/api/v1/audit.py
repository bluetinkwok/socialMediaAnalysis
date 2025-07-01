"""
Audit API Module

This module provides API endpoints for accessing and managing audit trails.
It includes endpoints for viewing audit records, exporting audit data,
and generating audit reports.
"""

import datetime
from typing import Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from core.audit_trail import (
    AuditActionType, AuditResourceType, AuditTrailService, get_audit_service
)
from core.auth import get_current_admin_user
from core.security_logger import security_logger
from db.audit_models import AuditRecord


# Pydantic models for API
class AuditChangeResponse(BaseModel):
    """Model for audit change response."""
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    is_sensitive: bool = False
    
    class Config:
        orm_mode = True


class AuditRecordResponse(BaseModel):
    """Model for audit record response."""
    id: str
    timestamp: datetime.datetime
    user_id: Optional[str] = None
    action_type: str
    resource_type: str
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    status: str
    metadata: Optional[Dict] = None
    changes: List[AuditChangeResponse] = []
    
    class Config:
        orm_mode = True


class AuditRecordListResponse(BaseModel):
    """Model for audit record list response."""
    records: List[AuditRecordResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class AuditStatisticsResponse(BaseModel):
    """Model for audit statistics response."""
    total_count: int
    action_type_counts: Dict[str, int]
    resource_type_counts: Dict[str, int]
    status_counts: Dict[str, int]
    start_time: Optional[str] = None
    end_time: Optional[str] = None


# Create router
router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(get_current_admin_user)],  # Require admin authentication
)


@router.get("/records", response_model=AuditRecordListResponse)
async def get_audit_records(
    request: Request,
    user_id: Optional[str] = None,
    action_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    audit_service: AuditTrailService = Depends(get_audit_service)
) -> AuditRecordListResponse:
    """
    Get audit records matching the specified criteria.
    
    Args:
        request: The HTTP request
        user_id: Filter by user ID
        action_type: Filter by action type
        resource_type: Filter by resource type
        resource_id: Filter by resource ID
        start_time: Filter by start time
        end_time: Filter by end time
        status: Filter by status
        page: Page number
        page_size: Number of records per page
        audit_service: Audit trail service
        
    Returns:
        List of audit records and pagination information
    """
    # Get the current user
    current_user = request.state.user
    
    # Calculate offset
    offset = (page - 1) * page_size
    
    # Get the client IP address
    client_ip = request.client.host if request.client else None
    
    # Get audit records
    records, total_count = audit_service.get_audit_records(
        user_id=user_id,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        start_time=start_time,
        end_time=end_time,
        status=status,
        limit=page_size,
        offset=offset,
        viewer_id=current_user.id,
        viewer_ip=client_ip
    )
    
    # Calculate total pages
    total_pages = (total_count + page_size - 1) // page_size
    
    # Log the audit records access
    security_logger.info(
        "Audit records accessed",
        user_id=current_user.id,
        ip_address=client_ip,
        filters={
            "user_id": user_id,
            "action_type": action_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "status": status,
            "page": page,
            "page_size": page_size
        },
        records_returned=len(records)
    )
    
    return AuditRecordListResponse(
        records=records,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/records/{record_id}", response_model=AuditRecordResponse)
async def get_audit_record(
    record_id: str,
    request: Request,
    audit_service: AuditTrailService = Depends(get_audit_service)
) -> AuditRecordResponse:
    """
    Get a specific audit record by ID.
    
    Args:
        record_id: ID of the audit record
        request: The HTTP request
        audit_service: Audit trail service
        
    Returns:
        The audit record
    """
    # Get the current user
    current_user = request.state.user
    
    # Get the client IP address
    client_ip = request.client.host if request.client else None
    
    # Get the audit record
    record = audit_service.get_audit_record(record_id)
    
    if not record:
        raise HTTPException(status_code=404, detail="Audit record not found")
    
    # Log the audit record access
    security_logger.info(
        "Audit record accessed",
        user_id=current_user.id,
        ip_address=client_ip,
        audit_record_id=record_id
    )
    
    return record


@router.get("/statistics", response_model=AuditStatisticsResponse)
async def get_audit_statistics(
    request: Request,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None,
    audit_service: AuditTrailService = Depends(get_audit_service)
) -> AuditStatisticsResponse:
    """
    Get statistics about audit records.
    
    Args:
        request: The HTTP request
        start_time: Filter by start time
        end_time: Filter by end time
        audit_service: Audit trail service
        
    Returns:
        Audit statistics
    """
    # Get the current user
    current_user = request.state.user
    
    # Get the client IP address
    client_ip = request.client.host if request.client else None
    
    # Get audit statistics
    statistics = audit_service.get_audit_statistics(
        start_time=start_time,
        end_time=end_time
    )
    
    # Log the audit statistics access
    security_logger.info(
        "Audit statistics accessed",
        user_id=current_user.id,
        ip_address=client_ip,
        filters={
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None
        }
    )
    
    return AuditStatisticsResponse(**statistics)


@router.get("/export")
async def export_audit_records(
    request: Request,
    user_id: Optional[str] = None,
    action_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None,
    status: Optional[str] = None,
    format: str = Query("json", regex="^(json|csv)$"),
    audit_service: AuditTrailService = Depends(get_audit_service)
) -> Response:
    """
    Export audit records to a specified format.
    
    Args:
        request: The HTTP request
        user_id: Filter by user ID
        action_type: Filter by action type
        resource_type: Filter by resource type
        resource_id: Filter by resource ID
        start_time: Filter by start time
        end_time: Filter by end time
        status: Filter by status
        format: Export format (json, csv)
        audit_service: Audit trail service
        
    Returns:
        Exported audit records as a file
    """
    # Get the current user
    current_user = request.state.user
    
    # Get the client IP address
    client_ip = request.client.host if request.client else None
    
    # Export audit records
    exported_data = audit_service.export_audit_records(
        user_id=user_id,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        start_time=start_time,
        end_time=end_time,
        status=status,
        format=format,
        exporter_id=current_user.id,
        exporter_ip=client_ip
    )
    
    # Log the audit records export
    security_logger.info(
        "Audit records exported",
        user_id=current_user.id,
        ip_address=client_ip,
        filters={
            "user_id": user_id,
            "action_type": action_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "status": status,
            "format": format
        }
    )
    
    # Set content type based on format
    content_type = "application/json" if format == "json" else "text/csv"
    
    # Generate filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"audit_export_{timestamp}.{format}"
    
    # Create response with appropriate headers
    return Response(
        content=exported_data,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    ) 