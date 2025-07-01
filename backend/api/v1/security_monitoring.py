"""
Security Monitoring API Module

This module provides API endpoints for security monitoring and intrusion detection.
It includes endpoints for viewing security events, suspicious activities,
and security incidents.
"""

import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from core.auth import get_current_admin_user
from core.intrusion_detection import (
    EventType, SecurityEvent, SeverityLevel, SuspiciousActivityType,
    get_recent_events, get_suspicious_ips, get_suspicious_users
)
from core.security_logger import security_logger
from db.audit_models import SecurityIncident


# Pydantic models for API
class SecurityEventResponse(BaseModel):
    """Model for security event response."""
    event_type: str
    user_id: Optional[str] = None
    ip_address: str
    timestamp: str
    details: Dict = {}


class SuspiciousActivityResponse(BaseModel):
    """Model for suspicious activity response."""
    activity_type: str
    severity: str
    ip_address: str
    user_id: Optional[str] = None
    timestamp: str
    details: Dict = {}


class SecurityIncidentResponse(BaseModel):
    """Model for security incident response."""
    id: str
    incident_type: str
    severity: str
    status: str
    timestamp: datetime.datetime
    description: str
    source: str
    affected_users: Optional[List[str]] = None
    affected_resources: Optional[List[Dict]] = None
    reported_by: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    resolved_at: Optional[datetime.datetime] = None
    
    class Config:
        orm_mode = True


class SecurityStatisticsResponse(BaseModel):
    """Model for security statistics response."""
    total_events: int
    events_by_type: Dict[str, int]
    suspicious_activities: int
    suspicious_activities_by_severity: Dict[str, int]
    blocked_ips_count: int
    active_incidents_count: int


class SuspiciousEntityResponse(BaseModel):
    """Model for suspicious entity response."""
    id: str  # IP address or user ID
    suspicion_score: int
    last_activity: Optional[str] = None
    activity_count: int = 0


# Create router
router = APIRouter(
    prefix="/security",
    tags=["security"],
    dependencies=[Depends(get_current_admin_user)],  # Require admin authentication
)


@router.get("/events", response_model=List[SecurityEventResponse])
async def get_security_events(
    request: Request,
    limit: int = Query(100, ge=1, le=1000)
) -> List[SecurityEventResponse]:
    """
    Get recent security events.
    
    Args:
        request: The HTTP request
        limit: Maximum number of events to return
        
    Returns:
        List of recent security events
    """
    # Get the current user
    current_user = request.state.user
    
    # Get the client IP address
    client_ip = request.client.host if request.client else None
    
    # Get recent events
    events = get_recent_events(limit)
    
    # Log the security events access
    security_logger.info(
        "Security events accessed",
        user_id=current_user.id,
        ip_address=client_ip,
        events_count=len(events)
    )
    
    # Convert to response format
    return [
        SecurityEventResponse(
            event_type=event["event_type"],
            user_id=event["user_id"],
            ip_address=event["ip_address"],
            timestamp=event["timestamp"],
            details=event["details"]
        )
        for event in events
    ]


@router.get("/suspicious/ips", response_model=List[SuspiciousEntityResponse])
async def get_suspicious_ips_endpoint(
    request: Request,
    threshold: int = Query(5, ge=1, le=100)
) -> List[SuspiciousEntityResponse]:
    """
    Get suspicious IP addresses.
    
    Args:
        request: The HTTP request
        threshold: Minimum suspicion score to include
        
    Returns:
        List of suspicious IP addresses
    """
    # Get the current user
    current_user = request.state.user
    
    # Get the client IP address
    client_ip = request.client.host if request.client else None
    
    # Get suspicious IPs
    suspicious_ips = get_suspicious_ips(threshold)
    
    # Log the suspicious IPs access
    security_logger.info(
        "Suspicious IPs accessed",
        user_id=current_user.id,
        ip_address=client_ip,
        ips_count=len(suspicious_ips)
    )
    
    # Convert to response format
    return [
        SuspiciousEntityResponse(
            id=ip,
            suspicion_score=score,
            activity_count=0,  # Would need to be calculated from events
            last_activity=None  # Would need to be calculated from events
        )
        for ip, score in suspicious_ips.items()
    ]


@router.get("/suspicious/users", response_model=List[SuspiciousEntityResponse])
async def get_suspicious_users_endpoint(
    request: Request,
    threshold: int = Query(5, ge=1, le=100)
) -> List[SuspiciousEntityResponse]:
    """
    Get suspicious users.
    
    Args:
        request: The HTTP request
        threshold: Minimum suspicion score to include
        
    Returns:
        List of suspicious users
    """
    # Get the current user
    current_user = request.state.user
    
    # Get the client IP address
    client_ip = request.client.host if request.client else None
    
    # Get suspicious users
    suspicious_users = get_suspicious_users(threshold)
    
    # Log the suspicious users access
    security_logger.info(
        "Suspicious users accessed",
        user_id=current_user.id,
        ip_address=client_ip,
        users_count=len(suspicious_users)
    )
    
    # Convert to response format
    return [
        SuspiciousEntityResponse(
            id=user_id,
            suspicion_score=score,
            activity_count=0,  # Would need to be calculated from events
            last_activity=None  # Would need to be calculated from events
        )
        for user_id, score in suspicious_users.items()
    ]


@router.get("/incidents", response_model=List[SecurityIncidentResponse])
async def get_security_incidents(
    request: Request,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> List[SecurityIncidentResponse]:
    """
    Get security incidents.
    
    Args:
        request: The HTTP request
        status: Filter by status
        severity: Filter by severity
        start_time: Filter by start time
        end_time: Filter by end time
        limit: Maximum number of incidents to return
        offset: Offset for pagination
        
    Returns:
        List of security incidents
    """
    # Get the current user
    current_user = request.state.user
    
    # Get the client IP address
    client_ip = request.client.host if request.client else None
    
    # Build query for security incidents
    # In a real implementation, this would query the database
    # For now, we'll return an empty list
    incidents = []
    
    # Log the security incidents access
    security_logger.info(
        "Security incidents accessed",
        user_id=current_user.id,
        ip_address=client_ip,
        filters={
            "status": status,
            "severity": severity,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "limit": limit,
            "offset": offset
        },
        incidents_count=len(incidents)
    )
    
    return incidents


@router.get("/statistics", response_model=SecurityStatisticsResponse)
async def get_security_statistics(
    request: Request,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None
) -> SecurityStatisticsResponse:
    """
    Get security statistics.
    
    Args:
        request: The HTTP request
        start_time: Filter by start time
        end_time: Filter by end time
        
    Returns:
        Security statistics
    """
    # Get the current user
    current_user = request.state.user
    
    # Get the client IP address
    client_ip = request.client.host if request.client else None
    
    # In a real implementation, these would be calculated from actual data
    # For now, we'll return placeholder statistics
    statistics = SecurityStatisticsResponse(
        total_events=0,
        events_by_type={},
        suspicious_activities=0,
        suspicious_activities_by_severity={},
        blocked_ips_count=0,
        active_incidents_count=0
    )
    
    # Log the security statistics access
    security_logger.info(
        "Security statistics accessed",
        user_id=current_user.id,
        ip_address=client_ip,
        filters={
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None
        }
    )
    
    return statistics


@router.post("/incidents/{incident_id}/assign", response_model=SecurityIncidentResponse)
async def assign_security_incident(
    incident_id: str,
    request: Request,
    assignee_id: str
) -> SecurityIncidentResponse:
    """
    Assign a security incident to a user.
    
    Args:
        incident_id: ID of the incident to assign
        request: The HTTP request
        assignee_id: ID of the user to assign the incident to
        
    Returns:
        The updated security incident
    """
    # Get the current user
    current_user = request.state.user
    
    # Get the client IP address
    client_ip = request.client.host if request.client else None
    
    # In a real implementation, this would update the incident in the database
    # For now, we'll raise a not found error
    raise HTTPException(status_code=404, detail="Security incident not found")


@router.post("/incidents/{incident_id}/resolve", response_model=SecurityIncidentResponse)
async def resolve_security_incident(
    incident_id: str,
    request: Request,
    resolution: str
) -> SecurityIncidentResponse:
    """
    Resolve a security incident.
    
    Args:
        incident_id: ID of the incident to resolve
        request: The HTTP request
        resolution: Resolution description
        
    Returns:
        The updated security incident
    """
    # Get the current user
    current_user = request.state.user
    
    # Get the client IP address
    client_ip = request.client.host if request.client else None
    
    # In a real implementation, this would update the incident in the database
    # For now, we'll raise a not found error
    raise HTTPException(status_code=404, detail="Security incident not found") 