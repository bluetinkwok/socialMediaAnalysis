"""
API endpoints for accessing actionable recommendations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from db.database import get_db
from db.models import Post, AnalyticsData, PlatformType, ContentType
from services.recommendation_engine import RecommendationEngine, RecommendationType

router = APIRouter(
    prefix="/api/v1/recommendations",
    tags=["recommendations"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
async def get_general_recommendations(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    days: int = Query(30, description="Number of days to look back"),
    limit: int = Query(5, description="Number of recommendations to return"),
    db: Session = Depends(get_db)
):
    """
    Get general actionable recommendations based on top success patterns
    
    - **platform**: Optional filter by platform (youtube, instagram, etc.)
    - **content_type**: Optional filter by content type (video, image, etc.)
    - **days**: Number of days to look back (default: 30)
    - **limit**: Number of recommendations to return (default: 5)
    """
    try:
        # Create recommendation engine
        recommendation_engine = RecommendationEngine(db)
        
        # Get recommendations
        result = recommendation_engine.get_general_recommendations(
            platform=platform,
            content_type=content_type,
            days=days,
            limit=limit
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving recommendations: {str(e)}")


@router.get("/post/{post_id}")
async def get_post_recommendations(
    post_id: int,
    limit: int = Query(5, description="Number of recommendations to return"),
    db: Session = Depends(get_db)
):
    """
    Get actionable recommendations for a specific post
    
    - **post_id**: ID of the post
    - **limit**: Number of recommendations to return (default: 5)
    """
    try:
        # Create recommendation engine
        recommendation_engine = RecommendationEngine(db)
        
        # Get recommendations for post
        result = recommendation_engine.get_recommendations_for_post(
            post_id=post_id,
            limit=limit
        )
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving post recommendations: {str(e)}")


@router.get("/types")
async def get_recommendation_types():
    """
    Get all available recommendation types
    """
    try:
        # Get all recommendation types
        types = vars(RecommendationType)
        
        # Filter out private attributes
        public_types = {k: v for k, v in types.items() if not k.startswith("_")}
        
        return {
            "success": True,
            "types": public_types
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving recommendation types: {str(e)}")


@router.get("/by-type/{recommendation_type}")
async def get_recommendations_by_type(
    recommendation_type: str,
    platform: Optional[str] = Query(None, description="Filter by platform"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    limit: int = Query(5, description="Number of recommendations to return"),
    db: Session = Depends(get_db)
):
    """
    Get recommendations filtered by type
    
    - **recommendation_type**: Type of recommendations to retrieve
    - **platform**: Optional filter by platform (youtube, instagram, etc.)
    - **content_type**: Optional filter by content type (video, image, etc.)
    - **limit**: Number of recommendations to return (default: 5)
    """
    try:
        # Create recommendation engine
        recommendation_engine = RecommendationEngine(db)
        
        # Get recommendations by type
        result = recommendation_engine.get_recommendations_by_type(
            recommendation_type=recommendation_type,
            platform=platform,
            content_type=content_type,
            limit=limit
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving recommendations by type: {str(e)}")


@router.post("/store")
async def store_recommendation(
    recommendation: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Store a recommendation for future reference
    
    Request body should contain the recommendation data
    """
    try:
        # Validate recommendation data
        required_fields = ["id", "type", "text", "impact_score", "source_pattern"]
        for field in required_fields:
            if field not in recommendation:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Create recommendation engine
        recommendation_engine = RecommendationEngine(db)
        
        # Store recommendation
        result = recommendation_engine.store_recommendation(recommendation)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error storing recommendation: {str(e)}") 