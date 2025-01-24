from datetime import datetime, timezone
from utils.ml_analyzer import MLAnalyzer
import logging

logger = logging.getLogger(__name__)

class AccountScorer:
    def __init__(self):
        self.ml_analyzer = MLAnalyzer()

    def calculate_score(self, user_data, activity_patterns, text_metrics):
        scores = {}

        try:
            # Get traditional scoring metrics
            account_age_days = (datetime.now(timezone.utc) - user_data['created_utc']).days
            scores['age_score'] = min(account_age_days / 365, 1.0)

            total_karma = user_data['comment_karma'] + user_data['link_karma']
            scores['karma_score'] = min(total_karma / 10000, 1.0)

            subreddit_diversity = min(activity_patterns['unique_subreddits'] / 10, 1.0)
            scores['diversity_score'] = subreddit_diversity

            vocab_score = min(text_metrics['vocab_size'] / 1000, 1.0)
            scores['text_score'] = vocab_score

            similarity_score = 1.0 - text_metrics.get('avg_similarity', 0.0)
            scores['uniqueness_score'] = similarity_score

            # Get ML-based risk score
            ml_risk_score, feature_importance = self.ml_analyzer.analyze_account(
                user_data, activity_patterns, text_metrics
            )
            scores['ml_risk_score'] = ml_risk_score

            # Calculate final weighted score with ML integration
            weights = {
                'age_score': 0.15,
                'karma_score': 0.15,
                'diversity_score': 0.15,
                'text_score': 0.15,
                'uniqueness_score': 0.15,
                'ml_risk_score': 0.25  # Give ML prediction higher weight
            }

            final_score = 0.0
            for score_name, weight in weights.items():
                final_score += scores[score_name] * weight

            # Store feature importance for visualization
            if feature_importance:
                scores['feature_importance'] = feature_importance

            return final_score, scores

        except Exception as e:
            logger.error(f"Error calculating score: {str(e)}")
            return 0.5, scores  # Return moderate risk score in case of error