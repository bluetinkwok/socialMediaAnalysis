"""
Platforms API endpoints for managing social media platforms
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from db.database import get_database
from db.models import Platform
from db.schemas import (
    Platform as PlatformSchema,
    PlatformCreate,
    PlatformUpdate,
    ApiResponse
)

router = APIRouter()


@router.get("/", response_model=ApiResponse)
async def get_platforms(
    active_only: bool = False,
    db: Session = Depends(get_database)
):
    """Get all platforms"""
    try:
        query = db.query(Platform)
        if active_only:
            query = query.filter(Platform.is_active == True)
        
        platforms = query.all()
        
        platform_data = [
            {
                "id": platform.id,
                "name": platform.name,
                "display_name": platform.display_name,
                "base_url": platform.base_url,
                "is_active": platform.is_active,
                "created_at": platform.created_at.isoformat(),
                "updated_at": platform.updated_at.isoformat()
            }
            for platform in platforms
        ]
        
        return ApiResponse(
            success=True,
            message=f"Retrieved {len(platform_data)} platforms",
            data=platform_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve platforms: {str(e)}"
        )


@router.get("/{platform_id}", response_model=ApiResponse)
async def get_platform(
    platform_id: int,
    db: Session = Depends(get_database)
):
    """Get a specific platform by ID"""
    try:
        platform = db.query(Platform).filter(Platform.id == platform_id).first()
        
        if not platform:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Platform not found"
            )
        
        platform_data = {
            "id": platform.id,
            "name": platform.name,
            "display_name": platform.display_name,
            "base_url": platform.base_url,
            "is_active": platform.is_active,
            "created_at": platform.created_at.isoformat(),
            "updated_at": platform.updated_at.isoformat()
        }
        
        return ApiResponse(
            success=True,
            message="Platform retrieved successfully",
            data=platform_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve platform: {str(e)}"
        )


@router.post("/", response_model=ApiResponse)
async def create_platform(
    platform_data: PlatformCreate,
    db: Session = Depends(get_database)
):
    """Create a new platform"""
    try:
        # Check if platform with this name already exists
        existing_platform = db.query(Platform).filter(
            Platform.name == platform_data.name
        ).first()
        
        if existing_platform:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Platform with this name already exists"
            )
        
        # Create new platform
        platform = Platform(
            name=platform_data.name,
            display_name=platform_data.display_name,
            base_url=platform_data.base_url,
            is_active=platform_data.is_active
        )
        
        db.add(platform)
        db.commit()
        db.refresh(platform)
        
        platform_response = {
            "id": platform.id,
            "name": platform.name,
            "display_name": platform.display_name,
            "base_url": platform.base_url,
            "is_active": platform.is_active,
            "created_at": platform.created_at.isoformat(),
            "updated_at": platform.updated_at.isoformat()
        }
        
        return ApiResponse(
            success=True,
            message="Platform created successfully",
            data=platform_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create platform: {str(e)}"
        )


@router.put("/{platform_id}", response_model=ApiResponse)
async def update_platform(
    platform_id: int,
    platform_data: PlatformUpdate,
    db: Session = Depends(get_database)
):
    """Update an existing platform"""
    try:
        platform = db.query(Platform).filter(Platform.id == platform_id).first()
        
        if not platform:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Platform not found"
            )
        
        # Update fields if provided
        update_data = platform_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(platform, field, value)
        
        db.commit()
        db.refresh(platform)
        
        platform_response = {
            "id": platform.id,
            "name": platform.name,
            "display_name": platform.display_name,
            "base_url": platform.base_url,
            "is_active": platform.is_active,
            "created_at": platform.created_at.isoformat(),
            "updated_at": platform.updated_at.isoformat()
        }
        
        return ApiResponse(
            success=True,
            message="Platform updated successfully",
            data=platform_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update platform: {str(e)}"
        )


@router.delete("/{platform_id}", response_model=ApiResponse)
async def delete_platform(
    platform_id: int,
    db: Session = Depends(get_database)
):
    """Delete a platform (soft delete by setting is_active to False)"""
    try:
        platform = db.query(Platform).filter(Platform.id == platform_id).first()
        
        if not platform:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Platform not found"
            )
        
        # Soft delete by setting is_active to False
        platform.is_active = False
        db.commit()
        
        return ApiResponse(
            success=True,
            message="Platform deactivated successfully",
            data={"id": platform_id, "is_active": False}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete platform: {str(e)}"
        ) 