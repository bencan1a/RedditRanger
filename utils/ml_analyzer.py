import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import logging
from typing import Dict, List, Tuple, Union
from datetime import datetime, timezone
from utils.performance_monitor import timing_decorator

logger = logging.getLogger(__name__)

class MLAnalyzer:
    @timing_decorator("ml_analyzer_init")
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self._setup_basic_rules()

        # Initialize training data storage
        self.training_features = []
        self.training_labels = []

    @timing_decorator("model_training")
    def _train_model(self) -> bool:
        """Train the model with collected examples."""
        try:
            if len(self.training_features) < 5:
                logger.warning("Not enough training examples to train model")
                return False

            # Convert lists to numpy arrays
            X = np.array(self.training_features)
            y = np.array(self.training_labels)

            # Fit the scaler
            X_scaled = self.scaler.fit_transform(X)

            # Train the model
            self.model.fit(X_scaled, y)
            self.is_trained = True

            logger.info("Model successfully trained")
            return True
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return False

    @timing_decorator("feature_extraction")
    def extract_features(self, user_data: Dict, activity_patterns: Dict, text_metrics: Dict) -> np.ndarray:
        """Extract and normalize features from user data."""
        try:
            # Calculate derived features
            account_age_days = float((datetime.now(timezone.utc) - user_data['created_utc']).days)
            karma_ratio = float(user_data['comment_karma']) / float(max(1, user_data['link_karma']))

            features = [
                float(account_age_days),  # account age in days
                float(user_data['comment_karma']),
                float(user_data['link_karma']),
                float(karma_ratio),  # ratio of comment to link karma

                float(activity_patterns['unique_subreddits']),
                float(activity_patterns.get('avg_score', 0)),
                float(len(activity_patterns.get('activity_hours', {}))),  # activity hours diversity
                float(len(activity_patterns.get('top_subreddits', {}))),  # number of active subreddits

                float(text_metrics.get('vocab_size', 0)),
                float(text_metrics.get('avg_word_length', 0)),
                float(text_metrics.get('avg_similarity', 0)),
                float(len(text_metrics.get('common_words', {})))  # vocabulary diversity
            ]

            # Reshape and scale features
            features_array = np.array(features, dtype=np.float64).reshape(1, -1)
            if self.is_trained:
                features_array = self.scaler.transform(features_array)

            return features_array

        except Exception as e:
            logger.error(f"Error extracting features: {str(e)}")
            return np.zeros((1, 12), dtype=np.float64)  # Return zero features array

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