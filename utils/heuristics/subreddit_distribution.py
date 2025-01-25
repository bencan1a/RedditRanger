from typing import Dict, Any, List, Set
from collections import Counter
from .base import BaseHeuristic

class SubredditHeuristic(BaseHeuristic):
    """Analyzes subreddit distribution and topic changes"""
    
    def __init__(self):
        self.promotional_keywords = {
            'free', 'deal', 'discount', 'promo', 'sale', 'offer',
            'buy', 'sell', 'price', 'shop', 'store', 'marketing'
        }
        
    def analyze(self, data: Dict[str, Any]) -> Dict[str, float]:
        # Get subreddit history
        subreddit_history = self._get_subreddit_history(data)
        if not subreddit_history:
            return {
                'diversity_score': 1.0,
                'topic_change_score': 1.0,
                'promotional_score': 1.0
            }
            
        # Analyze subreddit diversity
        diversity_score = self._analyze_diversity(subreddit_history)
        
        # Analyze topic changes
        topic_change_score = self._analyze_topic_changes(subreddit_history)
        
        # Analyze promotional content
        promotional_score = self._analyze_promotional_content(subreddit_history)
        
        return {
            'diversity_score': diversity_score,
            'topic_change_score': topic_change_score,
            'promotional_score': promotional_score
        }
        
    def _get_subreddit_history(self, data: Dict[str, Any]) -> List[Dict]:
        """Compile chronological subreddit history"""
        history = []
        
        # Add comments
        for comment in data['comments']:
            history.append({
                'time': comment['created_utc'],
                'subreddit': comment['subreddit'].lower()
            })
            
        # Add submissions
        for submission in data.get('submissions', []):
            history.append({
                'time': submission['created_utc'],
                'subreddit': submission['subreddit'].lower()
            })
            
        # Sort by time
        history.sort(key=lambda x: x['time'])
        return history
        
    def _analyze_diversity(self, history: List[Dict]) -> float:
        """Analyze subreddit diversity"""
        subreddits = [h['subreddit'] for h in history]
        unique_count = len(set(subreddits))
        
        if len(subreddits) < 5:  # Too few posts for meaningful analysis
            return 0.8
            
        # Calculate concentration using Counter
        counts = Counter(subreddits)
        top_ratio = counts.most_common(1)[0][1] / len(subreddits)
        
        if unique_count == 1:  # Only one subreddit
            return 0.4
        elif top_ratio > 0.8:  # Over 80% posts in one subreddit
            return 0.5
        elif top_ratio > 0.6:  # Over 60% posts in one subreddit
            return 0.7
        return 0.9  # Good diversity
        
    def _analyze_topic_changes(self, history: List[Dict]) -> float:
        """Analyze sudden changes in subreddit patterns"""
        if len(history) < 10:  # Need more data for meaningful analysis
            return 0.8
            
        # Look at recent vs historical distribution
        midpoint = len(history) // 2
        historical_subs = set(h['subreddit'] for h in history[:midpoint])
        recent_subs = set(h['subreddit'] for h in history[midpoint:])
        
        # Calculate overlap
        overlap = len(historical_subs & recent_subs)
        total_subs = len(historical_subs | recent_subs)
        
        if total_subs == 0:
            return 0.8
            
        similarity = overlap / total_subs
        
        if similarity < 0.1:  # Almost complete change
            return 0.3
        elif similarity < 0.3:  # Major change
            return 0.5
        elif similarity < 0.5:  # Moderate change
            return 0.7
        return 0.9  # Natural evolution
        
    def _analyze_promotional_content(self, history: List[Dict]) -> float:
        """Analyze presence in promotional subreddits"""
        promo_count = sum(
            1 for h in history 
            if any(kw in h['subreddit'] for kw in self.promotional_keywords)
        )
        
        promo_ratio = promo_count / max(1, len(history))
        
        if promo_ratio > 0.5:  # Majority promotional
            return 0.3
        elif promo_ratio > 0.3:  # High promotional
            return 0.5
        elif promo_ratio > 0.1:  # Some promotional
            return 0.7
        return 0.9  # Little/no promotional
