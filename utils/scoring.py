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

            # Apply each heuristic with safe data access
            heuristic_scores = {}

            try:
                heuristic_scores['account_age'] = self.heuristics['account_age'].analyze(sanitized_data)
            except Exception as e:
                logger.error(f"Error in account_age heuristic: {str(e)}")
                heuristic_scores['account_age'] = {'age_score': 0.5}

            try:
                heuristic_scores['karma'] = self.heuristics['karma'].analyze(sanitized_data)
            except Exception as e:
                logger.error(f"Error in karma heuristic: {str(e)}")
                heuristic_scores['karma'] = {'karma_score': 0.5}

            try:
                heuristic_scores['username'] = self.heuristics['username'].analyze(sanitized_data)
            except Exception as e:
                logger.error(f"Error in username heuristic: {str(e)}")
                heuristic_scores['username'] = {'username_score': 0.5}

            try:
                posting_data = {
                    'comments': sanitized_data['comments'],
                    'submissions': sanitized_data['submissions']
                }
                heuristic_scores['posting'] = self.heuristics['posting'].analyze(posting_data)
            except Exception as e:
                logger.error(f"Error in posting heuristic: {str(e)}")
                heuristic_scores['posting'] = {
                    'frequency_score': 0.5,
                    'interval_score': 0.5,
                    'timezone_score': 0.5
                }

            try:
                subreddit_data = {
                    'comments': sanitized_data['comments'],
                    'submissions': sanitized_data['submissions']
                }
                heuristic_scores['subreddit'] = self.heuristics['subreddit'].analyze(subreddit_data)
            except Exception as e:
                logger.error(f"Error in subreddit heuristic: {str(e)}")
                heuristic_scores['subreddit'] = {'diversity_score': 0.5}

            try:
                engagement_data = {
                    'comments': sanitized_data['comments'],
                    'submissions': sanitized_data['submissions']
                }
                heuristic_scores['engagement'] = self.heuristics['engagement'].analyze(engagement_data)
            except Exception as e:
                logger.error(f"Error in engagement heuristic: {str(e)}")
                heuristic_scores['engagement'] = {
                    'interaction_score': 0.5,
                    'depth_score': 0.5
                }

            try:
                linguistic_data = {
                    'comments': sanitized_data['comments']
                }
                heuristic_scores['linguistic'] = self.heuristics['linguistic'].analyze(linguistic_data)
            except Exception as e:
                logger.error(f"Error in linguistic heuristic: {str(e)}")
                heuristic_scores['linguistic'] = {
                    'similarity_score': 0.5,
                    'complexity_score': 0.5,
                    'pattern_score': 0.5,
                    'style_score': 0.5
                }

            # Extract primary scores and store detailed metrics
            for category, result in heuristic_scores.items():
                if isinstance(result, dict):
                    for score_name, score in result.items():
                        if isinstance(score, (int, float)):  # Primary scores
                            scores[f"{category}_{score_name}"] = float(score)  # Ensure float type
                        elif isinstance(score, dict) and score_name == 'metrics':
                            # Store detailed metrics for visualization
                            scores[f"{category}_metrics"] = score

            # Get ML-based risk score
            try:
                ml_risk_score, feature_importance = self.ml_analyzer.analyze_account(
                    sanitized_data, activity_patterns, text_metrics
                )
                scores['ml_risk_score'] = float(ml_risk_score)  # Ensure float type
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

            for score_name, weight in weights.items():
                if score_name in scores and isinstance(scores[score_name], (int, float)):
                    score = float(scores[score_name])
                    final_score += score * weight
                    weight_sum += weight

            if weight_sum == 0:
                logger.warning("No valid scores found for weighted calculation")
                return 0.5, scores  # Return moderate risk if no scores available

            # Normalize final score
            final_score = final_score / weight_sum

            return final_score, scores

        except Exception as e:
            logger.error(f"Error calculating score: {str(e)}")
            return 0.5, {}  # Return moderate risk score in case of error