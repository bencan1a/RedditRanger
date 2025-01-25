```python
import time
from collections import defaultdict
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class TokenBucket:
    """Token bucket algorithm implementation for rate limiting."""
    def __init__(self, tokens: int, fill_rate: float):
        self.capacity = tokens
        self.tokens = tokens
        self.fill_rate = fill_rate
        self.last_update = time.time()

    def consume(self, tokens: int = 1) -> bool:
        now = time.time()
        # Add tokens based on time passed
        time_passed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + time_passed * self.fill_rate)
        self.last_update = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

class RateLimiter:
    """Rate limiter using token bucket algorithm."""
    def __init__(self, tokens: int = 5, fill_rate: float = 0.1):
        """
        Initialize rate limiter
        :param tokens: Maximum number of tokens (requests)
        :param fill_rate: Rate at which tokens are added (tokens per second)
        """
        self.buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(tokens=tokens, fill_rate=fill_rate)
        )

    def check_rate_limit(self, key: str) -> Tuple[bool, Dict]:
        """
        Check if request should be rate limited
        :param key: Identifier for the client (e.g., IP address)
        :return: Tuple of (is_allowed, headers)
        """
        bucket = self.buckets[key]
        allowed = bucket.consume()
        
        # Calculate reset time
        tokens_needed = 1 if allowed else 1 - bucket.tokens
        reset_after = tokens_needed / bucket.fill_rate

        headers = {
            'X-RateLimit-Limit': str(bucket.capacity),
            'X-RateLimit-Remaining': str(int(bucket.tokens)),
            'X-RateLimit-Reset': str(int(time.time() + reset_after))
        }

        if not allowed:
            logger.warning(f"Rate limit exceeded for {key}")
            headers['Retry-After'] = str(int(reset_after))

        return allowed, headers
```
