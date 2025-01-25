from typing import Dict, Any
from .base import BaseHeuristic

class KarmaHeuristic(BaseHeuristic):
    """Analyzes karma patterns and trophy history"""
    
    def analyze(self, data: Dict[str, Any]) -> Dict[str, float]:
        comment_karma = data['comment_karma']
        link_karma = data['link_karma']
        total_karma = comment_karma + link_karma
        
        # Base karma score
        karma_score = self.normalize_score(total_karma / 10000)  # Normalize to 10k karma
        
        # Check for extreme karma patterns
        if total_karma > 100000:  # Extremely high karma
            karma_score *= 0.8  # Slightly suspicious
        elif total_karma < 10:  # Extremely low karma
            karma_score *= 0.6  # More suspicious
            
        # Analyze karma ratio
        if total_karma > 0:
            link_ratio = link_karma / total_karma
            if link_ratio > 0.9:  # Over 90% link karma
                karma_score *= 0.7  # Suspicious - mainly posting links
            elif link_ratio < 0.1:  # Less than 10% link karma
                karma_score *= 0.9  # Slightly suspicious - mainly commenting
        
        # Check for karma acceleration
        recent_karma = sum(c['score'] for c in data['comments'][-50:]) if len(data['comments']) >= 50 else 0
        if recent_karma > total_karma * 0.5:  # 50% of karma from recent posts
            karma_score *= 0.8  # Suspicious rapid karma gain
            
        return {
            'karma_score': karma_score,
            'metrics': {
                'total_karma': total_karma,
                'link_ratio': link_karma / max(1, total_karma),
                'recent_karma_ratio': recent_karma / max(1, total_karma)
            }
        }
