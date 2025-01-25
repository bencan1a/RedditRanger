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
            # Account age score (older accounts more likely legitimate)
            account_age_days = (datetime.now(timezone.utc) - user_data['created_utc']).days
            scores['age_score'] = min(account_age_days / 365, 1.0)  # Normalize to 1 year

            # Karma score (higher karma more likely legitimate)
            total_karma = user_data['comment_karma'] + user_data['link_karma']
            scores['karma_score'] = min(total_karma / 10000, 1.0)  # Normalize to 10k karma

            # Subreddit diversity (more diverse activity more likely legitimate)
            subreddit_diversity = min(len(activity_patterns['top_subreddits']) / 10, 1.0)
            scores['diversity_score'] = subreddit_diversity

            # Text analysis scores
            # Text complexity (richer vocabulary more likely legitimate)
            vocab_size = text_metrics.get('vocab_size', 0)
            if isinstance(vocab_size, (int, float)):
                scores['text_score'] = min(vocab_size / 1000, 1.0)
            else:
                scores['text_score'] = 0.5  # Default if vocab_size is invalid

            # Content uniqueness (more unique content more likely legitimate)
            similarity_score = text_metrics.get('avg_similarity', 0.0)
            scores['uniqueness_score'] = 1.0 - similarity_score

            # Get ML-based risk score
            ml_risk_score, feature_importance = self.ml_analyzer.analyze_account(
                user_data, activity_patterns, text_metrics
            )
            scores['ml_risk_score'] = ml_risk_score

            # Calculate final weighted score with ML integration
            weights = {
                'age_score': 0.15,        # Account age
                'karma_score': 0.15,      # Total karma
                'diversity_score': 0.15,  # Subreddit diversity
                'text_score': 0.15,       # Vocabulary richness
                'uniqueness_score': 0.15, # Content uniqueness
                'ml_risk_score': 0.25     # ML prediction
            }

            final_score = 0.0
            weight_sum = 0.0

            for score_name, weight in weights.items():
                if score_name in scores and scores[score_name] is not None:
                    score = scores[score_name]
                    # Apply dampening to reduce false positives
                    if score < 0.3:  # Low scores get reduced further
                        score = score * 0.5
                    final_score += score * weight
                    weight_sum += weight

            if weight_sum == 0:
                return 0.5, scores  # Return moderate risk if no scores available

            # Normalize final score
            final_score = final_score / weight_sum

            # Store feature importance for visualization if available
            if feature_importance:
                scores['feature_importance'] = feature_importance

            return final_score, scores

        except Exception as e:
            logger.error(f"Error calculating score: {str(e)}")
            return 0.5, scores  # Return moderate risk score in case of error