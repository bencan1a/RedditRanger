"""Machine Learning Analyzer for Reddit user behavior with optimized loading."""
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import logging
from typing import Dict, List, Tuple, Union, Optional
from datetime import datetime, timezone
from utils.performance_monitor import timing_decorator, performance_monitor
import joblib
from pathlib import Path
import os

logger = logging.getLogger(__name__)

class MLAnalyzer:
    """Singleton ML Analyzer with improved lazy loading and memory optimization."""
    _instance = None
    _initialized = False
    _model: Optional[RandomForestClassifier] = None
    _scaler: Optional[StandardScaler] = None
    _is_trained = False
    _model_cache_dir = Path('model_cache')

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MLAnalyzer, cls).__new__(cls)
        return cls._instance

    @timing_decorator("ml_analyzer_init")
    def __init__(self):
        """Initialize only essential components."""
        if not self._initialized:
            performance_monitor.start_operation("ml_init")
            try:
                # Initialize minimal required state
                self.training_features = []
                self.training_labels = []
                self._setup_basic_rules()
                self._initialized = True

                # Create cache directory if it doesn't exist
                self._model_cache_dir.mkdir(exist_ok=True)

                logger.info("MLAnalyzer base initialization complete")
            finally:
                performance_monitor.end_operation("ml_init")

    def _load_cached_model(self) -> bool:
        """Load model and scaler from cache if available."""
        try:
            model_path = self._model_cache_dir / 'model.joblib'
            scaler_path = self._model_cache_dir / 'scaler.joblib'

            if model_path.exists() and scaler_path.exists():
                self._model = joblib.load(model_path)
                self._scaler = joblib.load(scaler_path)
                self._is_trained = True
                logger.info("Loaded model and scaler from cache")
                return True
        except Exception as e:
            logger.warning(f"Failed to load cached model: {e}")
        return False

    def _save_model_to_cache(self):
        """Save current model and scaler to cache."""
        try:
            if self._model and self._scaler:
                joblib.dump(self._model, self._model_cache_dir / 'model.joblib')
                joblib.dump(self._scaler, self._model_cache_dir / 'scaler.joblib')
                logger.info("Saved model and scaler to cache")
        except Exception as e:
            logger.warning(f"Failed to cache model: {e}")

    @property
    def model(self):
        """Lazy load the RandomForestClassifier."""
        if self._model is None:
            performance_monitor.start_operation("ml_model_init")
            try:
                if not self._load_cached_model():
                    logger.info("Initializing new RandomForestClassifier")
                    self._model = RandomForestClassifier(
                        n_estimators=100,
                        max_depth=10,
                        random_state=42,
                        n_jobs=-1  # Parallel processing
                    )
            finally:
                performance_monitor.end_operation("ml_model_init")
        return self._model

    @property
    def scaler(self):
        """Lazy load the StandardScaler."""
        if self._scaler is None:
            logger.info("Initializing StandardScaler")
            self._scaler = StandardScaler()
        return self._scaler

    @property
    def is_trained(self):
        """Check if model is trained."""
        return self._is_trained

    @is_trained.setter
    def is_trained(self, value: bool):
        self._is_trained = value
        if value:
            self._save_model_to_cache()

    @timing_decorator("model_training")
    def _train_model(self) -> bool:
        """Train the model with collected examples using optimized memory usage."""
        try:
            if len(self.training_features) < 5:
                logger.warning("Not enough training examples to train model")
                return False

            # Convert lists to numpy arrays efficiently
            X = np.array(self.training_features, dtype=np.float32)  # Use float32 for memory efficiency
            y = np.array(self.training_labels, dtype=np.int8)

            # Scale features and train model
            X_scaled = self.scaler.fit_transform(X)
            self.model.fit(X_scaled, y)
            self.is_trained = True

            # Clear training data after successful training
            self.training_features = []
            self.training_labels = []

            logger.info("Model successfully trained")
            return True
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return False

    @timing_decorator("feature_extraction")
    def extract_features(self, user_data: Dict, activity_patterns: Dict, text_metrics: Dict) -> np.ndarray:
        """Extract and normalize features with memory optimization."""
        try:
            # Calculate derived features
            account_age_days = float((datetime.now(timezone.utc) - user_data['created_utc']).days)
            karma_ratio = float(user_data['comment_karma']) / float(max(1, user_data['link_karma']))

            # Use memory-efficient data types
            features = np.array([
                account_age_days,
                float(user_data['comment_karma']),
                float(user_data['link_karma']),
                karma_ratio,
                float(activity_patterns['unique_subreddits']),
                float(activity_patterns.get('avg_score', 0)),
                float(len(activity_patterns.get('activity_hours', {}))),
                float(len(activity_patterns.get('top_subreddits', {}))),
                float(text_metrics.get('vocab_size', 0)),
                float(text_metrics.get('avg_word_length', 0)),
                float(text_metrics.get('avg_similarity', 0)),
                float(len(text_metrics.get('common_words', {})))
            ], dtype=np.float32).reshape(1, -1)

            if self.is_trained:
                features = self.scaler.transform(features)

            return features

        except Exception as e:
            logger.error(f"Error extracting features: {str(e)}")
            return np.zeros((1, 12), dtype=np.float32)

    def cleanup(self):
        """Clean up resources and free memory."""
        self._model = None
        self._scaler = None
        self.training_features = []
        self.training_labels = []

    def _setup_basic_rules(self):
        """Set up basic rules for risk assessment when model is untrained."""
        self.basic_thresholds = {
            'min_account_age_days': 30,  # Minimum account age threshold
            'min_karma': 100,  # Minimum karma threshold
            'min_subreddits': 3,  # Minimum number of unique subreddits
            'min_vocab_size': 200,  # Minimum vocabulary size
        }

    def _apply_basic_rules(self, features: np.ndarray, user_data: Dict, 
                          activity_patterns: Dict, text_metrics: Dict) -> float:
        """Apply basic rules to determine risk when model is untrained."""
        try:
            # Start with a moderate-low base risk
            base_risk = 0.3
            risk_factors = 0
            total_factors = 4

            # Account age check
            account_age_days = float((datetime.now(timezone.utc) - user_data['created_utc']).days)
            if account_age_days < float(self.basic_thresholds['min_account_age_days']):
                risk_factors += 1

            # Karma check
            total_karma = float(user_data['comment_karma']) + float(user_data['link_karma'])
            if total_karma < float(self.basic_thresholds['min_karma']):
                risk_factors += 1

            # Subreddit diversity check
            if float(activity_patterns['unique_subreddits']) < float(self.basic_thresholds['min_subreddits']):
                risk_factors += 1

            # Vocabulary check
            if float(text_metrics.get('vocab_size', 0)) < float(self.basic_thresholds['min_vocab_size']):
                risk_factors += 1

            # Calculate final risk score
            risk_score = float(base_risk + (0.7 * risk_factors / total_factors))
            return risk_score
        except Exception as e:
            logger.error(f"Error applying basic rules: {str(e)}")
            return 0.3  # Return base risk on error

    def add_training_example(self, user_data: Dict, activity_patterns: Dict, 
                           text_metrics: Dict, is_legitimate: bool = True) -> bool:
        """Add a new training example to improve the model."""
        try:
            features = self.extract_features(user_data, activity_patterns, text_metrics)
            self.training_features.append(features[0])  # Remove the batch dimension
            self.training_labels.append(0 if is_legitimate else 1)  # 0 for legitimate, 1 for suspicious

            # Retrain model if we have enough examples
            if len(self.training_labels) >= 5:  # Minimum examples before training
                self._train_model()

            logger.info(f"Added new training example. Total examples: {len(self.training_labels)}")
            return True
        except Exception as e:
            logger.error(f"Error adding training example: {str(e)}")
            return False

    def analyze_account(self, user_data: Dict, activity_patterns: Dict, text_metrics: Dict) -> Tuple[float, Dict[str, float]]:
        """Analyze account using ML model and return risk score with feature importances."""
        try:
            features = self.extract_features(user_data, activity_patterns, text_metrics)
            risk_score = float(self.predict_risk_score(features, user_data, activity_patterns, text_metrics))

            # Get feature importance if model is trained
            feature_importance = {}
            if self.is_trained:
                importance = self.model.feature_importances_
                feature_names = [
                    'account_age', 'comment_karma', 'link_karma', 'karma_ratio',
                    'subreddit_diversity', 'avg_score', 'activity_hours', 'active_subreddits',
                    'vocab_size', 'word_length', 'comment_similarity', 'vocab_diversity'
                ]
                feature_importance = {name: float(imp) for name, imp in zip(feature_names, importance)}

            return risk_score, feature_importance

        except Exception as e:
            logger.error(f"Error in analyze_account: {str(e)}")
            return 0.3, {}  # Return safe defaults

    @timing_decorator("risk_prediction")
    def predict_risk_score(self, features: np.ndarray, user_data: Dict, 
                          activity_patterns: Dict, text_metrics: Dict) -> float:
        """Predict risk score for given features."""
        try:
            if not self.is_trained:
                logger.warning("Model not trained yet, using basic rules for prediction")
                return self._apply_basic_rules(features, user_data, activity_patterns, text_metrics)

            # Get probability of being suspicious (class 1)
            probabilities = self.model.predict_proba(features)
            return float(probabilities[0][1])  # Return probability of being suspicious

        except Exception as e:
            logger.error(f"Error predicting risk score: {str(e)}")
            return 0.3  # Return lower default risk score