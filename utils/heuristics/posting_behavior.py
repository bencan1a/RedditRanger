from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from .base import BaseHeuristic
import numpy as np

class PostingBehaviorHeuristic(BaseHeuristic):
    """Analyzes posting frequency and timing patterns"""

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Combine comments and submissions chronologically
            all_posts = []
            for item in data.get('comments', []):
                all_posts.append({
                    'time': item.get('created_utc', datetime.now(timezone.utc)),
                    'type': 'comment'
                })
            for item in data.get('submissions', []):
                all_posts.append({
                    'time': item.get('created_utc', datetime.now(timezone.utc)),
                    'type': 'submission'
                })

            all_posts.sort(key=lambda x: x['time'])

            if not all_posts:
                return {
                    'frequency_score': 0.8,  # Neutral default
                    'interval_score': 0.8,
                    'timezone_score': 0.8,
                    'metrics': {
                        'posts_per_day': 0.0,
                        'avg_interval': 0.0,
                        'sleep_ratio': 0.0
                    }
                }

            # Calculate metrics
            time_diff_days = max(1, (all_posts[-1]['time'] - all_posts[0]['time']).days)
            posts_per_day = float(len(all_posts) / time_diff_days)

            intervals = self._calculate_intervals([post['time'] for post in all_posts])
            hour_distribution = self._analyze_hour_distribution([post['time'].hour for post in all_posts])

            # Calculate scores
            frequency_score = float(self._calculate_frequency_score(posts_per_day))
            interval_score = float(self._analyze_intervals(intervals)) if intervals else 0.8
            timezone_score = float(self._calculate_timezone_score(hour_distribution))

            # Store metrics separately
            metrics = {
                'posts_per_day': float(posts_per_day),
                'avg_interval': float(np.mean(intervals)) if intervals else 0.0,
                'sleep_ratio': float(self._calculate_sleep_ratio(hour_distribution))
            }

            return {
                'frequency_score': frequency_score,
                'interval_score': interval_score,
                'timezone_score': timezone_score,
                'metrics': metrics
            }

        except Exception as e:
            # Return safe defaults with explicit float conversion
            return {
                'frequency_score': 0.8,
                'interval_score': 0.8,
                'timezone_score': 0.8,
                'metrics': {
                    'posts_per_day': 0.0,
                    'avg_interval': 0.0,
                    'sleep_ratio': 0.0
                }
            }

    def _calculate_intervals(self, timestamps: List[datetime]) -> List[float]:
        """Calculate time intervals between posts in minutes"""
        if len(timestamps) < 2:
            return []
        return [float((timestamps[i+1] - timestamps[i]).total_seconds() / 60)
                for i in range(len(timestamps)-1)]

    def _analyze_intervals(self, intervals: List[float]) -> float:
        if not intervals:
            return 0.8

        std_dev = float(np.std(intervals))
        mean_interval = float(np.mean(intervals))

        if mean_interval == 0:
            return 0.8

        cv = std_dev / mean_interval  # Coefficient of variation

        if cv < 0.1:  # Very consistent intervals
            return 0.2
        elif cv < 0.3:  # Somewhat consistent
            return 0.4
        elif cv < 0.5:  # Natural variation
            return 0.8
        return 1.0

    def _analyze_hour_distribution(self, hours: List[int]) -> Dict[int, float]:
        """Analyze distribution of posting hours"""
        counts = {hour: float(hours.count(hour)) for hour in range(24)}
        total = sum(counts.values())
        if total > 0:
            return {hour: float(count / total) for hour, count in counts.items()}
        return {hour: 0.0 for hour in range(24)}

    def _calculate_sleep_ratio(self, hour_dist: Dict[int, float]) -> float:
        """Calculate ratio of posts during sleep hours (2 AM to 6 AM)"""
        sleep_hours = set(range(2, 6))
        sleep_posts = sum(hour_dist.get(h, 0.0) for h in sleep_hours)
        return float(sleep_posts)

    def _calculate_frequency_score(self, posts_per_day: float) -> float:
        """Score based on average posts per day"""
        if posts_per_day > 50:  # Extremely high frequency
            return 0.2
        elif posts_per_day > 20:  # High frequency
            return 0.4
        elif posts_per_day > 10:  # Moderate frequency
            return 0.6
        return 0.8  # Normal frequency

    def _calculate_timezone_score(self, hour_dist: Dict[int, float]) -> float:
        """Score based on posting hour distribution"""
        sleep_ratio = self._calculate_sleep_ratio(hour_dist)

        if sleep_ratio > 0.2:  # More than 20% posts during sleep hours
            return 0.4
        elif sleep_ratio > 0.1:  # 10-20% posts during sleep hours
            return 0.6
        return 0.8  # Normal sleep pattern