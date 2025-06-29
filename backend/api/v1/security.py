"""
Security API endpoints for the Social Media Analysis Platform
"""

from typing import Dict, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, HttpUrl, validator

from core.security import url_validator
from core.malicious_url_detector import malicious_url_detector

router = APIRouter(
    prefix="/security",
    tags=["security"],
    responses={404: {"description": "Not found"}},
)


class URLValidationRequest(BaseModel):
    """URL validation request model"""
    url: str
    strict_mode: bool = True


class URLValidationResponse(BaseModel):
    """URL validation response model"""
    is_valid: bool
    error: Optional[str] = None
    validation_details: Optional[Dict] = None
    url_info: Optional[Dict] = None


class MaliciousURLCheckRequest(BaseModel):
    """Malicious URL check request model"""
    url: str


class MaliciousURLCheckResponse(BaseModel):
    """Malicious URL check response model"""
    url: str
    is_valid: bool
    is_malicious: bool
    domain: Optional[str] = None
    detection_method: Optional[str] = None
    threat_type: Optional[str] = None
    checks: Optional[Dict] = None
    error: Optional[str] = None


class BatchURLCheckRequest(BaseModel):
    """Batch URL check request model"""
    urls: List[str]


class BatchURLCheckResponse(BaseModel):
    """Batch URL check response model"""
    safe_urls: List[Dict]
    malicious_urls: List[Dict]
    summary: Dict


@router.post("/validate-url", response_model=URLValidationResponse)
async def validate_url(request: URLValidationRequest):
    """
    Validate URL format
    """
    result = url_validator.validate_url_format(request.url, request.strict_mode)
    return result


@router.post("/check-url", response_model=MaliciousURLCheckResponse)
async def check_url(request: MaliciousURLCheckRequest):
    """
    Check if a URL is malicious
    """
    result = malicious_url_detector.check_url(request.url)
    return result


@router.post("/batch-check", response_model=BatchURLCheckResponse)
async def batch_check(request: BatchURLCheckRequest):
    """
    Check multiple URLs for malicious content
    """
    if len(request.urls) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 URLs allowed per batch"
        )
    
    result = malicious_url_detector.check_batch_urls(request.urls)
    return result


@router.get("/stats")
async def get_stats():
    """
    Get URL validation and malicious detection statistics
    """
    return {
        "validation_stats": url_validator.get_validation_stats(),
        "detection_stats": malicious_url_detector.get_stats()
    }


@router.post("/blacklist/{domain}")
async def add_to_blacklist(domain: str):
    """
    Add a domain to the blacklist
    """
    success = malicious_url_detector.add_to_blacklist(domain)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add domain to blacklist"
        )
    return {"status": "success", "message": f"Added {domain} to blacklist"}


@router.post("/whitelist/{domain}")
async def add_to_whitelist(domain: str):
    """
    Add a domain to the whitelist
    """
    success = malicious_url_detector.add_to_whitelist(domain)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add domain to whitelist"
        )
    return {"status": "success", "message": f"Added {domain} to whitelist"} 