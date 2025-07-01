"""
API endpoints for the feedback system
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from db.database import get_db
from db.models import FeedbackData, Post, AnalyticsData
from analytics.feedback_loop import FeedbackLoop

router = APIRouter(
    prefix="/api/v1/feedback",
    tags=["feedback"],
    responses={404: {"description": "Not found"}},
)


class FeedbackSubmission(BaseModel):
    """Feedback submission model"""
    post_id: int
    pattern_name: str
    is_positive: bool
    comment: Optional[str] = None


@router.post("/submit")
async def submit_feedback(
    feedback: FeedbackSubmission,
    db: Session = Depends(get_db)
):
    """
    Submit feedback for a pattern detection
    
    - **post_id**: ID of the post
    - **pattern_name**: Name of the pattern
    - **is_positive**: Whether the feedback is positive (pattern correctly detected)
    - **comment**: Optional comment
    """
    try:
        # Check if post exists
        post = db.query(Post).filter(Post.id == feedback.post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail=f"Post with ID {feedback.post_id} not found")
        
        # Check if pattern exists in post analytics
        analytics = db.query(AnalyticsData).filter(AnalyticsData.post_id == feedback.post_id).first()
        if not analytics or not analytics.success_patterns:
            raise HTTPException(status_code=404, detail=f"No patterns found for post with ID {feedback.post_id}")
        
        # Check if the specified pattern exists
        pattern_exists = any(
            p.get("name") == feedback.pattern_name 
            for p in analytics.success_patterns 
            if isinstance(p, dict) and "name" in p
        )
        
        if not pattern_exists:
            raise HTTPException(
                status_code=404, 
                detail=f"Pattern '{feedback.pattern_name}' not found in post with ID {feedback.post_id}"
            )
        
        # Create feedback record
        feedback_data = FeedbackData(
            post_id=feedback.post_id,
            pattern_name=feedback.pattern_name,
            is_positive=feedback.is_positive,
            comment=feedback.comment,
            created_at=datetime.utcnow()
        )
        
        # Save to database
        db.add(feedback_data)
        db.commit()
        
        return {
            "success": True,
            "feedback_id": feedback_data.id,
            "message": "Feedback submitted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error submitting feedback: {str(e)}")


@router.get("/performance")
async def get_performance_metrics(
    days: int = Query(30, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get performance metrics for pattern recognition
    
    - **days**: Number of days to look back (default: 30)
    """
    try:
        # Create feedback loop
        feedback_loop = FeedbackLoop(db)
        
        # Get performance history
        performance_history = feedback_loop.get_performance_history(days=days)
        
        if not performance_history["success"]:
            raise HTTPException(status_code=500, detail=performance_history["message"])
        
        return performance_history
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting performance metrics: {str(e)}")


@router.post("/collect-metrics")
async def collect_performance_metrics(
    days: int = Query(7, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Manually trigger collection of performance metrics
    
    - **days**: Number of days to look back (default: 7)
    """
    try:
        # Create feedback loop
        feedback_loop = FeedbackLoop(db)
        
        # Collect metrics
        metrics = feedback_loop.collect_performance_metrics(days=days)
        
        if "error" in metrics:
            raise HTTPException(status_code=500, detail=metrics["error"])
        
        return {
            "success": True,
            "metrics": metrics
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error collecting performance metrics: {str(e)}")


@router.post("/retrain")
async def retrain_models(
    db: Session = Depends(get_db)
):
    """
    Manually trigger model retraining if needed
    """
    try:
        # Create feedback loop
        feedback_loop = FeedbackLoop(db)
        
        # Check if retraining is needed and retrain
        result = feedback_loop.retrain_models_if_needed()
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "success": True,
            "retrained": result["retrained"],
            "reason": result.get("reason", ""),
            "training_result": result.get("training_result", {})
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retraining models: {str(e)}")


@router.get("/")
async def get_feedback(
    post_id: Optional[int] = Query(None, description="Filter by post ID"),
    pattern_name: Optional[str] = Query(None, description="Filter by pattern name"),
    days: int = Query(30, description="Number of days to look back"),
    is_positive: Optional[bool] = Query(None, description="Filter by positive/negative feedback"),
    db: Session = Depends(get_db)
):
    """
    Get feedback data with optional filters
    
    - **post_id**: Filter by post ID (optional)
    - **pattern_name**: Filter by pattern name (optional)
    - **days**: Number of days to look back (default: 30)
    - **is_positive**: Filter by positive/negative feedback (optional)
    """
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Build query
        query = db.query(FeedbackData).filter(
            FeedbackData.created_at >= start_date,
            FeedbackData.created_at <= end_date
        )
        
        # Apply filters
        if post_id is not None:
            query = query.filter(FeedbackData.post_id == post_id)
            
        if pattern_name is not None:
            query = query.filter(FeedbackData.pattern_name == pattern_name)
            
        if is_positive is not None:
            query = query.filter(FeedbackData.is_positive == is_positive)
        
        # Execute query
        feedback_data = query.all()
        
        # Convert to response format
        result = []
        for feedback in feedback_data:
            result.append({
                "id": feedback.id,
                "post_id": feedback.post_id,
                "pattern_name": feedback.pattern_name,
                "is_positive": feedback.is_positive,
                "comment": feedback.comment,
                "created_at": feedback.created_at.isoformat()
            })
        
        return {
            "success": True,
            "feedback": result,
            "count": len(result),
            "filters": {
                "post_id": post_id,
                "pattern_name": pattern_name,
                "days": days,
                "is_positive": is_positive
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting feedback data: {str(e)}")


@router.post("/apply")
async def apply_feedback(
    days: int = Query(30, description="Number of days of feedback to apply"),
    db: Session = Depends(get_db)
):
    """
    Apply collected feedback to improve pattern recognition
    
    - **days**: Number of days of feedback to apply (default: 30)
    """
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get feedback data
        feedback_data = db.query(FeedbackData).filter(
            FeedbackData.created_at >= start_date,
            FeedbackData.created_at <= end_date
        ).all()
        
        # Create feedback loop
        feedback_loop = FeedbackLoop(db)
        
        # Apply feedback
        result = feedback_loop.apply_feedback(feedback_data)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])
        
        return {
            "success": True,
            "message": result["message"],
            "applied": result["applied"],
            "feedback_count": len(feedback_data)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error applying feedback: {str(e)}")


@router.post("/schedule/start")
async def start_scheduled_tasks(
    db: Session = Depends(get_db)
):
    """
    Start scheduled feedback loop tasks
    """
    try:
        # Create feedback loop
        feedback_loop = FeedbackLoop(db)
        
        # Start scheduled tasks
        feedback_loop.start_scheduled_tasks()
        
        return {
            "success": True,
            "message": "Scheduled feedback loop tasks started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting scheduled tasks: {str(e)}")


@router.post("/schedule/stop")
async def stop_scheduled_tasks(
    db: Session = Depends(get_db)
):
    """
    Stop scheduled feedback loop tasks
    """
    try:
        # Create feedback loop
        feedback_loop = FeedbackLoop(db)
        
        # Stop scheduled tasks
        feedback_loop.stop_scheduled_tasks()
        
        return {
            "success": True,
            "message": "Scheduled feedback loop tasks stopped"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping scheduled tasks: {str(e)}") 