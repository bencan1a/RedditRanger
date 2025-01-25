import logging
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

logger = logging.getLogger(__name__)

class AccountScorer:
    def __init__(self):
        self.ml_analyzer = MLAnalyzer()
        self.heuristics = {
            'account_age': AccountAgeHeuristic(),
            'karma': KarmaHeuristic(),
            'username': UsernameHeuristic(),
            'posting': PostingBehaviorHeuristic(),
            'subreddit': SubredditHeuristic(),
            'engagement': EngagementHeuristic(),
            'linguistic': LinguisticHeuristic()
        }

    def _extract_karma_value(self, karma_data):
        """Safely extract karma value from potentially nested data"""
        if isinstance(karma_data, (int, float)):
            return float(karma_data)
        elif isinstance(karma_data, dict):
            # If it's a dictionary, try to find a numeric value
            for key in ['value', 'score', 'count']:
                if key in karma_data and isinstance(karma_data[key], (int, float)):
                    return float(karma_data[key])
        elif isinstance(karma_data, str):
            # Try to convert string to float
            try:
                return float(karma_data.replace(',', ''))
            except (ValueError, TypeError):
                pass
        return 0.0

    def calculate_score(self, user_data, activity_patterns, text_metrics):
        try:
            # Initial debug logging
            logger.info("=== Starting score calculation ===")
            logger.debug(f"Input user_data type: {type(user_data)}")
            logger.debug(f"Input user_data keys: {user_data.keys() if isinstance(user_data, dict) else 'Not a dict'}")

            # Initialize containers
            scores = {}
            metrics = {}

            # Ensure user_data has required structure
            required_fields = {
                'username': '',
                'created_utc': datetime.now(timezone.utc),
                'comment_karma': 0,
                'link_karma': 0,
                'comments': [],
                'submissions': []
            }

            # Create sanitized data with defaults
            sanitized_data = {
                key: user_data.get(key, default_value) 
                for key, default_value in required_fields.items()
            }

            # Extract karma values safely
            sanitized_data['comment_karma'] = self._extract_karma_value(user_data.get('comment_karma', 0))
            sanitized_data['link_karma'] = self._extract_karma_value(user_data.get('link_karma', 0))

            # Process heuristics
            logger.info("Processing heuristics...")

            for heuristic_name, heuristic in self.heuristics.items():
                try:
                    logger.debug(f"Running {heuristic_name} heuristic...")
                    result = heuristic.analyze(sanitized_data)
                    logger.debug(f"{heuristic_name} raw result: {result}")

                    if isinstance(result, dict):
                        # Separate scores from metrics
                        for key, value in result.items():
                            if key == 'metrics':
                                metrics[heuristic_name] = value
                            elif isinstance(value, (int, float)):
                                key_name = f"{heuristic_name}_{key}"
                                scores[key_name] = float(value)
                                logger.debug(f"Added score {key_name}: {value}")

                except Exception as e:
                    logger.error(f"Error in {heuristic_name} heuristic: {str(e)}", exc_info=True)
                    continue

            # Calculate final weighted score
            logger.info("=== Starting weighted score calculation ===")
            final_score = 0.0
            weight_sum = 0.0

            weights = {
                'account_age_age_score': 0.10,
                'karma_karma_score': 0.10,
                'username_username_score': 0.05,
                'subreddit_diversity_score': 0.15,
                'posting_frequency_score': 0.10,
                'posting_interval_score': 0.10,
                'engagement_interaction_score': 0.05,
                'engagement_depth_score': 0.05,
                'posting_timezone_score': 0.05,
                'linguistic_similarity_score': 0.05,
                'linguistic_complexity_score': 0.05,
                'linguistic_pattern_score': 0.10,
                'linguistic_style_score': 0.05
            }

            # Log available scores
            logger.info("=== Available scores before weighted calculation ===")
            for score_name, score in scores.items():
                logger.debug(f"Score {score_name}: type={type(score)}, value={score}")

            # Process each weight
            for score_name, weight in weights.items():
                if score_name not in scores:
                    logger.debug(f"Score {score_name} not found in scores dictionary")
                    continue

                try:
                    score_value = scores[score_name]
                    logger.debug(f"Processing {score_name}: {score_value} * {weight}")
                    contribution = float(score_value) * weight
                    final_score += contribution
                    weight_sum += weight
                    logger.debug(f"Added contribution: {contribution}, running total: {final_score}")
                except Exception as e:
                    logger.error(f"Error calculating weighted score for {score_name}: {str(e)}", exc_info=True)
                    continue

            if weight_sum == 0:
                logger.warning("No valid scores found for weighted calculation")
                return 0.5, metrics

            # Calculate final normalized score
            final_score = final_score / weight_sum
            logger.info(f"=== Final normalized score: {final_score} ===")

            return final_score, metrics

        except Exception as e:
            logger.error(f"Error calculating score: {str(e)}", exc_info=True)
            return 0.5, {}