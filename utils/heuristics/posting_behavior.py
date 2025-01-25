from datetime import datetime, timezone
from typing import Dict, Any, List
from .base import BaseHeuristic
import numpy as np

class PostingBehaviorHeuristic(BaseHeuristic):
    """Analyzes posting frequency and timing patterns"""
    
    def analyze(self, data: Dict[str, Any]) -> Dict[str, float]:
        # Combine comments and submissions chronologically
        all_posts = []
        for item in data['comments']:
            all_posts.append({
                'time': item['created_utc'],
                'type': 'comment'
            })
        for item in data.get('submissions', []):
            all_posts.append({
                'time': item['created_utc'],
                'type': 'submission'
            })
            
        all_posts.sort(key=lambda x: x['time'])
        
        if not all_posts:
            return {
                'frequency_score': 1.0,
                'interval_score': 1.0,
                'timezone_score': 1.0
            }
            
        scores = {}
        
        # Analyze posting frequency
        posts_per_day = len(all_posts) / max(1, (all_posts[-1]['time'] - all_posts[0]['time']).days)
        scores['frequency_score'] = self._calculate_frequency_score(posts_per_day)
        
        # Analyze posting intervals
        intervals = self._calculate_intervals([post['time'] for post in all_posts])
        scores['interval_score'] = self._analyze_intervals(intervals)
        
        # Analyze timezone patterns
        hour_distribution = self._analyze_hour_distribution([post['time'].hour for post in all_posts])
        scores['timezone_score'] = self._calculate_timezone_score(hour_distribution)
        
        return scores
        
    def _calculate_frequency_score(self, posts_per_day: float) -> float:
        """Score based on average posts per day"""
        if posts_per_day > 50:  # Extremely high frequency
            return 0.2
        elif posts_per_day > 20:  # High frequency
            return 0.4
        elif posts_per_day > 10:  # Moderate frequency
            return 0.6
        return 0.8  # Normal frequency
        
    def _calculate_intervals(self, timestamps: List[datetime]) -> List[float]:
        """Calculate time intervals between posts in minutes"""
        return [(timestamps[i+1] - timestamps[i]).total_seconds() / 60 
                for i in range(len(timestamps)-1)]
                
    def _analyze_intervals(self, intervals: List[float]) -> float:
        if not intervals:
            return 1.0
            
        # Check for consistent intervals
        std_dev = np.std(intervals)
        mean_interval = np.mean(intervals)
        
        if mean_interval == 0:
            return 0.0  # Suspicious: posts at exact same time
            
        cv = std_dev / mean_interval  # Coefficient of variation
        
        if cv < 0.1:  # Very consistent intervals
            return 0.2
        elif cv < 0.3:  # Somewhat consistent
            return 0.4
        elif cv < 0.5:  # Natural variation
            return 0.8
        return 1.0  # Random/natural intervals
        
    def _analyze_hour_distribution(self, hours: List[int]) -> Dict[int, int]:
        """Analyze distribution of posting hours"""
        return {hour: hours.count(hour) for hour in range(24)}
        
    def _calculate_timezone_score(self, hour_dist: Dict[int, int]) -> float:
        """Score based on posting hour distribution"""
        total_posts = sum(hour_dist.values())
        if total_posts == 0:
            return 1.0
            
        # Check for posts during typical sleep hours
        sleep_hours = set(range(2, 6))  # 2 AM to 6 AM
        sleep_posts = sum(hour_dist.get(h, 0) for h in sleep_hours)
        
        sleep_ratio = sleep_posts / total_posts
        
        if sleep_ratio > 0.2:  # More than 20% posts during sleep hours
            return 0.4
        elif sleep_ratio > 0.1:  # 10-20% posts during sleep hours
            return 0.6
        return 0.8  # Normal sleep pattern
