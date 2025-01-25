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

    def _sanitize_user_data(self, user_data):
        """Sanitize user data to ensure proper types"""
        if not isinstance(user_data, dict):
            logger.error("User data is not a dictionary")
            return None

        sanitized = {}
        try:
            # Log the raw karma values for debugging
            logger.debug(f"Raw comment_karma: {user_data.get('comment_karma')}")
            logger.debug(f"Raw link_karma: {user_data.get('link_karma')}")

            # Extract karma values safely
            comment_karma = self._extract_karma_value(user_data.get('comment_karma', 0))
            link_karma = self._extract_karma_value(user_data.get('link_karma', 0))

            logger.debug(f"Extracted comment_karma: {comment_karma}")
            logger.debug(f"Extracted link_karma: {link_karma}")

            # Build sanitized data structure
            sanitized['username'] = str(user_data.get('username', ''))
            sanitized['created_utc'] = user_data.get('created_utc', datetime.now(timezone.utc))
            sanitized['comment_karma'] = comment_karma
            sanitized['link_karma'] = link_karma
            sanitized['comments'] = list(user_data.get('comments', []))
            sanitized['submissions'] = list(user_data.get('submissions', []))

            return sanitized
        except Exception as e:
            logger.error(f"Error sanitizing user data: {str(e)}")
            return None

    def calculate_score(self, user_data, activity_patterns, text_metrics):
        try:
            # Initial debug logging
            logger.info("=== Starting score calculation ===")
            logger.debug(f"Input user_data type: {type(user_data)}")
            logger.debug(f"Input user_data keys: {user_data.keys() if isinstance(user_data, dict) else 'Not a dict'}")

            scores = {}

            # Log before processing each heuristic
            logger.info("Processing heuristics...")

            for heuristic_name, heuristic in self.heuristics.items():
                try:
                    logger.debug(f"Running {heuristic_name} heuristic...")
                    result = heuristic.analyze(user_data)

                    # Log the raw result
                    logger.debug(f"{heuristic_name} raw result: {result}")

                    if isinstance(result, dict):
                        for key, value in result.items():
                            # Log each key-value pair being processed
                            logger.debug(f"Processing {heuristic_name} - {key}: {type(value)} = {value}")

                            if isinstance(value, (int, float)) and key != 'metrics':
                                scores[f"{heuristic_name}_{key}"] = float(value)
                                logger.debug(f"Added score {heuristic_name}_{key}: {value}")
                            elif key == 'metrics':
                                scores[f"{heuristic_name}_metrics"] = value
                                logger.debug(f"Added metrics for {heuristic_name}")
                except Exception as e:
                    logger.error(f"Error in {heuristic_name} heuristic: {str(e)}", exc_info=True)
                    continue

            # Log all accumulated scores before ML analysis
            logger.debug("=== Accumulated scores before ML analysis ===")
            for key, value in scores.items():
                logger.debug(f"Score: {key} = {type(value)} : {value}")

            try:
                logger.debug("Starting ML analysis...")
                ml_risk_score, feature_importance = self.ml_analyzer.analyze_account(
                    user_data, activity_patterns, text_metrics
                )
                if isinstance(ml_risk_score, (int, float)):
                    scores['ml_risk_score'] = float(ml_risk_score)
                    logger.debug(f"Added ML risk score: {ml_risk_score}")
                if feature_importance:
                    scores['feature_importance'] = feature_importance
            except Exception as e:
                logger.error(f"Error in ML analysis: {str(e)}", exc_info=True)
                scores['ml_risk_score'] = 0.5

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

            # Log all available scores before calculation
            logger.info("=== Available scores before weighted calculation ===")
            for score_name, score in scores.items():
                logger.info(f"Score {score_name}: type={type(score)}, value={score}")

            # Process each weight with detailed logging
            for score_name, weight in weights.items():
                logger.debug(f"\nProcessing weighted score: {score_name}")
                logger.debug(f"Weight: {weight}")

                if score_name in scores:
                    score_value = scores[score_name]
                    logger.debug(f"Found score value: type={type(score_value)}, value={score_value}")

                    if not isinstance(score_value, (int, float)):
                        logger.warning(f"Invalid score type for {score_name}: {type(score_value)}")
                        continue

                    try:
                        contribution = float(score_value) * weight
                        final_score += contribution
                        weight_sum += weight
                        logger.debug(f"Added contribution: {contribution}")
                        logger.debug(f"Running totals - final_score: {final_score}, weight_sum: {weight_sum}")
                    except Exception as e:
                        logger.error(f"Error calculating weighted score for {score_name}: {str(e)}", exc_info=True)
                        continue
                else:
                    logger.debug(f"Score {score_name} not found in scores dictionary")

            if weight_sum == 0:
                logger.warning("No valid scores found for weighted calculation")
                return 0.5, scores

            # Calculate final normalized score
            final_score = final_score / weight_sum
            logger.info(f"=== Final normalized score: {final_score} ===")

            return final_score, scores

        except Exception as e:
            logger.error(f"Error calculating score: {str(e)}", exc_info=True)
            return 0.5, {}