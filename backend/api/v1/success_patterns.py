"""
API endpoints for accessing success patterns
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from db.database import get_db
from db.models import Post, AnalyticsData, PlatformType, ContentType
from analytics.engine import AnalyticsEngine
from analytics.pattern_recognizer import PatternRecognizer
from analytics.ml_pattern_predictor import MLPatternPredictor

router = APIRouter(
    prefix="/api/v1/success-patterns",
    tags=["success-patterns"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
async def get_all_success_patterns(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    days: int = Query(30, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get all detected success patterns across posts
    
    - **platform**: Optional filter by platform (youtube, instagram, etc.)
    - **content_type**: Optional filter by content type (video, image, etc.)
    - **days**: Number of days to look back (default: 30)
    """
    try:
        # Create pattern recognizer
        pattern_recognizer = PatternRecognizer(db)
        
        # Convert string parameters to enums if provided
        platform_enum = None
        if platform:
            try:
                platform_enum = PlatformType(platform.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")
                
        content_type_enum = None
        if content_type:
            try:
                content_type_enum = ContentType(content_type.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid content type: {content_type}")
        
        # Get date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get success patterns
        patterns = pattern_recognizer.get_all_success_patterns(
            start_date=start_date,
            end_date=end_date,
            platform=platform_enum,
            content_type=content_type_enum
        )
        
        return {
            "success": True,
            "patterns": patterns,
            "count": len(patterns),
            "filters": {
                "platform": platform,
                "content_type": content_type,
                "days": days,
                "start_date": start_date,
                "end_date": end_date
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving success patterns: {str(e)}")


@router.get("/post/{post_id}")
async def get_post_success_patterns(
    post_id: int,
    db: Session = Depends(get_db)
):
    """
    Get success patterns for a specific post
    
    - **post_id**: ID of the post
    """
    try:
        # Check if post exists
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail=f"Post with ID {post_id} not found")
            
        # Get analytics data
        analytics = db.query(AnalyticsData).filter(AnalyticsData.post_id == post_id).first()
        if not analytics:
            # If no analytics data exists, analyze the post
            engine = AnalyticsEngine(db)
            result = engine.analyze_post(post_id)
            
            # Get fresh analytics data
            analytics = db.query(AnalyticsData).filter(AnalyticsData.post_id == post_id).first()
            
        # Return success patterns
        if analytics and analytics.success_patterns:
            return {
                "success": True,
                "post_id": post_id,
                "patterns": analytics.success_patterns,
                "count": len(analytics.success_patterns)
            }
        else:
            return {
                "success": True,
                "post_id": post_id,
                "patterns": [],
                "count": 0,
                "message": "No success patterns detected for this post"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving post success patterns: {str(e)}")


@router.get("/top")
async def get_top_success_patterns(
    limit: int = Query(10, description="Number of patterns to return"),
    days: int = Query(30, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get top success patterns by frequency
    
    - **limit**: Number of patterns to return (default: 10)
    - **days**: Number of days to look back (default: 30)
    """
    try:
        # Create pattern recognizer
        pattern_recognizer = PatternRecognizer(db)
        
        # Get date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get top patterns
        top_patterns = pattern_recognizer.get_top_patterns(
            limit=limit,
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "success": True,
            "patterns": top_patterns,
            "count": len(top_patterns),
            "filters": {
                "limit": limit,
                "days": days,
                "start_date": start_date,
                "end_date": end_date
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving top success patterns: {str(e)}")


@router.get("/by-platform")
async def get_patterns_by_platform(
    days: int = Query(30, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get success patterns grouped by platform
    
    - **days**: Number of days to look back (default: 30)
    """
    try:
        # Create pattern recognizer
        pattern_recognizer = PatternRecognizer(db)
        
        # Get date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get patterns by platform
        patterns_by_platform = pattern_recognizer.get_patterns_by_platform(
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "success": True,
            "patterns_by_platform": patterns_by_platform,
            "platforms_count": len(patterns_by_platform),
            "filters": {
                "days": days,
                "start_date": start_date,
                "end_date": end_date
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving patterns by platform: {str(e)}")


@router.get("/by-content-type")
async def get_patterns_by_content_type(
    days: int = Query(30, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get success patterns grouped by content type
    
    - **days**: Number of days to look back (default: 30)
    """
    try:
        # Create pattern recognizer
        pattern_recognizer = PatternRecognizer(db)
        
        # Get date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get patterns by content type
        patterns_by_content_type = pattern_recognizer.get_patterns_by_content_type(
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "success": True,
            "patterns_by_content_type": patterns_by_content_type,
            "content_types_count": len(patterns_by_content_type),
            "filters": {
                "days": days,
                "start_date": start_date,
                "end_date": end_date
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving patterns by content type: {str(e)}")


@router.post("/ml/train")
async def train_ml_pattern_models(
    days: int = Query(90, description="Number of days of data to use for training"),
    min_samples: int = Query(100, description="Minimum number of samples required for training"),
    db: Session = Depends(get_db)
):
    """
    Train machine learning models for pattern prediction
    
    - **days**: Number of days of data to use for training (default: 90)
    - **min_samples**: Minimum number of samples required for training (default: 100)
    """
    try:
        # Create ML pattern predictor
        ml_predictor = MLPatternPredictor(db)
        
        # Train models
        result = ml_predictor.train_models(days=days, min_samples=min_samples)
        
        if not result["success"]:
            return {
                "success": False,
                "message": result["message"]
            }
        
        return {
            "success": True,
            "training_results": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error training ML pattern models: {str(e)}")


@router.get("/ml/evaluate")
async def evaluate_ml_pattern_models(
    db: Session = Depends(get_db)
):
    """
    Evaluate machine learning models for pattern prediction
    """
    try:
        # Create ML pattern predictor
        ml_predictor = MLPatternPredictor(db)
        
        # Evaluate models
        result = ml_predictor.evaluate_models()
        
        if not result["success"]:
            return {
                "success": False,
                "message": result["message"]
            }
        
        return {
            "success": True,
            "evaluation_results": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating ML pattern models: {str(e)}")


@router.get("/ml/info")
async def get_ml_model_info(
    db: Session = Depends(get_db)
):
    """
    Get information about trained machine learning models for pattern prediction
    """
    try:
        # Create ML pattern predictor
        ml_predictor = MLPatternPredictor(db)
        
        # Get model info
        result = ml_predictor.get_model_info()
        
        if not result["success"]:
            return {
                "success": False,
                "message": result["message"]
            }
        
        return {
            "success": True,
            "model_info": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting ML model info: {str(e)}")


@router.post("/ml/predict")
async def predict_patterns_with_ml(
    features: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Predict success patterns using machine learning models
    
    Request body should contain post features including NLP and CV data
    """
    try:
        # Create ML pattern predictor
        ml_predictor = MLPatternPredictor(db)
        
        # Make predictions
        result = ml_predictor.predict_patterns(features)
        
        if not result["success"]:
            return {
                "success": False,
                "message": result["message"]
            }
        
        return {
            "success": True,
            "predicted_patterns": result["predicted_patterns"],
            "pattern_count": result["pattern_count"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error predicting patterns with ML: {str(e)}") 