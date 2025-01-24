import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import logging
from typing import Dict, List, Tuple, Union

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
        
    def extract_features(self, user_data: Dict, activity_patterns: Dict, text_metrics: Dict) -> np.ndarray:
        """Extract and normalize features from user data."""
        try:
            features = [
                # Account features
                (datetime.now(timezone.utc) - user_data['created_utc']).days,  # account age in days
                user_data['comment_karma'],
                user_data['link_karma'],
                
                # Activity features
                activity_patterns['unique_subreddits'],
                activity_patterns.get('avg_score', 0),
                len(activity_patterns.get('activity_hours', {})),  # activity hours diversity
                
                # Text features
                text_metrics.get('vocab_size', 0),
                text_metrics.get('avg_word_length', 0),
                text_metrics.get('avg_similarity', 0),
            ]
            
            # Reshape and scale features
            features_array = np.array(features).reshape(1, -1)
            if self.is_trained:
                features_array = self.scaler.transform(features_array)
            
            return features_array
            
        except Exception as e:
            logger.error(f"Error extracting features: {str(e)}")
            # Return a zero vector of appropriate size in case of error
            return np.zeros((1, 9))
    
    def predict_risk_score(self, features: np.ndarray) -> float:
        """Predict risk score for given features."""
        try:
            if not self.is_trained:
                logger.warning("Model not trained yet, returning default prediction")
                return 0.5
            
            # Get probability of being suspicious (class 1)
            probabilities = self.model.predict_proba(features)
            return float(probabilities[0][1])  # Return probability of being suspicious
            
        except Exception as e:
            logger.error(f"Error predicting risk score: {str(e)}")
            return 0.5
    
    def analyze_account(self, user_data: Dict, activity_patterns: Dict, text_metrics: Dict) -> Tuple[float, Dict[str, float]]:
        """Analyze account using ML model and return risk score with feature importances."""
        features = self.extract_features(user_data, activity_patterns, text_metrics)
        risk_score = self.predict_risk_score(features)
        
        # Get feature importance if model is trained
        feature_importance = {}
        if self.is_trained:
            importance = self.model.feature_importances_
            feature_names = [
                'account_age', 'comment_karma', 'link_karma',
                'subreddit_diversity', 'avg_score', 'activity_hours',
                'vocab_size', 'word_length', 'comment_similarity'
            ]
            feature_importance = dict(zip(feature_names, importance))
        
        return risk_score, feature_importance
