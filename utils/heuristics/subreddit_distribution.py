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

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Get subreddit history
        subreddit_history = self._get_subreddit_history(data)
        if not subreddit_history:
            return {
                'diversity_score': 0.8,
                'topic_change_score': 0.8,
                'promotional_score': 0.8,
                'metrics': {
                    'unique_subreddits': 0.0,
                    'total_subreddits': 0.0,
                    'promo_ratio': 0.0,
                    'topic_similarity': 0.0
                }
            }

        # Analyze subreddit patterns
        diversity_score = float(self._analyze_diversity(subreddit_history))
        topic_change_score = float(self._analyze_topic_changes(subreddit_history))
        promotional_score = float(self._analyze_promotional_content(subreddit_history))

        # Calculate metrics
        subreddits = [h['subreddit'] for h in subreddit_history]
        counts = Counter(subreddits)
        promo_count = sum(1 for sub in set(subreddits) 
                         if any(kw in sub for kw in self.promotional_keywords))

        metrics = {
            'unique_subreddits': float(len(set(subreddits))),
            'total_subreddits': float(len(subreddits)),
            'promo_ratio': float(promo_count / max(1, len(set(subreddits)))),
            'topic_similarity': float(self._calculate_topic_similarity(subreddit_history))
        }

        return {
            'diversity_score': diversity_score,
            'topic_change_score': topic_change_score,
            'promotional_score': promotional_score,
            'metrics': metrics
        }

    def _get_subreddit_history(self, data: Dict[str, Any]) -> List[Dict]:
        """Compile chronological subreddit history"""
        history = []

        # Add comments
        for comment in data.get('comments', []):
            history.append({
                'time': comment.get('created_utc', None),
                'subreddit': str(comment.get('subreddit', '')).lower()
            })

        # Add submissions
        for submission in data.get('submissions', []):
            history.append({
                'time': submission.get('created_utc', None),
                'subreddit': str(submission.get('subreddit', '')).lower()
            })

        # Sort by time and filter invalid entries
        return sorted(
            (h for h in history if h['time'] is not None and h['subreddit']),
            key=lambda x: x['time']
        )

    def _analyze_diversity(self, history: List[Dict]) -> float:
        """Analyze subreddit diversity"""
        subreddits = [h['subreddit'] for h in history]
        unique_count = len(set(subreddits))

        if len(subreddits) < 5:  # Too few posts for meaningful analysis
            return 0.8

        # Calculate concentration using Counter
        counts = Counter(subreddits)
        top_ratio = float(counts.most_common(1)[0][1] / len(subreddits))

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

        similarity = float(overlap / total_subs)

        if similarity < 0.1:  # Almost complete change
            return 0.3
        elif similarity < 0.3:  # Major change
            return 0.5
        elif similarity < 0.5:  # Moderate change
            return 0.7
        return 0.9  # Natural evolution

    def _analyze_promotional_content(self, history: List[Dict]) -> float:
        """Analyze presence in promotional subreddits"""
        subreddits = [h['subreddit'] for h in history]
        promo_count = sum(
            1 for sub in subreddits 
            if any(kw in sub for kw in self.promotional_keywords)
        )

        promo_ratio = float(promo_count / max(1, len(subreddits)))

        if promo_ratio > 0.5:  # Majority promotional
            return 0.3
        elif promo_ratio > 0.3:  # High promotional
            return 0.5
        elif promo_ratio > 0.1:  # Some promotional
            return 0.7
        return 0.9  # Little/no promotional

    def _calculate_topic_similarity(self, history: List[Dict]) -> float:
        """Calculate similarity between historical and recent subreddits"""
        if len(history) < 2:
            return 1.0

        midpoint = len(history) // 2
        historical = set(h['subreddit'] for h in history[:midpoint])
        recent = set(h['subreddit'] for h in history[midpoint:])

        if not historical or not recent:
            return 1.0

        intersection = len(historical & recent)
        union = len(historical | recent)

        return float(intersection / max(1, union))