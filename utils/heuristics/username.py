import re
from typing import Dict, Any
from .base import BaseHeuristic

class UsernameHeuristic(BaseHeuristic):
    """Analyzes username patterns for bot-like characteristics"""
    
    def __init__(self):
        self.suspicious_patterns = [
            r'\d{4,}',  # 4+ consecutive numbers
            r'bot\d*',  # Contains 'bot'
            r'[A-Z][a-z]+\d{2,}',  # CamelCase followed by numbers
            r'[a-zA-Z]\d{3,}[a-zA-Z]',  # Letters with 3+ numbers
            r'(best|top|cheap|deal|price|buy|sell)\w*',  # Commercial terms
            r'\w+_\w+_\d{2,}',  # Words_With_Numbers
            r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}',  # Email patterns
            r'\d{3}[-.]?\d{3}[-.]?\d{4}'  # Phone number patterns
        ]
    
    def analyze(self, data: Dict[str, Any]) -> Dict[str, float]:
        username = data['username'].lower()
        username_score = 1.0
        
        # Check for suspicious patterns
        pattern_matches = []
        for pattern in self.suspicious_patterns:
            if re.search(pattern, username):
                username_score *= 0.8  # Reduce score for each suspicious pattern
                pattern_matches.append(pattern)
        
        # Check username entropy (randomness)
        entropy_score = self._calculate_entropy(username)
        if entropy_score > 4.5:  # Very random username
            username_score *= 0.9
            
        # Check length
        if len(username) > 20:  # Very long usernames are suspicious
            username_score *= 0.9
            
        return {
            'username_score': self.normalize_score(username_score),
            'metrics': {
                'pattern_matches': pattern_matches,
                'entropy': entropy_score,
                'length': len(username)
            }
        }
    
    def _calculate_entropy(self, username: str) -> float:
        """Calculate Shannon entropy of username"""
        import math
        prob = [float(username.count(c)) / len(username) for c in dict.fromkeys(list(username))]
        entropy = - sum(p * math.log(p) / math.log(2.0) for p in prob)
        return entropy
