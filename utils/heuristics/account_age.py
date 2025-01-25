from datetime import datetime, timezone
from typing import Dict, Any
from .base import BaseHeuristic

class AccountAgeHeuristic(BaseHeuristic):
    """Analyzes account age patterns"""
    
    def analyze(self, data: Dict[str, Any]) -> Dict[str, float]:
        account_age = datetime.now(timezone.utc) - data['created_utc']
        account_age_days = account_age.days
        
        # Base age score (newer accounts are more suspicious)
        age_score = self.normalize_score(account_age_days / 365)  # Normalize to 1 year
        
        # Check for high volume in new accounts
        if account_age_days < 30:  # Account less than a month old
            post_rate = len(data['comments']) / max(1, account_age_days)
            if post_rate > 50:  # More than 50 posts per day
                age_score *= 0.5  # Increase suspicion
        
        # Check for sudden activity changes
        active_days = self._get_active_days(data['comments'])
        if account_age_days > 180:  # 6 months or older
            recent_activity = len([d for d in active_days if (datetime.now(timezone.utc) - d).days <= 30])
            historical_activity = len([d for d in active_days if (datetime.now(timezone.utc) - d).days > 30])
            
            if historical_activity == 0 and recent_activity > 0:
                age_score *= 0.7  # Suspicious sudden activity
        
        return {
            'age_score': age_score,
            'metrics': {
                'account_age_days': account_age_days,
                'post_frequency': len(data['comments']) / max(1, account_age_days),
                'active_days': len(active_days)
            }
        }
    
    def _get_active_days(self, comments):
        """Get unique days with activity"""
        return sorted(set(comment['created_utc'].date() for comment in comments))
