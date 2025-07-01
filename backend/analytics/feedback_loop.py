"""
Feedback Loop Module
Implements a feedback mechanism to continuously improve pattern recognition models
"""

import logging
import os
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import schedule
import threading
import time
from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import Post, AnalyticsData, FeedbackData, ModelPerformance
from .ml_pattern_predictor import MLPatternPredictor
from .pattern_recognizer import PatternRecognizer

logger = logging.getLogger(__name__)

# Directory for storing performance metrics
METRICS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'metrics')
os.makedirs(METRICS_DIR, exist_ok=True)


class FeedbackLoop:
    """
    Feedback Loop for continuously improving pattern recognition models
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize the feedback loop
        
        Args:
            db_session: Database session
        """
        self.db = db_session or SessionLocal()
        self.ml_predictor = MLPatternPredictor(self.db)
        self.pattern_recognizer = PatternRecognizer(self.db)
        self.scheduler = None
        
        logger.info("Feedback Loop initialized")
    
    def collect_performance_metrics(self, days: int = 7) -> Dict[str, Any]:
        """
        Collect performance metrics for pattern recognition models
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dict with performance metrics
        """
        try:
            # Get date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get ML model evaluation
            ml_evaluation = self.ml_predictor.evaluate_models()
            
            # Get rule-based model performance
            rule_based_metrics = self._evaluate_rule_based_patterns(start_date, end_date)
            
            # Get user feedback metrics
            feedback_metrics = self._collect_user_feedback(start_date, end_date)
            
            # Combine metrics
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "ml_model_metrics": ml_evaluation.get("evaluation", {}),
                "rule_based_metrics": rule_based_metrics,
                "feedback_metrics": feedback_metrics
            }
            
            # Save metrics to database
            self._save_metrics_to_db(metrics)
            
            # Save metrics to file
            self._save_metrics_to_file(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting performance metrics: {str(e)}")
            return {
                "error": str(e)
            }
    
    def _evaluate_rule_based_patterns(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Evaluate rule-based pattern recognition performance
        
        Args:
            start_date: Start date for evaluation period
            end_date: End date for evaluation period
            
        Returns:
            Dict with rule-based performance metrics
        """
        try:
            # Get patterns by type
            patterns_by_type = {}
            
            # Query posts with analytics data
            query = self.db.query(Post, AnalyticsData).join(
                AnalyticsData
            ).filter(
                Post.publish_date >= start_date,
                Post.publish_date <= end_date,
                AnalyticsData.success_patterns.isnot(None)
            )
            
            results = query.all()
            
            # Count pattern occurrences
            total_posts = len(results)
            pattern_counts = {}
            
            for post, analytics in results:
                if not analytics.success_patterns:
                    continue
                    
                for pattern in analytics.success_patterns:
                    if "name" in pattern:
                        pattern_name = pattern["name"]
                        if pattern_name not in pattern_counts:
                            pattern_counts[pattern_name] = 0
                        pattern_counts[pattern_name] += 1
            
            # Calculate pattern frequencies
            pattern_frequencies = {}
            for pattern_name, count in pattern_counts.items():
                pattern_frequencies[pattern_name] = count / total_posts if total_posts > 0 else 0
            
            # Get top patterns
            top_patterns = sorted(
                pattern_frequencies.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            return {
                "total_posts": total_posts,
                "pattern_counts": pattern_counts,
                "pattern_frequencies": pattern_frequencies,
                "top_patterns": dict(top_patterns)
            }
            
        except Exception as e:
            logger.error(f"Error evaluating rule-based patterns: {str(e)}")
            return {}
    
    def _collect_user_feedback(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Collect user feedback metrics
        
        Args:
            start_date: Start date for feedback period
            end_date: End date for feedback period
            
        Returns:
            Dict with user feedback metrics
        """
        try:
            # Query feedback data
            query = self.db.query(FeedbackData).filter(
                FeedbackData.created_at >= start_date,
                FeedbackData.created_at <= end_date
            )
            
            feedback_data = query.all()
            
            # Count feedback types
            total_feedback = len(feedback_data)
            positive_feedback = sum(1 for f in feedback_data if f.is_positive)
            negative_feedback = total_feedback - positive_feedback
            
            # Count feedback by pattern type
            pattern_feedback = {}
            
            for feedback in feedback_data:
                if feedback.pattern_name:
                    if feedback.pattern_name not in pattern_feedback:
                        pattern_feedback[feedback.pattern_name] = {
                            "positive": 0,
                            "negative": 0
                        }
                    
                    if feedback.is_positive:
                        pattern_feedback[feedback.pattern_name]["positive"] += 1
                    else:
                        pattern_feedback[feedback.pattern_name]["negative"] += 1
            
            # Calculate accuracy by pattern
            pattern_accuracy = {}
            for pattern_name, counts in pattern_feedback.items():
                total = counts["positive"] + counts["negative"]
                pattern_accuracy[pattern_name] = counts["positive"] / total if total > 0 else 0
            
            return {
                "total_feedback": total_feedback,
                "positive_feedback": positive_feedback,
                "negative_feedback": negative_feedback,
                "pattern_feedback": pattern_feedback,
                "pattern_accuracy": pattern_accuracy
            }
            
        except Exception as e:
            logger.error(f"Error collecting user feedback: {str(e)}")
            return {}
    
    def _save_metrics_to_db(self, metrics: Dict[str, Any]):
        """
        Save performance metrics to database
        
        Args:
            metrics: Performance metrics
        """
        try:
            # Create new model performance record
            model_performance = ModelPerformance(
                timestamp=datetime.utcnow(),
                metrics=metrics,
                ml_model_accuracy=self._get_average_metric(metrics.get("ml_model_metrics", {}), "accuracy"),
                rule_based_accuracy=self._calculate_rule_accuracy(metrics.get("feedback_metrics", {})),
                feedback_count=metrics.get("feedback_metrics", {}).get("total_feedback", 0)
            )
            
            # Add to database
            self.db.add(model_performance)
            self.db.commit()
            
            logger.info(f"Saved performance metrics to database (ID: {model_performance.id})")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving metrics to database: {str(e)}")
    
    def _save_metrics_to_file(self, metrics: Dict[str, Any]):
        """
        Save performance metrics to file
        
        Args:
            metrics: Performance metrics
        """
        try:
            # Create filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"metrics_{timestamp}.json"
            filepath = os.path.join(METRICS_DIR, filename)
            
            # Write metrics to file
            with open(filepath, 'w') as f:
                json.dump(metrics, f, indent=2)
                
            logger.info(f"Saved performance metrics to file: {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving metrics to file: {str(e)}")
    
    def _get_average_metric(self, metrics: Dict[str, Any], metric_name: str) -> float:
        """
        Calculate average value for a specific metric across all models
        
        Args:
            metrics: Metrics dictionary
            metric_name: Name of the metric to average
            
        Returns:
            Average metric value
        """
        try:
            if not metrics:
                return 0.0
                
            values = []
            for model_name, model_metrics in metrics.items():
                if metric_name in model_metrics:
                    values.append(model_metrics[metric_name])
            
            return sum(values) / len(values) if values else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating average metric: {str(e)}")
            return 0.0
    
    def _calculate_rule_accuracy(self, feedback_metrics: Dict[str, Any]) -> float:
        """
        Calculate rule-based pattern accuracy from feedback
        
        Args:
            feedback_metrics: Feedback metrics
            
        Returns:
            Rule-based accuracy
        """
        try:
            positive = feedback_metrics.get("positive_feedback", 0)
            total = feedback_metrics.get("total_feedback", 0)
            
            return positive / total if total > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating rule accuracy: {str(e)}")
            return 0.0
    
    def retrain_models_if_needed(self) -> Dict[str, Any]:
        """
        Check if models need retraining and retrain if necessary
        
        Returns:
            Dict with retraining results
        """
        try:
            # Get latest performance metrics
            latest_metrics = self._get_latest_performance_metrics()
            
            # Check if retraining is needed
            needs_retraining = self._check_if_retraining_needed(latest_metrics)
            
            if needs_retraining:
                logger.info("Retraining models based on performance metrics")
                
                # Retrain ML models
                training_result = self.ml_predictor.train_models(days=90)
                
                return {
                    "retrained": True,
                    "reason": needs_retraining,
                    "training_result": training_result
                }
            else:
                return {
                    "retrained": False,
                    "reason": "Models performing adequately"
                }
            
        except Exception as e:
            logger.error(f"Error checking if retraining is needed: {str(e)}")
            return {
                "retrained": False,
                "error": str(e)
            }
    
    def _get_latest_performance_metrics(self) -> Dict[str, Any]:
        """
        Get the latest performance metrics from the database
        
        Returns:
            Dict with latest performance metrics
        """
        try:
            # Query latest model performance record
            latest_performance = self.db.query(ModelPerformance).order_by(
                ModelPerformance.timestamp.desc()
            ).first()
            
            if latest_performance and latest_performance.metrics:
                return latest_performance.metrics
            else:
                return {}
            
        except Exception as e:
            logger.error(f"Error getting latest performance metrics: {str(e)}")
            return {}
    
    def _check_if_retraining_needed(self, metrics: Dict[str, Any]) -> Union[str, bool]:
        """
        Check if models need retraining based on performance metrics
        
        Args:
            metrics: Performance metrics
            
        Returns:
            Reason for retraining if needed, False otherwise
        """
        try:
            if not metrics:
                return "No previous metrics available"
            
            # Check ML model accuracy
            ml_metrics = metrics.get("ml_model_metrics", {})
            avg_accuracy = self._get_average_metric(ml_metrics, "accuracy")
            
            if avg_accuracy < 0.7:
                return f"Low ML model accuracy: {avg_accuracy:.2f}"
            
            # Check feedback metrics
            feedback_metrics = metrics.get("feedback_metrics", {})
            positive_ratio = feedback_metrics.get("positive_feedback", 0) / feedback_metrics.get("total_feedback", 1)
            
            if positive_ratio < 0.6 and feedback_metrics.get("total_feedback", 0) >= 20:
                return f"Low positive feedback ratio: {positive_ratio:.2f}"
            
            # Check if any pattern has particularly low accuracy
            pattern_accuracy = feedback_metrics.get("pattern_accuracy", {})
            for pattern, accuracy in pattern_accuracy.items():
                if accuracy < 0.5:
                    return f"Low accuracy for pattern '{pattern}': {accuracy:.2f}"
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if retraining is needed: {str(e)}")
            return False
    
    def apply_feedback(self, feedback_data: List[FeedbackData]) -> Dict[str, Any]:
        """
        Apply user feedback to improve pattern recognition
        
        Args:
            feedback_data: List of feedback data
            
        Returns:
            Dict with results of applying feedback
        """
        try:
            if not feedback_data:
                return {
                    "success": True,
                    "message": "No feedback to apply",
                    "applied": 0
                }
            
            # Group feedback by pattern
            pattern_feedback = {}
            for feedback in feedback_data:
                if feedback.pattern_name not in pattern_feedback:
                    pattern_feedback[feedback.pattern_name] = []
                pattern_feedback[feedback.pattern_name].append(feedback)
            
            # Apply feedback to each pattern
            applied_count = 0
            for pattern_name, feedbacks in pattern_feedback.items():
                # Calculate positive ratio
                positive = sum(1 for f in feedbacks if f.is_positive)
                total = len(feedbacks)
                positive_ratio = positive / total if total > 0 else 0
                
                # Apply feedback based on ratio
                if positive_ratio < 0.3 and total >= 5:
                    # Pattern is performing poorly, adjust threshold
                    self._adjust_pattern_threshold(pattern_name, 0.1)  # Increase threshold
                    applied_count += 1
                elif positive_ratio > 0.9 and total >= 5:
                    # Pattern is performing well, adjust threshold
                    self._adjust_pattern_threshold(pattern_name, -0.05)  # Decrease threshold
                    applied_count += 1
            
            return {
                "success": True,
                "message": f"Applied feedback to {applied_count} patterns",
                "applied": applied_count
            }
            
        except Exception as e:
            logger.error(f"Error applying feedback: {str(e)}")
            return {
                "success": False,
                "message": f"Error applying feedback: {str(e)}",
                "applied": 0
            }
    
    def _adjust_pattern_threshold(self, pattern_name: str, adjustment: float):
        """
        Adjust confidence threshold for a pattern rule
        
        Args:
            pattern_name: Name of the pattern
            adjustment: Amount to adjust threshold (positive increases, negative decreases)
        """
        try:
            # Check if pattern exists in rules
            if pattern_name in self.pattern_recognizer.rules:
                rule = self.pattern_recognizer.rules[pattern_name]
                
                # Adjust threshold within bounds
                new_threshold = min(max(0.5, rule.confidence_threshold + adjustment), 0.95)
                
                # Update threshold
                rule.confidence_threshold = new_threshold
                
                logger.info(f"Adjusted threshold for pattern '{pattern_name}': {new_threshold:.2f}")
            else:
                logger.warning(f"Pattern '{pattern_name}' not found in rules")
                
        except Exception as e:
            logger.error(f"Error adjusting pattern threshold: {str(e)}")
    
    def start_scheduled_tasks(self):
        """Start scheduled feedback loop tasks"""
        try:
            # Schedule daily performance metrics collection
            schedule.every().day.at("03:00").do(self.collect_performance_metrics)
            
            # Schedule weekly model retraining check
            schedule.every().monday.at("04:00").do(self.retrain_models_if_needed)
            
            # Start scheduler in a separate thread
            self.scheduler = threading.Thread(target=self._run_scheduler)
            self.scheduler.daemon = True
            self.scheduler.start()
            
            logger.info("Started scheduled feedback loop tasks")
            
        except Exception as e:
            logger.error(f"Error starting scheduled tasks: {str(e)}")
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    def stop_scheduled_tasks(self):
        """Stop scheduled feedback loop tasks"""
        try:
            # Clear all scheduled jobs
            schedule.clear()
            
            logger.info("Stopped scheduled feedback loop tasks")
            
        except Exception as e:
            logger.error(f"Error stopping scheduled tasks: {str(e)}")
    
    def get_performance_history(self, days: int = 30) -> Dict[str, Any]:
        """
        Get historical performance metrics
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dict with historical performance metrics
        """
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Query performance records
            query = self.db.query(ModelPerformance).filter(
                ModelPerformance.timestamp >= start_date,
                ModelPerformance.timestamp <= end_date
            ).order_by(ModelPerformance.timestamp.asc())
            
            performance_records = query.all()
            
            # Extract time series data
            timestamps = []
            ml_accuracy = []
            rule_accuracy = []
            feedback_counts = []
            
            for record in performance_records:
                timestamps.append(record.timestamp.isoformat())
                ml_accuracy.append(record.ml_model_accuracy)
                rule_accuracy.append(record.rule_based_accuracy)
                feedback_counts.append(record.feedback_count)
            
            return {
                "success": True,
                "days": days,
                "record_count": len(performance_records),
                "timestamps": timestamps,
                "ml_accuracy": ml_accuracy,
                "rule_accuracy": rule_accuracy,
                "feedback_counts": feedback_counts
            }
            
        except Exception as e:
            logger.error(f"Error getting performance history: {str(e)}")
            return {
                "success": False,
                "message": f"Error getting performance history: {str(e)}"
            } 