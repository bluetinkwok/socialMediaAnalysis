"""
Analytics API endpoints for performance metrics and analysis
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from db.database import get_database
from db.models import Post, AnalyticsData, PlatformType, TrendData
from db.schemas import ApiResponse
from analytics.engine import AnalyticsEngine
from analytics.trend_detector import TrendDetector, TrendType

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyze/{post_id}", response_model=ApiResponse)
async def analyze_post(
    post_id: int,
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Force re-analysis of already analyzed posts"),
    db: Session = Depends(get_database)
):
    """
    Analyze a specific post and calculate performance metrics
    
    Args:
        post_id: ID of the post to analyze
        force: Whether to force re-analysis of already analyzed posts
        db: Database session
    """
    try:
        # Check if post exists
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with ID {post_id} not found"
            )
        
        # Check if already analyzed and force flag
        if post.is_analyzed and not force:
            return ApiResponse(
                success=True,
                data={"post_id": post_id, "status": "already_analyzed"},
                message=f"Post {post_id} is already analyzed. Use force=true to re-analyze."
            )
        
        # Initialize analytics engine
        analytics_engine = AnalyticsEngine(db)
        
        # Run analysis
        result = analytics_engine.analyze_post(post_id)
        
        if result["success"]:
            return ApiResponse(
                success=True,
                data=result,
                message=f"Successfully analyzed post {post_id}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Analysis failed: {result.get('error', 'Unknown error')}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing post {post_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze post: {str(e)}"
        )


@router.post("/analyze/batch", response_model=ApiResponse)
async def analyze_batch_posts(
    post_ids: List[int],
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Force re-analysis of already analyzed posts"),
    db: Session = Depends(get_database)
):
    """
    Analyze multiple posts in batch
    
    Args:
        post_ids: List of post IDs to analyze
        force: Whether to force re-analysis of already analyzed posts
        db: Database session
    """
    try:
        # Validate post IDs
        if len(post_ids) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 posts can be analyzed in a single batch"
            )
        
        # Check which posts exist
        existing_posts = db.query(Post.id).filter(Post.id.in_(post_ids)).all()
        existing_ids = {post.id for post in existing_posts}
        missing_ids = set(post_ids) - existing_ids
        
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Posts not found: {list(missing_ids)}"
            )
        
        # Filter out already analyzed posts if not forcing
        if not force:
            analyzed_posts = db.query(Post.id).filter(
                Post.id.in_(post_ids),
                Post.is_analyzed == True
            ).all()
            analyzed_ids = {post.id for post in analyzed_posts}
            post_ids = [pid for pid in post_ids if pid not in analyzed_ids]
            
            if not post_ids:
                return ApiResponse(
                    success=True,
                    data={"analyzed_ids": list(analyzed_ids), "skipped": len(analyzed_ids)},
                    message="All posts are already analyzed. Use force=true to re-analyze."
                )
        
        # Initialize analytics engine
        analytics_engine = AnalyticsEngine(db)
        
        # Run batch analysis
        results = analytics_engine.analyze_batch_posts(post_ids)
        
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        
        return ApiResponse(
            success=True,
            data={
                "total_requested": len(post_ids),
                "successful": len(successful),
                "failed": len(failed),
                "results": results
            },
            message=f"Batch analysis completed: {len(successful)}/{len(post_ids)} successful"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch analysis failed: {str(e)}"
        )


@router.post("/analyze/unprocessed", response_model=ApiResponse)
async def analyze_unprocessed_posts(
    background_tasks: BackgroundTasks,
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of posts to process"),
    platform: Optional[PlatformType] = Query(None, description="Filter by platform"),
    db: Session = Depends(get_database)
):
    """
    Analyze all unprocessed posts or posts from a specific platform
    
    Args:
        limit: Maximum number of posts to process
        platform: Optional platform filter
        db: Database session
    """
    try:
        # Initialize analytics engine
        analytics_engine = AnalyticsEngine(db)
        
        if platform:
            # Analyze posts from specific platform
            results = analytics_engine.analyze_platform_posts(platform, limit)
            message = f"Analyzed unprocessed {platform.value} posts"
        else:
            # Analyze all unprocessed posts
            results = analytics_engine.analyze_unprocessed_posts(limit)
            message = "Analyzed unprocessed posts"
        
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        
        return ApiResponse(
            success=True,
            data={
                "total_processed": len(results),
                "successful": len(successful),
                "failed": len(failed),
                "results": results
            },
            message=f"{message}: {len(successful)}/{len(results)} successful"
        )
    
    except Exception as e:
        logger.error(f"Error analyzing unprocessed posts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze unprocessed posts: {str(e)}"
        )


@router.get("/{post_id}", response_model=ApiResponse)
async def get_post_analytics(
    post_id: int,
    detailed: bool = Query(False, description="Include detailed breakdown"),
    db: Session = Depends(get_database)
):
    """
    Get analytics data for a specific post
    
    Args:
        post_id: ID of the post
        detailed: Whether to include detailed score breakdown
        db: Database session
    """
    try:
        # Get post with analytics data
        post = db.query(Post).options(
            joinedload(Post.platform)
        ).filter(Post.id == post_id).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with ID {post_id} not found"
            )
        
        # Get analytics data
        analytics_data = db.query(AnalyticsData).filter(
            AnalyticsData.post_id == post_id
        ).first()
        
        if not analytics_data:
            return ApiResponse(
                success=True,
                data={
                    "post_id": post_id,
                    "analyzed": False,
                    "message": "Post has not been analyzed yet"
                },
                message=f"No analytics data found for post {post_id}"
            )
        
        # Prepare response data
        response_data = {
            "post_id": post_id,
            "analyzed": True,
            "performance_score": analytics_data.performance_score,
            "engagement_rate": analytics_data.engagement_rate,
            "analyzed_at": analytics_data.analyzed_at,
            "algorithm_version": analytics_data.algorithm_version
        }
        
        if detailed:
            response_data.update({
                "advanced_metrics": {
                    "virality_score": analytics_data.virality_score,
                    "trend_score": analytics_data.trend_score,
                    "engagement_velocity": analytics_data.engagement_velocity,
                    "content_quality_score": analytics_data.content_quality_score,
                    "audience_reach_score": analytics_data.audience_reach_score,
                    "interaction_depth_score": analytics_data.interaction_depth_score
                },
                "scoring_breakdown": {
                    "weighted_components": analytics_data.weighted_components,
                    "applied_bonuses": analytics_data.applied_bonuses,
                    "applied_penalties": analytics_data.applied_penalties,
                    "platform_adjustment": analytics_data.platform_adjustment,
                    "confidence_score": analytics_data.confidence_score
                },
                "ranking": {
                    "platform_rank": analytics_data.platform_rank,
                    "category_rank": analytics_data.category_rank,
                    "overall_rank": analytics_data.overall_rank
                },
                "metadata": {
                    "success_patterns": analytics_data.success_patterns,
                    "content_features": analytics_data.content_features,
                    "processing_duration": analytics_data.processing_duration,
                    "data_quality_flags": analytics_data.data_quality_flags
                }
            })
        
        return ApiResponse(
            success=True,
            data=response_data,
            message=f"Retrieved analytics for post {post_id}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analytics for post {post_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analytics: {str(e)}"
        )


@router.get("/", response_model=ApiResponse)
async def get_analytics_list(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    platform: Optional[PlatformType] = Query(None, description="Filter by platform"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum performance score"),
    max_score: Optional[float] = Query(None, ge=0, le=100, description="Maximum performance score"),
    sort_by: str = Query("performance_score", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_database)
):
    """
    Get list of analytics data with filtering and pagination
    
    Args:
        skip: Number of records to skip for pagination
        limit: Number of records to return
        platform: Optional platform filter
        min_score: Minimum performance score filter
        max_score: Maximum performance score filter  
        sort_by: Field to sort by
        sort_order: Sort order (asc or desc)
        db: Database session
    """
    try:
        # Build query
        query = db.query(AnalyticsData).join(Post).options(
            joinedload(AnalyticsData.post).joinedload(Post.platform)
        )
        
        # Apply filters
        if platform:
            query = query.filter(Post.platform.has(platform_type=platform))
        
        if min_score is not None:
            query = query.filter(AnalyticsData.performance_score >= min_score)
        
        if max_score is not None:
            query = query.filter(AnalyticsData.performance_score <= max_score)
        
        # Get total count
        total = query.count()
        
        # Apply sorting
        sort_field = getattr(AnalyticsData, sort_by, AnalyticsData.performance_score)
        if sort_order == "desc":
            query = query.order_by(sort_field.desc())
        else:
            query = query.order_by(sort_field.asc())
        
        # Apply pagination
        analytics_records = query.offset(skip).limit(limit).all()
        
        # Format response
        records_data = []
        for record in analytics_records:
            record_data = {
                "id": record.id,
                "post_id": record.post_id,
                "performance_score": record.performance_score,
                "engagement_rate": record.engagement_rate,
                "platform": record.post.platform.platform_type.value if record.post.platform else None,
                "analyzed_at": record.analyzed_at,
                "algorithm_version": record.algorithm_version
            }
            records_data.append(record_data)
        
        return ApiResponse(
            success=True,
            data={
                "analytics": records_data,
                "total": total,
                "skip": skip,
                "limit": limit,
                "filters_applied": {
                    "platform": platform.value if platform else None,
                    "min_score": min_score,
                    "max_score": max_score,
                    "sort_by": sort_by,
                    "sort_order": sort_order
                }
            },
            message=f"Retrieved {len(records_data)} analytics records"
        )
    
    except Exception as e:
        logger.error(f"Error retrieving analytics list: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analytics list: {str(e)}"
        )


@router.get("/summary/overview", response_model=ApiResponse)
async def get_analytics_overview(
    platform: Optional[PlatformType] = Query(None, description="Filter by platform"),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    db: Session = Depends(get_database)
):
    """
    Get analytics overview and summary statistics
    
    Args:
        platform: Optional platform filter
        days: Number of days to include in the analysis
        db: Database session
    """
    try:
        # Initialize analytics engine
        analytics_engine = AnalyticsEngine(db)
        
        # Get analytics summary
        summary = analytics_engine.get_analytics_summary(platform)
        
        # Add time-based filtering for recent analysis
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = db.query(AnalyticsData).join(Post)
        if platform:
            query = query.filter(Post.platform.has(platform_type=platform))
        
        query = query.filter(AnalyticsData.analyzed_at >= cutoff_date)
        
        recent_analytics = query.all()
        
        if recent_analytics:
            recent_scores = [a.performance_score for a in recent_analytics if a.performance_score]
            recent_engagement = [a.engagement_rate for a in recent_analytics if a.engagement_rate]
            
            summary.update({
                "recent_period": {
                    "days": days,
                    "total_analyzed": len(recent_analytics),
                    "avg_performance_score": sum(recent_scores) / len(recent_scores) if recent_scores else 0,
                    "avg_engagement_rate": sum(recent_engagement) / len(recent_engagement) if recent_engagement else 0,
                    "top_performers": sorted(recent_scores, reverse=True)[:5] if recent_scores else []
                }
            })
        
        return ApiResponse(
            success=True,
            data=summary,
            message=f"Analytics overview generated for {platform.value if platform else 'all platforms'}"
        )
    
    except Exception as e:
        logger.error(f"Error generating analytics overview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate analytics overview: {str(e)}"
        )


@router.get("/top-performers/{platform_type}", response_model=ApiResponse)
async def get_top_performers(
    platform_type: PlatformType,
    limit: int = Query(10, ge=1, le=50, description="Number of top performers to return"),
    metric: str = Query("performance_score", description="Metric to rank by"),
    days: Optional[int] = Query(None, ge=1, le=365, description="Filter to posts from last N days"),
    db: Session = Depends(get_database)
):
    """
    Get top performing posts for a specific platform
    
    Args:
        platform_type: Platform to get top performers for
        limit: Number of top performers to return
        metric: Metric to rank by (performance_score, engagement_rate, etc.)
        days: Optional filter for recent posts only
        db: Database session
    """
    try:
        # Build query
        query = db.query(AnalyticsData).join(Post).options(
            joinedload(AnalyticsData.post).joinedload(Post.platform)
        ).filter(
            Post.platform.has(platform_type=platform_type)
        )
        
        # Apply time filter if specified
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            query = query.filter(Post.created_at >= cutoff_date)
        
        # Apply sorting by metric
        sort_field = getattr(AnalyticsData, metric, AnalyticsData.performance_score)
        query = query.order_by(sort_field.desc())
        
        # Get top performers
        top_performers = query.limit(limit).all()
        
        # Format response
        performers_data = []
        for record in top_performers:
            performer_data = {
                "post_id": record.post_id,
                "performance_score": record.performance_score,
                "engagement_rate": record.engagement_rate,
                "metric_value": getattr(record, metric, None),
                "post_title": record.post.title if record.post else None,
                "post_url": record.post.url if record.post else None,
                "analyzed_at": record.analyzed_at,
                "success_patterns": record.success_patterns
            }
            performers_data.append(performer_data)
        
        return ApiResponse(
            success=True,
            data={
                "platform": platform_type.value,
                "metric": metric,
                "period_days": days,
                "top_performers": performers_data,
                "total_found": len(performers_data)
            },
            message=f"Retrieved top {len(performers_data)} {platform_type.value} performers by {metric}"
        )
    
    except Exception as e:
        logger.error(f"Error retrieving top performers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve top performers: {str(e)}"
        )


@router.get("/trends/performance", response_model=ApiResponse)
async def get_performance_trends(
    window: str = Query("short", regex="^(realtime|short|medium|long)$"),
    platform: Optional[PlatformType] = None,
    content_type: Optional[ContentType] = None,
    db: Session = Depends(get_database)
):
    """
    Get posts with significantly higher performance scores
    
    Args:
        window: Analysis window ('realtime', 'short', 'medium', 'long')
        platform: Optional platform filter
        content_type: Optional content type filter
        db: Database session
    """
    try:
        trend_detector = TrendDetector(db)
        trends = trend_detector.detect_performance_trends(window, platform, content_type)
        
        return ApiResponse(
            success=True,
            data={
                "trends": trends,
                "window": window,
                "total": len(trends)
            },
            message=f"Found {len(trends)} performance trends"
        )
    except Exception as e:
        logger.error(f"Error detecting performance trends: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect performance trends: {str(e)}"
        )


@router.get("/trends/viral", response_model=ApiResponse)
async def get_viral_content(
    window: str = Query("realtime", regex="^(realtime|short|medium|long)$"),
    platform: Optional[PlatformType] = None,
    db: Session = Depends(get_database)
):
    """
    Get potentially viral content based on virality score and velocity
    
    Args:
        window: Analysis window ('realtime', 'short', 'medium', 'long')
        platform: Optional platform filter
        db: Database session
    """
    try:
        trend_detector = TrendDetector(db)
        trends = trend_detector.detect_viral_content(window, platform)
        
        return ApiResponse(
            success=True,
            data={
                "trends": trends,
                "window": window,
                "total": len(trends)
            },
            message=f"Found {len(trends)} viral content trends"
        )
    except Exception as e:
        logger.error(f"Error detecting viral content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect viral content: {str(e)}"
        )


@router.get("/trends/rising", response_model=ApiResponse)
async def get_rising_trends(
    window: str = Query("short", regex="^(realtime|short|medium|long)$"),
    platform: Optional[PlatformType] = None,
    db: Session = Depends(get_database)
):
    """
    Get content with rising engagement trends
    
    Args:
        window: Analysis window ('realtime', 'short', 'medium', 'long')
        platform: Optional platform filter
        db: Database session
    """
    try:
        trend_detector = TrendDetector(db)
        trends = trend_detector.detect_rising_trends(window, platform)
        
        return ApiResponse(
            success=True,
            data={
                "trends": trends,
                "window": window,
                "total": len(trends)
            },
            message=f"Found {len(trends)} rising trends"
        )
    except Exception as e:
        logger.error(f"Error detecting rising trends: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect rising trends: {str(e)}"
        )


@router.get("/trends/quality", response_model=ApiResponse)
async def get_quality_trends(
    window: str = Query("medium", regex="^(realtime|short|medium|long)$"),
    platform: Optional[PlatformType] = None,
    db: Session = Depends(get_database)
):
    """
    Get high-quality content trends
    
    Args:
        window: Analysis window ('realtime', 'short', 'medium', 'long')
        platform: Optional platform filter
        db: Database session
    """
    try:
        trend_detector = TrendDetector(db)
        trends = trend_detector.detect_quality_trends(window, platform)
        
        return ApiResponse(
            success=True,
            data={
                "trends": trends,
                "window": window,
                "total": len(trends)
            },
            message=f"Found {len(trends)} quality trends"
        )
    except Exception as e:
        logger.error(f"Error detecting quality trends: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect quality trends: {str(e)}"
        )


@router.get("/trends/hashtags", response_model=ApiResponse)
async def get_hashtag_trends(
    window: str = Query("short", regex="^(realtime|short|medium|long)$"),
    platform: Optional[PlatformType] = None,
    min_occurrences: int = Query(3, ge=1, description="Minimum occurrences to consider"),
    db: Session = Depends(get_database)
):
    """
    Get trending hashtags
    
    Args:
        window: Analysis window ('realtime', 'short', 'medium', 'long')
        platform: Optional platform filter
        min_occurrences: Minimum number of occurrences to consider
        db: Database session
    """
    try:
        trend_detector = TrendDetector(db)
        trends = trend_detector.detect_hashtag_trends(window, platform, min_occurrences)
        
        return ApiResponse(
            success=True,
            data={
                "trends": trends,
                "window": window,
                "total": len(trends)
            },
            message=f"Found {len(trends)} hashtag trends"
        )
    except Exception as e:
        logger.error(f"Error detecting hashtag trends: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect hashtag trends: {str(e)}"
        )


@router.get("/trends/patterns", response_model=ApiResponse)
async def get_content_patterns(
    window: str = Query("medium", regex="^(realtime|short|medium|long)$"),
    platform: Optional[PlatformType] = None,
    db: Session = Depends(get_database)
):
    """
    Get successful content patterns
    
    Args:
        window: Analysis window ('realtime', 'short', 'medium', 'long')
        platform: Optional platform filter
        db: Database session
    """
    try:
        trend_detector = TrendDetector(db)
        trends = trend_detector.detect_content_patterns(window, platform)
        
        return ApiResponse(
            success=True,
            data={
                "trends": trends,
                "window": window,
                "total": len(trends)
            },
            message=f"Found {len(trends)} content pattern trends"
        )
    except Exception as e:
        logger.error(f"Error detecting content patterns: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect content patterns: {str(e)}"
        )


@router.get("/trends/all", response_model=ApiResponse)
async def get_all_trends(
    window: str = Query("short", regex="^(realtime|short|medium|long)$"),
    platform: Optional[PlatformType] = None,
    db: Session = Depends(get_database)
):
    """
    Get all types of trends in a single request
    
    Args:
        window: Analysis window ('realtime', 'short', 'medium', 'long')
        platform: Optional platform filter
        db: Database session
    """
    try:
        trend_detector = TrendDetector(db)
        all_trends = trend_detector.analyze_all_trends(window, platform)
        
        total_trends = sum(len(trends) for trends in all_trends.values())
        
        return ApiResponse(
            success=True,
            data={
                "trends": all_trends,
                "window": window,
                "total": total_trends
            },
            message=f"Found {total_trends} total trends across all categories"
        )
    except Exception as e:
        logger.error(f"Error detecting all trends: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect all trends: {str(e)}"
        ) 