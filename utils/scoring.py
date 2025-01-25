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
            # Initialize scores dictionary
            scores = {}

            # Sanitize user data
            sanitized_data = self._sanitize_user_data(user_data)
            if not sanitized_data:
                logger.error("Invalid user data format")
                return 0.5, {'error': 'Invalid user data format'}

            # Apply each heuristic with safe data access and store only numeric scores
            heuristic_scores = {}

            for heuristic_name, heuristic in self.heuristics.items():
                try:
                    result = heuristic.analyze(sanitized_data)
                    if isinstance(result, dict):
                        # Extract only numeric values from the result
                        for key, value in result.items():
                            if isinstance(value, (int, float)) and key != 'metrics':
                                scores[f"{heuristic_name}_{key}"] = float(value)
                            elif key == 'metrics' and isinstance(value, dict):
                                scores[f"{heuristic_name}_metrics"] = value
                except Exception as e:
                    logger.error(f"Error in {heuristic_name} heuristic: {str(e)}")
                    continue

            # Get ML-based risk score
            try:
                ml_risk_score, feature_importance = self.ml_analyzer.analyze_account(
                    sanitized_data, activity_patterns, text_metrics
                )
                if isinstance(ml_risk_score, (int, float)):
                    scores['ml_risk_score'] = float(ml_risk_score)
                if feature_importance:
                    scores['feature_importance'] = feature_importance
            except Exception as e:
                logger.error(f"Error in ML analysis: {str(e)}")
                scores['ml_risk_score'] = 0.5

            # Calculate final weighted score
            final_score = 0.0
            weight_sum = 0.0

            # Define weights for different components
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

            logger.debug("Scores before weighted calculation:")
            for score_name, score in scores.items():
                if score_name in weights:
                    logger.debug(f"{score_name}: {score}")

            for score_name, weight in weights.items():
                if score_name in scores:
                    try:
                        score_value = scores[score_name]
                        if isinstance(score_value, (int, float)):
                            score = float(score_value)
                            final_score += score * weight
                            weight_sum += weight
                        else:
                            logger.warning(f"Non-numeric score found for {score_name}: {type(score_value)}")
                    except Exception as e:
                        logger.error(f"Error processing score {score_name}: {str(e)}")
                        continue

            if weight_sum == 0:
                logger.warning("No valid scores found for weighted calculation")
                return 0.5, scores  # Return moderate risk if no scores available

            # Normalize final score
            final_score = final_score / weight_sum

            return final_score, scores

        except Exception as e:
            logger.error(f"Error calculating score: {str(e)}")
            return 0.5, {}  # Return moderate risk score in case of error