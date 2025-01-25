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
        logger.debug("Initializing AccountScorer")
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
        logger.debug("AccountScorer initialized with all heuristics")

    def _extract_karma_value(self, karma_data):
        """Safely extract karma value from potentially nested data"""
        logger.debug(f"Extracting karma value from: {karma_data} (type: {type(karma_data)})")

        if isinstance(karma_data, (int, float)):
            value = float(karma_data)
            logger.debug(f"Direct numeric value extracted: {value}")
            return value
        elif isinstance(karma_data, dict):
            # If it's a dictionary, try to find a numeric value
            logger.debug(f"Karma data is dictionary with keys: {karma_data.keys()}")
            for key in ['value', 'score', 'count']:
                if key in karma_data and isinstance(karma_data[key], (int, float)):
                    value = float(karma_data[key])
                    logger.debug(f"Found numeric value in dict under key '{key}': {value}")
                    return value
        elif isinstance(karma_data, str):
            # Try to convert string to float
            try:
                value = float(karma_data.replace(',', ''))
                logger.debug(f"Converted string to numeric value: {value}")
                return value
            except (ValueError, TypeError) as e:
                logger.error(f"Failed to convert string to float: {e}")
                pass

        logger.warning("Could not extract valid karma value, returning 0.0")
        return 0.0

    def calculate_score(self, user_data, activity_patterns, text_metrics):
        """Calculate final score for the account"""
        try:
            # Initial debug logging
            logger.info("=== Starting score calculation ===")
            logger.debug(f"Input user_data type: {type(user_data)}")
            logger.debug(f"Input user_data keys: {user_data.keys() if isinstance(user_data, dict) else 'Not a dict'}")
            logger.debug(f"Raw user_data: {user_data}")

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
            logger.debug(f"Sanitized data: {sanitized_data}")

            # Extract karma values safely
            logger.debug("Extracting karma values...")
            sanitized_data['comment_karma'] = self._extract_karma_value(user_data.get('comment_karma', 0))
            sanitized_data['link_karma'] = self._extract_karma_value(user_data.get('link_karma', 0))
            logger.debug(f"Extracted comment_karma: {sanitized_data['comment_karma']}")
            logger.debug(f"Extracted link_karma: {sanitized_data['link_karma']}")

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
                    scores[score_name] = 0.5  # Add default score
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
                    scores[score_name] = 0.5  # Add default score on error
                    continue

            if weight_sum == 0:
                logger.warning("No valid scores found for weighted calculation")
                return 0.5, scores

            # Calculate final normalized score
            final_score = final_score / weight_sum
            logger.info(f"=== Final normalized score: {final_score:.5f} ===")

            return final_score, scores

        except Exception as e:
            logger.error(f"Error calculating score: {str(e)}", exc_info=True)
            return 0.5, {}