from typing import Dict, Any
from .base import BaseHeuristic

class KarmaHeuristic(BaseHeuristic):
    """Analyzes karma patterns and trophy history"""

    def analyze(self, data: Dict[str, Any]) -> Dict[str, float]:
        try:
            # Initialize scores dictionary
            scores = {}

            # Safely extract karma values with type conversion
            comment_karma = float(data.get('comment_karma', 0))
            link_karma = float(data.get('link_karma', 0))
            total_karma = max(1.0, comment_karma + link_karma)

            # Calculate the base karma score
            base_score = self.normalize_score(total_karma / 10000)  # Normalize to 10k karma
            scores['karma_score'] = float(base_score)

            # Extract metrics separately
            metrics = {
                'total_karma': float(total_karma),
                'link_ratio': float(link_karma / total_karma if total_karma > 0 else 0.0),
                'recent_karma_ratio': 0.0  # Default value
            }

            # Calculate recent karma ratio if comments are available
            if data.get('comments'):
                recent_karma = sum(float(c.get('score', 0)) for c in data['comments'][-50:])
                metrics['recent_karma_ratio'] = float(recent_karma / total_karma if total_karma > 0 else 0.0)

            # Apply score modifiers based on patterns
            if total_karma > 100000:  # Extremely high karma
                scores['karma_score'] *= 0.8
            elif total_karma < 10:  # Extremely low karma
                scores['karma_score'] *= 0.6

            if metrics['link_ratio'] > 0.9:  # Over 90% link karma
                scores['karma_score'] *= 0.7
            elif metrics['link_ratio'] < 0.1:  # Less than 10% link karma
                scores['karma_score'] *= 0.9

            if metrics['recent_karma_ratio'] > 0.5:  # 50% of karma from recent posts
                scores['karma_score'] *= 0.8

            # Store metrics separately from scores
            scores['metrics'] = metrics

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