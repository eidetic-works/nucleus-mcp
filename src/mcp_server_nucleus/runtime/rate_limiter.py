"""
Nucleus Runtime - Rate Limiter (DoS Protection)
================================================
Prevents resource exhaustion from tool spam or malicious clients.

SECURITY: This module addresses vulnerability C47 identified in
the exhaustive design thinking analysis (Feb 24, 2026).

Attack vector: Malicious client spams MCP tools, exhausts CPU/memory
Defense: Token bucket rate limiting per client/tool

References:
- Evidence: E071, E072
"""

import time
import threading
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logger = logging.getLogger("nucleus.rate_limiter")


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: float
    fill_rate: float  # tokens per second
    tokens: float = None
    last_fill: float = None
    
    def __post_init__(self):
        if self.tokens is None:
            self.tokens = self.capacity  # Start full
        if self.last_fill is None:
            self.last_fill = time.time()
    
    def consume(self, tokens: float = 1.0) -> bool:
        """
        Try to consume tokens from bucket.
        
        Returns True if tokens available, False if rate limited.
        """
        now = time.time()
        elapsed = now - self.last_fill
        
        # Refill tokens
        self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
        self.last_fill = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def time_until_available(self, tokens: float = 1.0) -> float:
        """Calculate seconds until tokens available."""
        if self.tokens >= tokens:
            return 0.0
        needed = tokens - self.tokens
        return needed / self.fill_rate


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    def __init__(self, retry_after: float, message: str = "Rate limit exceeded"):
        self.retry_after = retry_after
        self.message = message
        super().__init__(f"{message}. Retry after {retry_after:.1f}s")


class RateLimiter:
    """
    Rate limiter for MCP tools.
    
    Supports:
    - Per-client rate limiting
    - Per-tool rate limiting
    - Global rate limiting
    - Configurable limits
    """
    
    def __init__(
        self,
        default_capacity: float = 100.0,
        default_fill_rate: float = 10.0,
        global_capacity: float = 1000.0,
        global_fill_rate: float = 100.0,
    ):
        """
        Initialize rate limiter.
        
        Args:
            default_capacity: Default bucket capacity per client
            default_fill_rate: Default tokens/second per client
            global_capacity: Global bucket capacity
            global_fill_rate: Global tokens/second
        """
        self.default_capacity = default_capacity
        self.default_fill_rate = default_fill_rate
        
        # Client buckets: {client_id: TokenBucket}
        self._client_buckets: Dict[str, TokenBucket] = {}
        
        # Tool buckets: {tool_name: TokenBucket}
        self._tool_buckets: Dict[str, TokenBucket] = {}
        
        # Global bucket
        self._global_bucket = TokenBucket(global_capacity, global_fill_rate)
        
        # Tool-specific limits: {tool_name: (capacity, fill_rate)}
        self._tool_limits: Dict[str, Tuple[float, float]] = {}
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        # Statistics
        self._stats = defaultdict(int)
    
    def set_tool_limit(
        self,
        tool_name: str,
        capacity: float,
        fill_rate: float
    ) -> None:
        """Set custom rate limit for a specific tool."""
        self._tool_limits[tool_name] = (capacity, fill_rate)
    
    def check(
        self,
        client_id: str = "default",
        tool_name: str = "default",
        tokens: float = 1.0
    ) -> bool:
        """
        Check if request is allowed.
        
        Args:
            client_id: Client identifier
            tool_name: Tool being called
            tokens: Tokens to consume
            
        Returns:
            True if allowed, False if rate limited
        """
        with self._lock:
            # Check global limit
            if not self._global_bucket.consume(tokens):
                self._stats["global_limited"] += 1
                return False
            
            # Get or create client bucket
            if client_id not in self._client_buckets:
                self._client_buckets[client_id] = TokenBucket(
                    self.default_capacity,
                    self.default_fill_rate
                )
            
            if not self._client_buckets[client_id].consume(tokens):
                self._stats["client_limited"] += 1
                return False
            
            # Check tool-specific limit if exists
            if tool_name in self._tool_limits:
                if tool_name not in self._tool_buckets:
                    cap, rate = self._tool_limits[tool_name]
                    self._tool_buckets[tool_name] = TokenBucket(cap, rate)
                
                if not self._tool_buckets[tool_name].consume(tokens):
                    self._stats["tool_limited"] += 1
                    return False
            
            self._stats["allowed"] += 1
            return True
    
    def check_or_raise(
        self,
        client_id: str = "default",
        tool_name: str = "default",
        tokens: float = 1.0
    ) -> None:
        """
        Check rate limit, raise RateLimitError if exceeded.
        """
        if not self.check(client_id, tool_name, tokens):
            # Calculate retry time
            with self._lock:
                retry_after = max(
                    self._global_bucket.time_until_available(tokens),
                    self._client_buckets.get(
                        client_id, 
                        TokenBucket(1, 1)
                    ).time_until_available(tokens)
                )
            
            logger.warning(
                f"Rate limit exceeded: client={client_id}, tool={tool_name}"
            )
            raise RateLimitError(retry_after)
    
    def get_stats(self) -> Dict[str, int]:
        """Get rate limiting statistics."""
        return dict(self._stats)
    
    def reset_client(self, client_id: str) -> None:
        """Reset rate limit for a specific client."""
        with self._lock:
            if client_id in self._client_buckets:
                del self._client_buckets[client_id]
    
    def reset_all(self) -> None:
        """Reset all rate limits."""
        with self._lock:
            self._client_buckets.clear()
            self._tool_buckets.clear()
            self._global_bucket = TokenBucket(
                self._global_bucket.capacity,
                self._global_bucket.fill_rate
            )
            self._stats.clear()


# Global rate limiter instance
_global_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter."""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter()
    return _global_limiter


def rate_limit(
    client_id: str = "default",
    tool_name: str = "default",
    tokens: float = 1.0
) -> bool:
    """
    Convenience function to check rate limit.
    
    Returns True if allowed, False if limited.
    """
    return get_rate_limiter().check(client_id, tool_name, tokens)


def rate_limit_or_raise(
    client_id: str = "default",
    tool_name: str = "default",
    tokens: float = 1.0
) -> None:
    """
    Convenience function to check rate limit, raise if exceeded.
    """
    get_rate_limiter().check_or_raise(client_id, tool_name, tokens)
