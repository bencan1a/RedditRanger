from typing import Dict, Any
from .base import BaseHeuristic

class KarmaHeuristic(BaseHeuristic):
    """Analyzes karma patterns and trophy history"""

    def analyze(self, data: Dict[str, Any]) -> Dict[str, float]:
        try:
            # Initialize the scores dictionary
            scores = {}

            # Safely extract karma values
            comment_karma = float(data.get('comment_karma', 0))
            link_karma = float(data.get('link_karma', 0))
            total_karma = max(1.0, comment_karma + link_karma)  # Ensure non-zero float

            # Calculate base karma score
            scores['karma_score'] = float(self.normalize_score(total_karma / 10000))  # Normalize to 10k karma

            # Check for extreme karma patterns
            if total_karma > 100000:  # Extremely high karma
                scores['karma_score'] *= 0.8  # Slightly suspicious
            elif total_karma < 10:  # Extremely low karma
                scores['karma_score'] *= 0.6  # More suspicious

            # Analyze karma ratio (safely handle zero division)
            link_ratio = link_karma / total_karma if total_karma > 0 else 0.0
            if link_ratio > 0.9:  # Over 90% link karma
                scores['karma_score'] *= 0.7  # Suspicious - mainly posting links
            elif link_ratio < 0.1:  # Less than 10% link karma
                scores['karma_score'] *= 0.9  # Slightly suspicious - mainly commenting

            # Check for karma acceleration
            recent_karma = sum(float(c.get('score', 0)) for c in data.get('comments', [])[-50:])
            karma_acceleration = recent_karma / total_karma if total_karma > 0 else 0.0
            if karma_acceleration > 0.5:  # 50% of karma from recent posts
                scores['karma_score'] *= 0.8  # Suspicious rapid karma gain

            # Store metrics separately
            scores['metrics'] = {
                'total_karma': float(total_karma),
                'link_ratio': float(link_ratio),
                'recent_karma_ratio': float(karma_acceleration)
            }

            return scores

        except Exception as e:
            # Return safe defaults if any error occurs
            return {
                'karma_score': 0.5,  # Neutral score
                'metrics': {
                    'total_karma': 0.0,
                    'link_ratio': 0.0,
                    'recent_karma_ratio': 0.0
                }
            }