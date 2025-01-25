from datetime import datetime, timezone
from typing import Dict, Any
from .base import BaseHeuristic

class AccountAgeHeuristic(BaseHeuristic):
    """Analyzes account age patterns"""

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            account_age = datetime.now(timezone.utc) - data['created_utc']
            account_age_days = float(account_age.days)

            # Calculate metrics
            post_rate = float(len(data.get('comments', [])) / max(1, account_age_days))
            active_days = self._get_active_days(data.get('comments', []))

            # Base age score (newer accounts are more suspicious)
            age_score = float(self.normalize_score(account_age_days / 365))  # Normalize to 1 year

            # Check for high volume in new accounts
            if account_age_days < 30:  # Account less than a month old
                if post_rate > 50:  # More than 50 posts per day
                    age_score *= 0.5  # Increase suspicion

            # Check for sudden activity changes
            if account_age_days > 180:  # 6 months or older
                recent_activity = float(len([d for d in active_days 
                    if (datetime.now(timezone.utc) - d).days <= 30]))
                historical_activity = float(len([d for d in active_days 
                    if (datetime.now(timezone.utc) - d).days > 30]))

                if historical_activity == 0 and recent_activity > 0:
                    age_score *= 0.7  # Suspicious sudden activity

            # Store metrics separately
            metrics = {
                'account_age_days': float(account_age_days),
                'post_frequency': float(post_rate),
                'active_days': float(len(active_days)),
                'recent_activity_ratio': float(
                    recent_activity / max(1, historical_activity + recent_activity)
                    if 'recent_activity' in locals() else 0.0
                )
            }

            return {
                'age_score': float(age_score),
                'metrics': metrics
            }

        except Exception as e:
            # Return safe defaults
            return {
                'age_score': 0.8,
                'metrics': {
                    'account_age_days': 0.0,
                    'post_frequency': 0.0,
                    'active_days': 0.0,
                    'recent_activity_ratio': 0.0
                }
            }

    def _get_active_days(self, comments):
        """Get unique days with activity"""
        try:
            return sorted(set(comment['created_utc'].date() 
                            for comment in comments 
                            if 'created_utc' in comment))
        except Exception:
            return []