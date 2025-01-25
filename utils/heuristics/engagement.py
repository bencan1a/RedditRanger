from typing import Dict, Any, List
from datetime import datetime, timedelta
from .base import BaseHeuristic

class EngagementHeuristic(BaseHeuristic):
    """Analyzes user engagement patterns"""

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            scores = {}

            # Analyze post to comment ratio
            interaction_score = float(self._analyze_interaction_ratio(data))

            # Analyze response timing
            response_score = float(self._analyze_response_timing(data))

            # Analyze engagement depth
            depth_score = float(self._analyze_engagement_depth(data))

            # Calculate metrics
            num_comments = len(data.get('comments', []))
            num_submissions = len(data.get('submissions', []))
            total_posts = max(1, num_comments + num_submissions)

            metrics = {
                'comment_ratio': float(num_comments / total_posts),
                'total_interactions': float(total_posts),
                'avg_response_time': float(self._calculate_avg_response_time(data)),
                'conversation_depth': float(self._calculate_conversation_depth(data))
            }

            return {
                'interaction_score': interaction_score,
                'response_score': response_score,
                'depth_score': depth_score,
                'metrics': metrics
            }

        except Exception as e:
            # Return safe defaults
            return {
                'interaction_score': 0.8,
                'response_score': 0.8,
                'depth_score': 0.8,
                'metrics': {
                    'comment_ratio': 0.0,
                    'total_interactions': 0.0,
                    'avg_response_time': 0.0,
                    'conversation_depth': 0.0
                }
            }

    def _analyze_interaction_ratio(self, data: Dict[str, Any]) -> float:
        """Analyze ratio between posts and comments"""
        num_comments = len(data.get('comments', []))
        num_submissions = len(data.get('submissions', []))

        if num_comments + num_submissions == 0:
            return 0.8  # Default for new accounts

        # Calculate ratio of comments to total posts
        comment_ratio = float(num_comments / max(1, (num_comments + num_submissions)))

        if comment_ratio < 0.1:  # Almost no comments
            return 0.3  # Very suspicious
        elif comment_ratio < 0.3:  # Low comment ratio
            return 0.5
        elif comment_ratio > 0.9:  # Almost no submissions
            return 0.7  # Slightly suspicious
        return 0.9  # Healthy mix

    def _analyze_response_timing(self, data: Dict[str, Any]) -> float:
        """Analyze timing of responses to other posts"""
        if not data.get('comments', []):
            return 0.8

        # Calculate response times for comments
        response_times = self._calculate_response_times(data.get('comments', []))
        if not response_times:
            return 0.8

        quick_responses = sum(1 for t in response_times if t < 30)  # Less than 30 seconds
        quick_ratio = float(quick_responses / max(1, len(response_times)))

        if quick_ratio > 0.5:  # Majority quick responses
            return 0.3
        elif quick_ratio > 0.3:  # Many quick responses
            return 0.5
        elif quick_ratio > 0.1:  # Some quick responses
            return 0.7
        return 0.9  # Natural response times

    def _analyze_engagement_depth(self, data: Dict[str, Any]) -> float:
        """Analyze depth of conversation engagement"""
        thread_depths = self._calculate_thread_depths(data.get('comments', []))

        if not thread_depths:
            return 0.8

        avg_depth = float(sum(thread_depths) / max(1, len(thread_depths)))

        if avg_depth < 1.5:  # Mostly single comments
            return 0.5
        elif avg_depth < 2.5:  # Some back-and-forth
            return 0.7
        elif avg_depth < 4:  # Good engagement
            return 0.9
        return 1.0  # Deep conversations

    def _calculate_response_times(self, comments: List[Dict]) -> List[float]:
        """Calculate response times in seconds"""
        try:
            return [
                float((comment['created_utc'] - comment['parent_created_utc']).total_seconds())
                for comment in comments
                if 'parent_created_utc' in comment and 'created_utc' in comment
            ]
        except Exception:
            return []

    def _calculate_thread_depths(self, comments: List[Dict]) -> List[int]:
        """Calculate depths of conversation threads"""
        try:
            thread_depths = []
            current_thread = []

            for comment in sorted(comments, key=lambda x: x.get('created_utc', datetime.min)):
                if (current_thread and 
                    (comment['created_utc'] - current_thread[-1]['created_utc']) > 
                    timedelta(hours=1)):
                    thread_depths.append(len(current_thread))
                    current_thread = []
                current_thread.append(comment)

            if current_thread:
                thread_depths.append(len(current_thread))

            return thread_depths
        except Exception:
            return []

    def _calculate_avg_response_time(self, data: Dict[str, Any]) -> float:
        """Calculate average response time in seconds"""
        response_times = self._calculate_response_times(data.get('comments', []))
        if not response_times:
            return 0.0
        return float(sum(response_times) / len(response_times))

    def _calculate_conversation_depth(self, data: Dict[str, Any]) -> float:
        """Calculate average conversation depth"""
        thread_depths = self._calculate_thread_depths(data.get('comments', []))
        if not thread_depths:
            return 0.0
        return float(sum(thread_depths) / len(thread_depths))