"""
Posts API endpoints for content management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime

from db.database import get_database
from db.models import Post, MediaFile, Platform, PlatformType, ContentType
from db.schemas import (
    Post as PostSchema,
    PostCreate,
    PostUpdate,
    ApiResponse
)

router = APIRouter()


@router.get("/", response_model=ApiResponse)
async def get_posts(
    skip: int = Query(0, ge=0, description="Number of posts to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of posts to return"),
    platform: Optional[PlatformType] = Query(None, description="Filter by platform"),
    content_type: Optional[ContentType] = Query(None, description="Filter by content type"),
    search: Optional[str] = Query(None, description="Search in title and content"),
    db: Session = Depends(get_database)
):
    """Get all posts with optional filtering and pagination"""
    try:
        query = db.query(Post).options(
            joinedload(Post.platform),
            joinedload(Post.media_files)
        )
        
        # Apply filters
        if platform:
            query = query.join(Platform).filter(Platform.platform_type == platform)
        
        if content_type:
            query = query.filter(Post.content_type == content_type)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Post.title.ilike(search_term)) | 
                (Post.content.ilike(search_term))
            )
        
        # Get total count for pagination
        total = query.count()
        
        # Apply pagination and ordering
        posts = query.order_by(Post.created_at.desc()).offset(skip).limit(limit).all()
        
        # Convert to Pydantic models
        posts_data = [PostSchema.model_validate(post) for post in posts]
        
        return ApiResponse(
            success=True,
            data={
                "posts": posts_data,
                "total": total,
                "skip": skip,
                "limit": limit
            },
            message=f"Retrieved {len(posts_data)} posts"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve posts: {str(e)}"
        )


@router.get("/{post_id}", response_model=ApiResponse)
async def get_post(
    post_id: int,
    db: Session = Depends(get_database)
):
    """Get a specific post by ID"""
    try:
        post = db.query(Post).options(
            joinedload(Post.platform),
            joinedload(Post.media_files)
        ).filter(Post.id == post_id).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with ID {post_id} not found"
            )
        
        post_data = PostSchema.model_validate(post)
        
        return ApiResponse(
            success=True,
            data=post_data,
            message=f"Retrieved post {post_id}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve post: {str(e)}"
        )


@router.post("/", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: PostCreate,
    db: Session = Depends(get_database)
):
    """Create a new post"""
    try:
        # Verify platform exists
        platform = db.query(Platform).filter(Platform.id == post_data.platform_id).first()
        if not platform:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Platform with ID {post_data.platform_id} not found"
            )
        
        # Create new post
        db_post = Post(**post_data.model_dump())
        db.add(db_post)
        db.commit()
        db.refresh(db_post)
        
        # Load relationships for response
        post_with_relations = db.query(Post).options(
            joinedload(Post.platform),
            joinedload(Post.media_files)
        ).filter(Post.id == db_post.id).first()
        
        post_response = PostSchema.model_validate(post_with_relations)
        
        return ApiResponse(
            success=True,
            data=post_response,
            message=f"Post created successfully with ID {db_post.id}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create post: {str(e)}"
        )


@router.put("/{post_id}", response_model=ApiResponse)
async def update_post(
    post_id: int,
    post_update: PostUpdate,
    db: Session = Depends(get_database)
):
    """Update an existing post"""
    try:
        # Get existing post
        db_post = db.query(Post).filter(Post.id == post_id).first()
        if not db_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with ID {post_id} not found"
            )
        
        # Update fields
        update_data = post_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_post, field, value)
        
        db_post.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_post)
        
        # Load relationships for response
        post_with_relations = db.query(Post).options(
            joinedload(Post.platform),
            joinedload(Post.media_files)
        ).filter(Post.id == post_id).first()
        
        post_response = PostSchema.model_validate(post_with_relations)
        
        return ApiResponse(
            success=True,
            data=post_response,
            message=f"Post {post_id} updated successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update post: {str(e)}"
        )


@router.delete("/{post_id}", response_model=ApiResponse)
async def delete_post(
    post_id: int,
    db: Session = Depends(get_database)
):
    """Delete a post"""
    try:
        db_post = db.query(Post).filter(Post.id == post_id).first()
        if not db_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with ID {post_id} not found"
            )
        
        db.delete(db_post)
        db.commit()
        
        return ApiResponse(
            success=True,
            data={"deleted_post_id": post_id},
            message=f"Post {post_id} deleted successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete post: {str(e)}"
        )


@router.get("/platform/{platform_type}", response_model=ApiResponse)
async def get_posts_by_platform(
    platform_type: PlatformType,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_database)
):
    """Get posts filtered by platform type"""
    try:
        posts = db.query(Post).options(
            joinedload(Post.platform),
            joinedload(Post.media_files)
        ).join(Platform).filter(
            Platform.platform_type == platform_type
        ).order_by(Post.created_at.desc()).offset(skip).limit(limit).all()
        
        total = db.query(Post).join(Platform).filter(
            Platform.platform_type == platform_type
        ).count()
        
        posts_data = [PostSchema.model_validate(post) for post in posts]
        
        return ApiResponse(
            success=True,
            data={
                "posts": posts_data,
                "total": total,
                "platform": platform_type.value,
                "skip": skip,
                "limit": limit
            },
            message=f"Retrieved {len(posts_data)} posts from {platform_type.value}"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve posts for platform {platform_type.value}: {str(e)}"
        )


@router.get("/stats/summary", response_model=ApiResponse)
async def get_posts_summary(
    db: Session = Depends(get_database)
):
    """Get summary statistics for posts"""
    try:
        total_posts = db.query(Post).count()
        
        # Posts by platform
        platform_stats = db.query(
            Platform.platform_type,
            db.func.count(Post.id).label('count')
        ).join(Post).group_by(Platform.platform_type).all()
        
        # Posts by content type
        content_type_stats = db.query(
            Post.content_type,
            db.func.count(Post.id).label('count')
        ).group_by(Post.content_type).all()
        
        # Recent activity (last 7 days)
        from datetime import timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_posts = db.query(Post).filter(Post.created_at >= week_ago).count()
        
        return ApiResponse(
            success=True,
            data={
                "total_posts": total_posts,
                "platform_breakdown": {stat.platform_type.value: stat.count for stat in platform_stats},
                "content_type_breakdown": {stat.content_type.value: stat.count for stat in content_type_stats},
                "recent_posts_7_days": recent_posts
            },
            message="Posts summary retrieved successfully"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve posts summary: {str(e)}"
        ) 