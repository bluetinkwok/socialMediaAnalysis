"""
File Upload API

This module provides API endpoints for file uploads with integrated security features.
"""

import os
import shutil
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request, status, BackgroundTasks
from fastapi.responses import JSONResponse

from core.config import get_settings
from core.auth import get_current_user
from models.user import User
from security.security_integrator import get_security_integrator, init_security_integrator
from utils.file_utils import generate_secure_filename, validate_file_extension, get_file_hash

# Configure logging
logger = logging.getLogger(__name__)
settings = get_settings()

# Create router
router = APIRouter(prefix="/upload", tags=["upload"])

# Ensure upload directory exists
os.makedirs(settings.upload_dir, exist_ok=True)

@router.on_event("startup")
async def startup_event():
    """Initialize security components on startup"""
    logger.info("Initializing security components for upload API...")
    success = await init_security_integrator()
    if not success:
        logger.warning("Security components initialization failed. Some security features may be unavailable.")

@router.post("/", response_model=Dict[str, Any])
async def upload_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a file with security scanning.
    
    Args:
        request: The FastAPI request object
        background_tasks: FastAPI background tasks
        file: The file to upload
        description: Optional description of the file
        tags: Optional comma-separated tags for the file
        current_user: The authenticated user
        
    Returns:
        JSON response with upload status and details
    """
    try:
        # Get security integrator
        security_integrator = get_security_integrator()
        
        # Validate file extension
        if not validate_file_extension(file.filename):
            logger.warning(f"Invalid file extension: {file.filename}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed: {file.filename}"
            )
        
        # Generate secure filename
        secure_filename = generate_secure_filename(file.filename)
        file_path = os.path.join(settings.upload_dir, secure_filename)
        
        # Save file to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get file hash for integrity verification
        file_hash = get_file_hash(file_path)
        
        # Process file through security checks
        is_safe, security_results = await security_integrator.process_file(
            file_path=file_path,
            user_id=str(current_user.id)
        )
        
        if not is_safe:
            # Delete the unsafe file
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Return error with security results
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "rejected",
                    "message": "File failed security checks",
                    "security_results": security_results
                }
            )
        
        # File is safe, prepare response
        response_data = {
            "status": "success",
            "filename": secure_filename,
            "original_filename": file.filename,
            "file_size": os.path.getsize(file_path),
            "file_hash": file_hash,
            "description": description,
            "tags": tags.split(",") if tags else [],
            "security_passed": True,
            "security_details": security_results
        }
        
        # Add file to database in background
        background_tasks.add_task(
            save_file_to_database,
            file_path=file_path,
            original_filename=file.filename,
            secure_filename=secure_filename,
            file_hash=file_hash,
            description=description,
            tags=tags,
            user_id=current_user.id
        )
        
        return response_data
        
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )

async def save_file_to_database(
    file_path: str,
    original_filename: str,
    secure_filename: str,
    file_hash: str,
    description: Optional[str],
    tags: Optional[str],
    user_id: int
) -> None:
    """
    Save file information to database.
    
    Args:
        file_path: Path to the saved file
        original_filename: Original filename
        secure_filename: Secure filename used for storage
        file_hash: SHA-256 hash of the file
        description: Optional description
        tags: Optional comma-separated tags
        user_id: ID of the user who uploaded the file
    """
    try:
        # This would typically involve database operations
        # For now, just log the action
        logger.info(f"File saved to database: {secure_filename} (user: {user_id})")
        
        # In a real implementation, you would:
        # 1. Create a database record for the file
        # 2. Associate it with the user
        # 3. Store metadata like description, tags, etc.
        
    except Exception as e:
        logger.error(f"Error saving file to database: {str(e)}")

@router.get("/security-events", response_model=List[Dict[str, Any]])
async def get_security_events(
    event_type: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """
    Get recent security events.
    
    Args:
        event_type: Optional filter for event type
        limit: Maximum number of events to return
        current_user: The authenticated user
        
    Returns:
        List of security events
    """
    # Only allow admin users to access security events
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access security events"
        )
    
    security_integrator = get_security_integrator()
    events = security_integrator.get_security_events(event_type, limit)
    
    return events
