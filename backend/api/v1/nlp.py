"""
NLP API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Body
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
import logging

from db.database import get_db
from db.models import Post, PlatformType
from services.nlp_service import NLPService
from analytics.nlp_analyzer import NLPAnalyzer

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/analyze/text", response_model=Dict[str, Any])
async def analyze_text(
    text: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Analyze text content using NLP
    
    Args:
        text: Text content to analyze
        
    Returns:
        Dict: NLP analysis results
    """
    try:
        nlp_service = NLPService()
        result = nlp_service.analyze_text(text)
        
        return result.to_dict()
    
    except Exception as e:
        logger.error(f"Error analyzing text: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error analyzing text: {str(e)}"
        )


@router.get("/analyze/post/{post_id}", response_model=Dict[str, Any])
async def analyze_post(
    post_id: int,
    db: Session = Depends(get_db)
):
    """
    Analyze a post's text content using NLP
    
    Args:
        post_id: ID of the post to analyze
        
    Returns:
        Dict: NLP analysis results
    """
    try:
        # Get the post from the database
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(
                status_code=404,
                detail=f"Post with ID {post_id} not found"
            )
        
        # Create NLP analyzer and analyze the post
        nlp_analyzer = NLPAnalyzer()
        result = nlp_analyzer.analyze_post(post)
        
        # Extract content features
        features = nlp_analyzer.extract_content_features(post)
        
        # Calculate content quality score
        quality_score = nlp_analyzer.calculate_content_quality_score(result)
        
        # Identify content patterns
        patterns = nlp_analyzer.identify_content_patterns(result)
        
        return {
            "post_id": post_id,
            "analysis": result,
            "content_features": features,
            "quality_score": quality_score,
            "patterns": patterns
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error analyzing post {post_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error analyzing post: {str(e)}"
        )


@router.get("/analyze/platform/{platform}", response_model=Dict[str, Any])
async def analyze_platform_sentiment(
    platform: PlatformType,
    limit: int = Query(10, description="Maximum number of posts to analyze"),
    db: Session = Depends(get_db)
):
    """
    Analyze sentiment trends for a specific platform
    
    Args:
        platform: Platform to analyze
        limit: Maximum number of posts to analyze
        
    Returns:
        Dict: Sentiment analysis summary
    """
    try:
        # Get recent posts from the platform
        posts = db.query(Post).filter(
            Post.platform == platform
        ).order_by(
            Post.publish_date.desc()
        ).limit(limit).all()
        
        if not posts:
            return {
                "platform": platform.value,
                "post_count": 0,
                "sentiment_summary": {
                    "positive": 0,
                    "neutral": 0,
                    "negative": 0
                },
                "average_sentiment_score": 0,
                "top_keywords": [],
                "top_topics": []
            }
        
        # Initialize NLP components
        nlp_service = NLPService()
        nlp_analyzer = NLPAnalyzer()
        
        # Analyze each post
        sentiment_scores = []
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        all_keywords = {}
        all_topics = {}
        
        for post in posts:
            # Analyze the post
            result = nlp_analyzer.analyze_post(post)
            
            # Track sentiment
            sentiment = result.get("sentiment", {})
            sentiment_label = sentiment.get("label", "neutral")
            sentiment_score = sentiment.get("score", 0)
            
            sentiment_counts[sentiment_label] = sentiment_counts.get(sentiment_label, 0) + 1
            sentiment_scores.append(sentiment_score)
            
            # Track keywords
            for keyword in result.get("keywords", []):
                keyword_text = keyword.get("keyword")
                relevance = keyword.get("relevance", 0)
                if keyword_text:
                    if keyword_text in all_keywords:
                        all_keywords[keyword_text]["count"] += 1
                        all_keywords[keyword_text]["relevance"] += relevance
                    else:
                        all_keywords[keyword_text] = {
                            "count": 1,
                            "relevance": relevance
                        }
            
            # Track topics
            for topic in result.get("topics", []):
                topic_name = topic.get("name")
                relevance = topic.get("relevance", 0)
                if topic_name:
                    if topic_name in all_topics:
                        all_topics[topic_name]["count"] += 1
                        all_topics[topic_name]["relevance"] += relevance
                    else:
                        all_topics[topic_name] = {
                            "count": 1,
                            "relevance": relevance
                        }
        
        # Calculate average sentiment
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        # Get top keywords
        sorted_keywords = sorted(
            all_keywords.items(),
            key=lambda x: (x[1]["count"], x[1]["relevance"]),
            reverse=True
        )
        top_keywords = [
            {"keyword": k, "count": v["count"], "relevance": v["relevance"] / v["count"]}
            for k, v in sorted_keywords[:10]
        ]
        
        # Get top topics
        sorted_topics = sorted(
            all_topics.items(),
            key=lambda x: (x[1]["count"], x[1]["relevance"]),
            reverse=True
        )
        top_topics = [
            {"topic": k, "count": v["count"], "relevance": v["relevance"] / v["count"]}
            for k, v in sorted_topics[:5]
        ]
        
        return {
            "platform": platform.value,
            "post_count": len(posts),
            "sentiment_summary": sentiment_counts,
            "average_sentiment_score": avg_sentiment,
            "top_keywords": top_keywords,
            "top_topics": top_topics
        }
    
    except Exception as e:
        logger.error(f"Error analyzing platform sentiment: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error analyzing platform sentiment: {str(e)}"
        )


@router.post("/batch/analyze", response_model=Dict[str, Any])
async def batch_analyze_posts(
    post_ids: List[int] = Body(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Analyze multiple posts in batch
    
    Args:
        post_ids: List of post IDs to analyze
        
    Returns:
        Dict: Status of the batch analysis request
    """
    try:
        # Verify posts exist
        existing_posts = db.query(Post.id).filter(Post.id.in_(post_ids)).all()
        existing_ids = [p.id for p in existing_posts]
        
        missing_ids = [pid for pid in post_ids if pid not in existing_ids]
        if missing_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Posts with IDs {missing_ids} not found"
            )
        
        # If we have background tasks, run analysis in background
        if background_tasks:
            background_tasks.add_task(_batch_analyze_posts, existing_ids, db)
            
            return {
                "status": "processing",
                "message": f"Batch analysis of {len(existing_ids)} posts started",
                "post_ids": existing_ids
            }
        
        # Otherwise, run analysis synchronously
        results = []
        nlp_analyzer = NLPAnalyzer()
        
        for post_id in existing_ids:
            post = db.query(Post).filter(Post.id == post_id).first()
            if post:
                result = nlp_analyzer.analyze_post(post)
                results.append({
                    "post_id": post_id,
                    "analysis": result
                })
        
        return {
            "status": "completed",
            "message": f"Analyzed {len(results)} posts",
            "results": results
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error in batch analysis: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error in batch analysis: {str(e)}"
        )


async def _batch_analyze_posts(post_ids: List[int], db: Session):
    """
    Background task for batch analyzing posts
    
    Args:
        post_ids: List of post IDs to analyze
        db: Database session
    """
    try:
        nlp_analyzer = NLPAnalyzer()
        
        for post_id in post_ids:
            try:
                post = db.query(Post).filter(Post.id == post_id).first()
                if post:
                    nlp_analyzer.analyze_post(post)
                    logger.info(f"Completed NLP analysis for post {post_id}")
            except Exception as e:
                logger.error(f"Error analyzing post {post_id}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error in background batch analysis: {str(e)}")
