"""
Machine Learning Pattern Predictor Module
Implements ML models for predicting success patterns based on combined AI insights
"""

import logging
import pickle
import os
from typing import Dict, List, Optional, Any, Union, Tuple
import numpy as np
from datetime import datetime, timedelta
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sqlalchemy.orm import Session

from db.models import Post, AnalyticsData, PlatformType, ContentType
from db.database import SessionLocal
from .pattern_recognizer import PatternRecognizer

logger = logging.getLogger(__name__)

# Directory for storing ML models
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
os.makedirs(MODEL_DIR, exist_ok=True)


class MLPatternPredictor:
    """
    Machine Learning Pattern Predictor for identifying and predicting success patterns
    using combined NLP and CV insights
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize the ML Pattern Predictor
        
        Args:
            db_session: Database session
        """
        self.db = db_session or SessionLocal()
        self.pattern_recognizer = PatternRecognizer(self.db)
        self.scaler = StandardScaler()
        
        # Initialize models
        self.classifiers = {}
        self.cluster_models = {}
        
        # Load existing models if available
        self._load_models()
        
        logger.info("ML Pattern Predictor initialized")
    
    def _load_models(self):
        """Load trained models from disk if available"""
        try:
            # Load classifiers
            classifier_path = os.path.join(MODEL_DIR, 'pattern_classifiers.pkl')
            if os.path.exists(classifier_path):
                self.classifiers = joblib.load(classifier_path)
                logger.info(f"Loaded {len(self.classifiers)} pattern classifiers")
            
            # Load cluster models
            cluster_path = os.path.join(MODEL_DIR, 'pattern_clusters.pkl')
            if os.path.exists(cluster_path):
                self.cluster_models = joblib.load(cluster_path)
                logger.info(f"Loaded {len(self.cluster_models)} pattern cluster models")
            
            # Load scaler
            scaler_path = os.path.join(MODEL_DIR, 'feature_scaler.pkl')
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
                logger.info("Loaded feature scaler")
                
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
    
    def _save_models(self):
        """Save trained models to disk"""
        try:
            # Save classifiers
            classifier_path = os.path.join(MODEL_DIR, 'pattern_classifiers.pkl')
            joblib.dump(self.classifiers, classifier_path)
            
            # Save cluster models
            cluster_path = os.path.join(MODEL_DIR, 'pattern_clusters.pkl')
            joblib.dump(self.cluster_models, cluster_path)
            
            # Save scaler
            scaler_path = os.path.join(MODEL_DIR, 'feature_scaler.pkl')
            joblib.dump(self.scaler, scaler_path)
            
            logger.info("Saved ML models to disk")
            
        except Exception as e:
            logger.error(f"Error saving models: {str(e)}")
    
    def train_models(self, days: int = 90, min_samples: int = 100) -> Dict[str, Any]:
        """
        Train ML models for pattern prediction using historical data
        
        Args:
            days: Number of days of historical data to use
            min_samples: Minimum number of samples required for training
            
        Returns:
            Dict with training results
        """
        try:
            # Get training data
            X, y, pattern_types = self._get_training_data(days)
            
            if len(X) < min_samples:
                logger.warning(f"Insufficient training data: {len(X)} samples, minimum required: {min_samples}")
                return {
                    "success": False,
                    "message": f"Insufficient training data: {len(X)} samples, minimum required: {min_samples}",
                    "samples": len(X)
                }
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train pattern classifiers
            classifier_metrics = {}
            for pattern_type in pattern_types:
                # Create binary labels for this pattern type
                y_binary = [1 if pattern_type in patterns else 0 for patterns in y]
                
                # Skip if there are too few positive samples
                positive_count = sum(y_binary)
                if positive_count < 10:
                    logger.info(f"Skipping pattern '{pattern_type}' due to insufficient positive samples ({positive_count})")
                    continue
                
                # Split data
                X_train, X_test, y_train, y_test = train_test_split(
                    X_scaled, y_binary, test_size=0.2, random_state=42
                )
                
                # Train classifier
                clf = RandomForestClassifier(n_estimators=100, random_state=42)
                clf.fit(X_train, y_train)
                
                # Evaluate
                y_pred = clf.predict(X_test)
                metrics = {
                    "accuracy": accuracy_score(y_test, y_pred),
                    "precision": precision_score(y_test, y_pred, zero_division=0),
                    "recall": recall_score(y_test, y_pred, zero_division=0),
                    "f1": f1_score(y_test, y_pred, zero_division=0),
                    "positive_samples": positive_count
                }
                
                # Store classifier if performance is acceptable
                if metrics["f1"] > 0.6:
                    self.classifiers[pattern_type] = clf
                    classifier_metrics[pattern_type] = metrics
                    logger.info(f"Trained classifier for pattern '{pattern_type}' with F1 score: {metrics['f1']:.2f}")
            
            # Train clustering model for pattern discovery
            kmeans = KMeans(n_clusters=min(8, len(X) // 20), random_state=42)
            clusters = kmeans.fit_predict(X_scaled)
            
            # Analyze clusters to identify pattern associations
            cluster_patterns = {}
            for i in range(kmeans.n_clusters):
                cluster_indices = [idx for idx, cluster in enumerate(clusters) if cluster == i]
                cluster_patterns[i] = {}
                
                # Count pattern occurrences in this cluster
                for pattern_type in pattern_types:
                    pattern_count = sum(1 for idx in cluster_indices if pattern_type in y[idx])
                    if pattern_count > 0:
                        pattern_ratio = pattern_count / len(cluster_indices)
                        if pattern_ratio > 0.5:  # Pattern appears in >50% of cluster samples
                            cluster_patterns[i][pattern_type] = pattern_ratio
            
            # Store cluster model
            self.cluster_models['kmeans'] = {
                'model': kmeans,
                'pattern_associations': cluster_patterns
            }
            
            # Save models
            self._save_models()
            
            return {
                "success": True,
                "samples": len(X),
                "pattern_types": len(pattern_types),
                "classifiers_trained": len(classifier_metrics),
                "classifier_metrics": classifier_metrics,
                "clusters": kmeans.n_clusters,
                "cluster_patterns": cluster_patterns
            }
            
        except Exception as e:
            logger.error(f"Error training models: {str(e)}")
            return {
                "success": False,
                "message": f"Error training models: {str(e)}"
            }
    
    def predict_patterns(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict success patterns for a post based on its features
        
        Args:
            features: Post features including NLP and CV data
            
        Returns:
            Dict with predicted patterns and confidence scores
        """
        try:
            # Extract and normalize features
            X = self._extract_features(features)
            
            # Check if we have any trained models
            if not self.classifiers:
                logger.warning("No trained classifiers available for prediction")
                return {
                    "success": False,
                    "message": "No trained classifiers available"
                }
            
            # Scale features
            X_scaled = self.scaler.transform([X])
            
            # Make predictions with each classifier
            predicted_patterns = {}
            for pattern_type, clf in self.classifiers.items():
                # Get prediction and probability
                pred = clf.predict(X_scaled)[0]
                prob = clf.predict_proba(X_scaled)[0][1]  # Probability of positive class
                
                # Add to results if predicted positive with sufficient confidence
                if pred == 1 and prob >= 0.7:
                    predicted_patterns[pattern_type] = {
                        "confidence": float(prob),
                        "is_ml_prediction": True
                    }
            
            # Identify potential new patterns using clustering
            if 'kmeans' in self.cluster_models:
                kmeans = self.cluster_models['kmeans']['model']
                pattern_associations = self.cluster_models['kmeans']['pattern_associations']
                
                # Get cluster assignment
                cluster = kmeans.predict(X_scaled)[0]
                
                # Add associated patterns from this cluster
                if cluster in pattern_associations:
                    for pattern_type, confidence in pattern_associations[cluster].items():
                        # Only add if not already predicted and confidence is high enough
                        if pattern_type not in predicted_patterns and confidence >= 0.7:
                            predicted_patterns[pattern_type] = {
                                "confidence": float(confidence),
                                "is_ml_prediction": True,
                                "from_cluster": True
                            }
            
            return {
                "success": True,
                "predicted_patterns": predicted_patterns,
                "pattern_count": len(predicted_patterns)
            }
            
        except Exception as e:
            logger.error(f"Error predicting patterns: {str(e)}")
            return {
                "success": False,
                "message": f"Error predicting patterns: {str(e)}"
            }
    
    def _get_training_data(self, days: int = 90) -> Tuple[List[List[float]], List[List[str]], List[str]]:
        """
        Get training data from historical posts
        
        Args:
            days: Number of days of historical data to use
            
        Returns:
            Tuple of (features, pattern_labels, unique_pattern_types)
        """
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Query posts with analytics data
        query = self.db.query(Post, AnalyticsData).join(
            AnalyticsData
        ).filter(
            Post.publish_date >= start_date,
            Post.publish_date <= end_date,
            AnalyticsData.performance_score.isnot(None),
            AnalyticsData.success_patterns.isnot(None)
        ).order_by(Post.publish_date.desc())
        
        results = query.all()
        logger.info(f"Found {len(results)} posts with analytics data for training")
        
        # Extract features and labels
        X = []  # Features
        y = []  # Pattern labels
        all_patterns = set()
        
        for post, analytics in results:
            # Skip if no patterns
            if not analytics.success_patterns:
                continue
                
            # Extract features
            features = self._extract_features_from_post(post, analytics)
            if not features:
                continue
                
            # Extract pattern types
            pattern_types = [p["name"] for p in analytics.success_patterns if "name" in p]
            if not pattern_types:
                continue
                
            # Add to dataset
            X.append(features)
            y.append(pattern_types)
            all_patterns.update(pattern_types)
        
        return X, y, list(all_patterns)
    
    def _extract_features_from_post(self, post: Post, analytics: AnalyticsData) -> List[float]:
        """
        Extract features from a post and its analytics data
        
        Args:
            post: Post model instance
            analytics: AnalyticsData model instance
            
        Returns:
            List of numerical features
        """
        features = []
        
        try:
            # Basic metrics
            features.extend([
                analytics.performance_score or 0,
                analytics.engagement_rate or 0,
                analytics.virality_score or 0,
                analytics.trend_score or 0,
                analytics.content_quality_score or 0
            ])
            
            # Content type features (one-hot encoded)
            content_types = ['video', 'image', 'text', 'link', 'mixed']
            content_type_vec = [1 if post.content_type.value == ct else 0 for ct in content_types]
            features.extend(content_type_vec)
            
            # Platform features (one-hot encoded)
            platforms = ['youtube', 'instagram', 'threads', 'rednote']
            platform_vec = [1 if post.platform.value == p else 0 for p in platforms]
            features.extend(platform_vec)
            
            # Temporal features
            if post.publish_date:
                hour = post.publish_date.hour / 24.0  # Normalize to 0-1
                day_of_week = post.publish_date.weekday() / 6.0  # Normalize to 0-1
                features.extend([hour, day_of_week])
            else:
                features.extend([0, 0])
            
            # Content features
            features.extend([
                len(post.hashtags.split(',')) if post.hashtags else 0,
                len(post.mentions.split(',')) if post.mentions else 0,
                1 if post.images else 0,
                1 if post.videos else 0,
                len(post.content_text or '') / 1000.0  # Normalize by 1000 chars
            ])
            
            # NLP features if available
            if analytics.nlp_data:
                nlp_data = analytics.nlp_data
                sentiment = nlp_data.get('sentiment', {})
                sentiment_score = sentiment.get('score', 0)
                sentiment_magnitude = sentiment.get('magnitude', 0)
                
                text_stats = nlp_data.get('text_stats', {})
                readability = text_stats.get('readability_score', 0) / 100.0  # Normalize to 0-1
                
                features.extend([
                    sentiment_score,
                    sentiment_magnitude,
                    readability,
                    len(nlp_data.get('keywords', [])) / 10.0,  # Normalize by 10
                    len(nlp_data.get('topics', [])) / 5.0  # Normalize by 5
                ])
            else:
                features.extend([0, 0, 0, 0, 0])
            
            # CV features if available
            if analytics.cv_data:
                cv_data = analytics.cv_data
                agg_metrics = cv_data.get('aggregate_metrics', {})
                
                features.extend([
                    agg_metrics.get('avg_brightness', 0.5),
                    agg_metrics.get('color_diversity', 0),
                    agg_metrics.get('face_count', 0) / 5.0,  # Normalize by 5
                    agg_metrics.get('object_count', 0) / 10.0,  # Normalize by 10
                    1 if agg_metrics.get('has_people', False) else 0
                ])
            else:
                features.extend([0, 0, 0, 0, 0])
                
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features from post {post.id}: {str(e)}")
            return []
    
    def _extract_features(self, feature_data: Dict[str, Any]) -> List[float]:
        """
        Extract features from input feature data
        
        Args:
            feature_data: Dictionary with post features
            
        Returns:
            List of numerical features
        """
        features = []
        
        try:
            # Basic metrics
            features.extend([
                feature_data.get('performance_score', 0),
                feature_data.get('engagement_rate', 0),
                feature_data.get('virality_score', 0),
                feature_data.get('trend_score', 0),
                feature_data.get('content_quality_score', 0)
            ])
            
            # Content type features (one-hot encoded)
            content_type = feature_data.get('content_type', 'text')
            content_types = ['video', 'image', 'text', 'link', 'mixed']
            content_type_vec = [1 if content_type == ct else 0 for ct in content_types]
            features.extend(content_type_vec)
            
            # Platform features (one-hot encoded)
            platform = feature_data.get('platform', 'instagram')
            platforms = ['youtube', 'instagram', 'threads', 'rednote']
            platform_vec = [1 if platform == p else 0 for p in platforms]
            features.extend(platform_vec)
            
            # Temporal features
            publish_date = feature_data.get('publish_date')
            if publish_date:
                hour = publish_date.hour / 24.0  # Normalize to 0-1
                day_of_week = publish_date.weekday() / 6.0  # Normalize to 0-1
                features.extend([hour, day_of_week])
            else:
                features.extend([0, 0])
            
            # Content features
            features.extend([
                len(feature_data.get('hashtags', '').split(',')) if feature_data.get('hashtags') else 0,
                len(feature_data.get('mentions', '').split(',')) if feature_data.get('mentions') else 0,
                1 if feature_data.get('has_images', False) else 0,
                1 if feature_data.get('has_videos', False) else 0,
                len(feature_data.get('content_text', '')) / 1000.0  # Normalize by 1000 chars
            ])
            
            # NLP features if available
            nlp_data = feature_data.get('nlp_data', {})
            if nlp_data:
                sentiment = nlp_data.get('sentiment', {})
                sentiment_score = sentiment.get('score', 0)
                sentiment_magnitude = sentiment.get('magnitude', 0)
                
                text_stats = nlp_data.get('text_stats', {})
                readability = text_stats.get('readability_score', 0) / 100.0  # Normalize to 0-1
                
                features.extend([
                    sentiment_score,
                    sentiment_magnitude,
                    readability,
                    len(nlp_data.get('keywords', [])) / 10.0,  # Normalize by 10
                    len(nlp_data.get('topics', [])) / 5.0  # Normalize by 5
                ])
            else:
                features.extend([0, 0, 0, 0, 0])
            
            # CV features if available
            cv_data = feature_data.get('cv_data', {})
            if cv_data:
                agg_metrics = cv_data.get('aggregate_metrics', {})
                
                features.extend([
                    agg_metrics.get('avg_brightness', 0.5),
                    agg_metrics.get('color_diversity', 0),
                    agg_metrics.get('face_count', 0) / 5.0,  # Normalize by 5
                    agg_metrics.get('object_count', 0) / 10.0,  # Normalize by 10
                    1 if agg_metrics.get('has_people', False) else 0
                ])
            else:
                features.extend([0, 0, 0, 0, 0])
                
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features: {str(e)}")
            return []
    
    def evaluate_models(self) -> Dict[str, Any]:
        """
        Evaluate the performance of trained models
        
        Returns:
            Dict with evaluation results
        """
        try:
            if not self.classifiers:
                return {
                    "success": False,
                    "message": "No trained classifiers available"
                }
            
            # Get fresh test data (last 30 days)
            X, y, pattern_types = self._get_training_data(days=30)
            
            if len(X) < 50:
                return {
                    "success": False,
                    "message": f"Insufficient test data: {len(X)} samples"
                }
            
            # Scale features
            X_scaled = self.scaler.transform(X)
            
            # Evaluate each classifier
            evaluation = {}
            for pattern_type, clf in self.classifiers.items():
                if pattern_type not in pattern_types:
                    continue
                    
                # Create binary labels for this pattern type
                y_binary = [1 if pattern_type in patterns else 0 for patterns in y]
                
                # Make predictions
                y_pred = clf.predict(X_scaled)
                
                # Calculate metrics
                metrics = {
                    "accuracy": accuracy_score(y_binary, y_pred),
                    "precision": precision_score(y_binary, y_pred, zero_division=0),
                    "recall": recall_score(y_binary, y_pred, zero_division=0),
                    "f1": f1_score(y_binary, y_pred, zero_division=0),
                    "positive_samples": sum(y_binary)
                }
                
                evaluation[pattern_type] = metrics
            
            return {
                "success": True,
                "test_samples": len(X),
                "evaluation": evaluation
            }
            
        except Exception as e:
            logger.error(f"Error evaluating models: {str(e)}")
            return {
                "success": False,
                "message": f"Error evaluating models: {str(e)}"
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about trained models
        
        Returns:
            Dict with model information
        """
        try:
            classifier_info = {}
            for pattern_type, clf in self.classifiers.items():
                if hasattr(clf, 'feature_importances_'):
                    classifier_info[pattern_type] = {
                        "feature_importances": clf.feature_importances_.tolist(),
                        "n_estimators": clf.n_estimators if hasattr(clf, 'n_estimators') else None,
                        "model_type": clf.__class__.__name__
                    }
                else:
                    classifier_info[pattern_type] = {
                        "model_type": clf.__class__.__name__
                    }
            
            cluster_info = {}
            if 'kmeans' in self.cluster_models:
                kmeans = self.cluster_models['kmeans']['model']
                pattern_associations = self.cluster_models['kmeans']['pattern_associations']
                
                cluster_info['kmeans'] = {
                    "n_clusters": kmeans.n_clusters,
                    "pattern_associations": pattern_associations
                }
            
            return {
                "success": True,
                "classifiers": len(self.classifiers),
                "classifier_info": classifier_info,
                "cluster_models": len(self.cluster_models),
                "cluster_info": cluster_info
            }
            
        except Exception as e:
            logger.error(f"Error getting model info: {str(e)}")
            return {
                "success": False,
                "message": f"Error getting model info: {str(e)}"
            } 