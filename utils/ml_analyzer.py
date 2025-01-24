import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import logging
from typing import Dict, List, Tuple, Union
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class MLAnalyzer:
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        # Initialize with some basic rules for untrained model
        self._setup_basic_rules()

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
        # Start with a moderate-low base risk
        base_risk = 0.3
        risk_factors = 0
        total_factors = 4

        # Account age check
        account_age_days = (datetime.now(timezone.utc) - user_data['created_utc']).days
        if account_age_days < self.basic_thresholds['min_account_age_days']:
            risk_factors += 1

        # Karma check
        total_karma = user_data['comment_karma'] + user_data['link_karma']
        if total_karma < self.basic_thresholds['min_karma']:
            risk_factors += 1

        # Subreddit diversity check
        if activity_patterns['unique_subreddits'] < self.basic_thresholds['min_subreddits']:
            risk_factors += 1

        # Vocabulary check
        if text_metrics.get('vocab_size', 0) < self.basic_thresholds['min_vocab_size']:
            risk_factors += 1

        # Calculate final risk score
        risk_score = base_risk + (0.7 * risk_factors / total_factors)
        return risk_score

    def extract_features(self, user_data: Dict, activity_patterns: Dict, text_metrics: Dict) -> np.ndarray:
        """Extract and normalize features from user data."""
        try:
            # Calculate derived features
            account_age_days = (datetime.now(timezone.utc) - user_data['created_utc']).days
            karma_ratio = (user_data['comment_karma'] / (user_data['link_karma'] + 1)) if user_data['link_karma'] > 0 else 0

            features = [
                # Account features
                account_age_days,  # account age in days
                user_data['comment_karma'],
                user_data['link_karma'],
                karma_ratio,  # ratio of comment to link karma

                # Activity features
                activity_patterns['unique_subreddits'],
                activity_patterns.get('avg_score', 0),
                len(activity_patterns.get('activity_hours', {})),  # activity hours diversity
                len(activity_patterns.get('top_subreddits', {})),  # number of active subreddits

                # Text features
                text_metrics.get('vocab_size', 0),
                text_metrics.get('avg_word_length', 0),
                text_metrics.get('avg_similarity', 0),
                len(text_metrics.get('common_words', {}))  # vocabulary diversity
            ]

            # Reshape and scale features
            features_array = np.array(features).reshape(1, -1)
            if self.is_trained:
                features_array = self.scaler.transform(features_array)

            return features_array

        except Exception as e:
            logger.error(f"Error extracting features: {str(e)}")
            return np.zeros((1, 12))  # Updated size to match new features

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
            return 0.3  # Return a lower default risk score

    def analyze_account(self, user_data: Dict, activity_patterns: Dict, text_metrics: Dict) -> Tuple[float, Dict[str, float]]:
        """Analyze account using ML model and return risk score with feature importances."""
        features = self.extract_features(user_data, activity_patterns, text_metrics)
        risk_score = self.predict_risk_score(features, user_data, activity_patterns, text_metrics)

        # Get feature importance if model is trained
        feature_importance = {}
        if self.is_trained:
            importance = self.model.feature_importances_
            feature_names = [
                'account_age', 'comment_karma', 'link_karma', 'karma_ratio',
                'subreddit_diversity', 'avg_score', 'activity_hours', 'active_subreddits',
                'vocab_size', 'word_length', 'comment_similarity', 'vocab_diversity'
            ]
            feature_importance = dict(zip(feature_names, importance))

        return risk_score, feature_importance