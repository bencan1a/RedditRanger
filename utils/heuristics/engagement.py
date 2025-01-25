from typing import Dict, Any, List
from datetime import datetime, timedelta
from .base import BaseHeuristic

class EngagementHeuristic(BaseHeuristic):
    """Analyzes user engagement patterns"""
    
    def analyze(self, data: Dict[str, Any]) -> Dict[str, float]:
        scores = {}
        
        # Analyze post to comment ratio
        scores['interaction_score'] = self._analyze_interaction_ratio(data)
        
        # Analyze response timing
        scores['response_score'] = self._analyze_response_timing(data)
        
        # Analyze engagement depth
        scores['depth_score'] = self._analyze_engagement_depth(data)
        
        return scores
        
    def _analyze_interaction_ratio(self, data: Dict[str, Any]) -> float:
        """Analyze ratio between posts and comments"""
        num_comments = len(data['comments'])
        num_submissions = len(data.get('submissions', []))
        
        if num_comments + num_submissions == 0:
            return 0.8  # Default for new accounts
            
        # Calculate ratio of comments to total posts
        comment_ratio = num_comments / max(1, (num_comments + num_submissions))
        
        if comment_ratio < 0.1:  # Almost no comments
            return 0.3  # Very suspicious
        elif comment_ratio < 0.3:  # Low comment ratio
            return 0.5
        elif comment_ratio > 0.9:  # Almost no submissions
            return 0.7  # Slightly suspicious
        return 0.9  # Healthy mix
        
    def _analyze_response_timing(self, data: Dict[str, Any]) -> float:
        """Analyze timing of responses to other posts"""
        if not data['comments']:
            return 0.8
            
        # Calculate response times for comments
        quick_responses = 0
        total_responses = 0
        
        for comment in data['comments']:
            if 'parent_created_utc' in comment:
                response_time = (comment['created_utc'] - 
                               comment['parent_created_utc']).total_seconds()
                               
                if response_time < 30:  # Less than 30 seconds
                    quick_responses += 1
                total_responses += 1
                
        if total_responses == 0:
            return 0.8
            
        quick_ratio = quick_responses / total_responses
        
        if quick_ratio > 0.5:  # Majority quick responses
            return 0.3
        elif quick_ratio > 0.3:  # Many quick responses
            return 0.5
        elif quick_ratio > 0.1:  # Some quick responses
            return 0.7
        return 0.9  # Natural response times
        
    def _analyze_engagement_depth(self, data: Dict[str, Any]) -> float:
        """Analyze depth of conversation engagement"""
        if not data['comments']:
            return 0.8
            
        # Analyze comment chains and discussion depth
        thread_depths = []
        current_thread = []
        
        for comment in sorted(data['comments'], key=lambda x: x['created_utc']):
            if current_thread and (comment['created_utc'] - 
                                 current_thread[-1]['created_utc'] > 
                                 timedelta(hours=1)):
                thread_depths.append(len(current_thread))
                current_thread = []
            current_thread.append(comment)
            
        if current_thread:
            thread_depths.append(len(current_thread))
            
        if not thread_depths:
            return 0.8
            
        avg_depth = sum(thread_depths) / len(thread_depths)
        
        if avg_depth < 1.5:  # Mostly single comments
            return 0.5
        elif avg_depth < 2.5:  # Some back-and-forth
            return 0.7
        elif avg_depth < 4:  # Good engagement
            return 0.9
        return 1.0  # Deep conversations
