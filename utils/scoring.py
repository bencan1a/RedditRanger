from datetime import datetime, timezone
from utils.ml_analyzer import MLAnalyzer
from utils.heuristics import (
    AccountAgeHeuristic,
    KarmaHeuristic,
    UsernameHeuristic,
    PostingBehaviorHeuristic,
    SubredditHeuristic,
    EngagementHeuristic,
    LinguisticHeuristic
)
import logging

logger = logging.getLogger(__name__)

class AccountScorer:
    def __init__(self):
        self.ml_analyzer = MLAnalyzer()
        # Initialize all heuristic analyzers
        self.heuristics = {
            'account_age': AccountAgeHeuristic(),
            'karma': KarmaHeuristic(),
            'username': UsernameHeuristic(),
            'posting': PostingBehaviorHeuristic(),
            'subreddit': SubredditHeuristic(),
            'engagement': EngagementHeuristic(),
            'linguistic': LinguisticHeuristic()
        }

    def calculate_score(self, user_data, activity_patterns, text_metrics):
        try:
            # Initialize scores dictionary
            scores = {}

            # Apply each heuristic
            heuristic_scores = {
                'account_age': self.heuristics['account_age'].analyze(user_data),
                'karma': self.heuristics['karma'].analyze(user_data),
                'username': self.heuristics['username'].analyze(user_data),
                'posting': self.heuristics['posting'].analyze({
                    'comments': user_data['comments'],
                    'submissions': user_data.get('submissions', [])
                }),
                'subreddit': self.heuristics['subreddit'].analyze({
                    'comments': user_data['comments'],
                    'submissions': user_data.get('submissions', [])
                }),
                'engagement': self.heuristics['engagement'].analyze({
                    'comments': user_data['comments'],
                    'submissions': user_data.get('submissions', [])
                }),
                'linguistic': self.heuristics['linguistic'].analyze({
                    'comments': user_data['comments']
                })
            }

            # Extract primary scores and store detailed metrics
            for category, result in heuristic_scores.items():
                for score_name, score in result.items():
                    if isinstance(score, (int, float)):  # Primary scores
                        scores[f"{category}_{score_name}"] = score
                    elif isinstance(score, dict) and score_name == 'metrics':
                        # Store detailed metrics for visualization
                        scores[f"{category}_metrics"] = score

            # Get ML-based risk score
            ml_risk_score, feature_importance = self.ml_analyzer.analyze_account(
                user_data, activity_patterns, text_metrics
            )
            scores['ml_risk_score'] = ml_risk_score

            # Define weights for different components
            weights = {
                # Traditional metrics (40%)
                'account_age_age_score': 0.10,
                'karma_karma_score': 0.10,
                'username_username_score': 0.05,
                'subreddit_diversity_score': 0.15,

                # Behavioral metrics (35%)
                'posting_frequency_score': 0.10,
                'posting_interval_score': 0.10,
                'engagement_interaction_score': 0.05,
                'engagement_depth_score': 0.05,
                'posting_timezone_score': 0.05,

                # Content analysis (25%)
                'linguistic_similarity_score': 0.05,
                'linguistic_complexity_score': 0.05,
                'linguistic_pattern_score': 0.10,
                'linguistic_style_score': 0.05
            }

            # Calculate weighted score
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

            # Integrate ML score (25% influence)
            if 'ml_risk_score' in scores:
                final_score = (final_score * 0.75) + (scores['ml_risk_score'] * 0.25)

            # Store feature importance for visualization
            if feature_importance:
                scores['feature_importance'] = feature_importance

            return final_score, scores

        except Exception as e:
            logger.error(f"Error calculating score: {str(e)}")
            return 0.5, scores  # Return moderate risk score in case of error