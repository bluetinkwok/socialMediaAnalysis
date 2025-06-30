"""
File upload API endpoints with validation.

This module provides endpoints for uploading files with validation for:
- File types and MIME types
- File sizes
- File signatures (magic bytes)
- Security features (malware scanning, pattern detection, metadata sanitization)
"""

import os
import logging
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Request
from sqlalchemy.orm import Session

from db.database import get_database
from db.models import MediaFile
from db.schemas import ApiResponse, MediaFileCreate
from core.file_validator import FileValidator
from core.config import get_settings
from security.security_integrator import get_security_integrator, SecurityIntegrator

# Configure logging
logger = logging.getLogger(__name__)
settings = get_settings()

# Create router
router = APIRouter(
    prefix="/uploads",
    tags=["uploads"],
    responses={404: {"description": "Not found"}},
)

# Initialize file validator
file_validator = FileValidator(
    max_file_size=settings.max_file_size_mb * 1024 * 1024,  # Convert MB to bytes
    allowed_mime_types=None,  # Use default list
    enforce_signature_check=True,
)

@router.post("/", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    db: Session = Depends(get_database),
    security: SecurityIntegrator = Depends(get_security_integrator),
):
    """
    Upload a file with validation and security scanning.
    
    This endpoint accepts a file upload, validates it using the FileValidator,
    scans it for security threats, and stores it in the appropriate location.
    
    The file is validated for:
    - File size (configurable maximum)
    - MIME type (must be in allowed list)
    - File signature (magic bytes must match the file extension)
    
    The file is also scanned for:
    - Malware using ClamAV
    - Suspicious patterns using YARA rules
    - Metadata that should be sanitized
    """
    try:
        # Validate the file
        is_valid, error = await file_validator.validate_file(file)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file: {error}"
            )
        
        # Create uploads directory if it doesn't exist
        uploads_dir = Path(settings.uploads_path)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix if file.filename else ""
        unique_filename = f"{os.urandom(8).hex()}{file_extension}"
        file_path = uploads_dir / unique_filename
        
        # Save the file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Get file size
        file_size = file_path.stat().st_size
        
        # Determine MIME type
        mime_type = file_validator.mime_magic.from_file(str(file_path))
        
        # Extract user ID from request if available (for future authentication)
        user_id = None  # Will be set when authentication is implemented
        
        # Process file with security features
        is_safe, security_error, security_results = await security.secure_upload_processing(
            file=file,
            file_path=file_path,
            request=request,
            user_id=user_id
        )
        
        if not is_safe:
            # Delete the unsafe file
            if file_path.exists():
                file_path.unlink()
                
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security check failed: {security_error}"
            )
        
        # Create media file record
        media_file = MediaFile(
            filename=file.filename,
            file_path=str(file_path),
            file_type=file_extension.lstrip(".").lower(),
            file_size=file_size,
            mime_type=mime_type,
            # These fields would be set if the file is associated with a post
            post_id=None  # Will need to be updated later if associated with a post
        )
        
        db.add(media_file)
        db.commit()
        db.refresh(media_file)
        
        return ApiResponse(
            success=True,
            message="File uploaded and security-checked successfully",
            data={
                "id": media_file.id,
                "filename": media_file.filename,
                "file_size": media_file.file_size,
                "mime_type": media_file.mime_type,
                "security_results": {
                    "metadata_sanitized": bool(security_results["metadata_sanitized"]),
                    "patterns_detected": len(security_results["suspicious_patterns"]),
                    "scan_status": "passed"
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )

@router.post("/multiple", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def upload_multiple_files(
    request: Request,
    files: List[UploadFile] = File(...),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    db: Session = Depends(get_database),
    security: SecurityIntegrator = Depends(get_security_integrator),
):
    """
    Upload multiple files with validation and security scanning.
    
    This endpoint accepts multiple file uploads, validates each using the FileValidator,
    scans them for security threats, and stores them in the appropriate location.
    """
    try:
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files provided"
            )
        
        # Create uploads directory if it doesn't exist
        uploads_dir = Path(settings.uploads_path)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        uploaded_files = []
        failed_files = []
        
        # Extract user ID from request if available (for future authentication)
        user_id = None  # Will be set when authentication is implemented
        
        for file in files:
            try:
                # Validate the file
                is_valid, error = await file_validator.validate_file(file)
                if not is_valid:
                    failed_files.append({
                        "filename": file.filename,
                        "error": f"Validation failed: {error}"
                    })
                    continue
                
                # Generate unique filename
                file_extension = Path(file.filename).suffix if file.filename else ""
                unique_filename = f"{os.urandom(8).hex()}{file_extension}"
                file_path = uploads_dir / unique_filename
                
                # Save the file
                with open(file_path, "wb") as f:
                    content = await file.read()
                    f.write(content)
                
                # Get file size
                file_size = file_path.stat().st_size
                
                # Determine MIME type
                mime_type = file_validator.mime_magic.from_file(str(file_path))
                
                # Process file with security features
                is_safe, security_error, security_results = await security.secure_upload_processing(
                    file=file,
                    file_path=file_path,
                    request=request,
                    user_id=user_id
                )
                
                if not is_safe:
                    # Delete the unsafe file
                    if file_path.exists():
                        file_path.unlink()
                        
                    failed_files.append({
                        "filename": file.filename,
                        "error": f"Security check failed: {security_error}"
                    })
                    continue
                
                # Create media file record
                media_file = MediaFile(
                    filename=file.filename,
                    file_path=str(file_path),
                    file_type=file_extension.lstrip(".").lower(),
                    file_size=file_size,
                    mime_type=mime_type,
                    # These fields would be set if the file is associated with a post
                    post_id=None  # Will need to be updated later if associated with a post
                )
                
                db.add(media_file)
                
                uploaded_files.append({
                    "filename": file.filename,
                    "file_size": file_size,
                    "mime_type": mime_type,
                    "security_results": {
                        "metadata_sanitized": bool(security_results["metadata_sanitized"]),
                        "patterns_detected": len(security_results["suspicious_patterns"]),
                        "scan_status": "passed"
                    }
                })
                
            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {str(e)}")
                failed_files.append({
                    "filename": file.filename,
                    "error": str(e)
                })
        
        db.commit()
        
        if not uploaded_files and failed_files:
            return ApiResponse(
                success=False,
                message="All files failed validation or security checks",
                data={
                    "uploaded_count": 0,
                    "failed_count": len(failed_files),
                    "failed_files": failed_files
                }
            )
        
        return ApiResponse(
            success=True,
            message=f"Successfully uploaded {len(uploaded_files)} files" + 
                    (f", {len(failed_files)} files failed" if failed_files else ""),
            data={
                "uploaded_count": len(uploaded_files),
                "failed_count": len(failed_files),
                "files": uploaded_files,
                "failed_files": failed_files if failed_files else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading multiple files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload files: {str(e)}"
        ) 