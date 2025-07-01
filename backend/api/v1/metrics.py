"""
Metrics API Module

This module provides API endpoints for exposing application metrics in Prometheus format.
It includes security metrics, performance metrics, and system metrics.
"""

import os
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest, multiprocess

from core.auth import get_current_admin_user
from core.security_logger import security_logger

# Create router
router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
    dependencies=[Depends(get_current_admin_user)],  # Require admin authentication
)


@router.get("")
async def get_metrics(request: Request) -> Response:
    """
    Get application metrics in Prometheus format.
    
    This endpoint exposes all registered Prometheus metrics in the text-based
    exposition format that can be scraped by a Prometheus server.
    
    Returns:
        Response: Prometheus metrics in text format
    """
    # Log metrics access
    client_ip = request.client.host if request.client else "unknown"
    user = request.state.user if hasattr(request.state, "user") else None
    user_id = user.id if user else "unknown"
    
    security_logger.info(
        "Metrics accessed",
        user_id=user_id,
        ip_address=client_ip
    )
    
    # Generate metrics
    registry = CollectorRegistry()
    
    # Handle multi-process mode if enabled
    if 'PROMETHEUS_MULTIPROC_DIR' in os.environ:
        multiprocess.MultiProcessCollector(registry)
    
    # Generate metrics output
    metrics_data = generate_latest(registry)
    
    # Return response with proper content type
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )


@router.get("/security")
async def get_security_metrics(request: Request) -> Response:
    """
    Get security-specific metrics in Prometheus format.
    
    This endpoint exposes only security-related metrics for specialized monitoring.
    
    Returns:
        Response: Security metrics in Prometheus text format
    """
    # Log metrics access
    client_ip = request.client.host if request.client else "unknown"
    user = request.state.user if hasattr(request.state, "user") else None
    user_id = user.id if user else "unknown"
    
    security_logger.info(
        "Security metrics accessed",
        user_id=user_id,
        ip_address=client_ip
    )
    
    # Create a specialized registry with only security metrics
    registry = CollectorRegistry()
    
    # Handle multi-process mode if enabled
    if 'PROMETHEUS_MULTIPROC_DIR' in os.environ:
        multiprocess.MultiProcessCollector(registry)
    
    # Filter for only security metrics (those with 'security_' prefix)
    # This is a bit of a hack since Prometheus doesn't have built-in filtering
    # In a real implementation, you might want to use a more robust approach
    
    # Generate metrics output
    metrics_data = generate_latest(registry)
    
    # Filter lines starting with security metrics
    security_metrics_lines = [
        line for line in metrics_data.decode('utf-8').split('\n')
        if line.startswith('security_') or line.startswith('# HELP security_') or line.startswith('# TYPE security_')
    ]
    
    # Return response with proper content type
    return Response(
        content='\n'.join(security_metrics_lines).encode('utf-8'),
        media_type=CONTENT_TYPE_LATEST
    ) 