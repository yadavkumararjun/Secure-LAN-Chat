import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any
from ..config import settings


class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory sliding-window rate limiter.
    Enforces maximum request/event rates per key (user ID or client IP)
    to prevent brute-force attacks, flooding, and denial-of-service.
    """

    def __init__(self, max_requests: int = 10, window_seconds: float = 3.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps = defaultdict(deque)
        self._lock = Lock()

    def is_allowed(self, key: Any) -> bool:
        """
        Check if the key is permitted to perform the action under the sliding window limit.
        Returns True if allowed, False if rate-limited.
        """
        now = time.time()
        with self._lock:
            queue = self._timestamps[key]

            # Evict timestamps older than the sliding window
            cutoff = now - self.window_seconds
            while queue and queue[0] <= cutoff:
                queue.popleft()

            if len(queue) >= self.max_requests:
                return False

            queue.append(now)
            return True

    def reset(self, key: Any):
        """Reset rate-limit history for a given key (useful in tests)."""
        with self._lock:
            if key in self._timestamps:
                self._timestamps[key].clear()

    def reset_all(self):
        """Clear all tracked keys and timestamps."""
        with self._lock:
            self._timestamps.clear()


# Pre-configured rate limiters based on centralized settings
chat_rate_limiter = SlidingWindowRateLimiter(
    max_requests=settings.RATE_LIMIT_CHAT_MESSAGES,
    window_seconds=settings.RATE_LIMIT_CHAT_WINDOW_SECONDS,
)

auth_rate_limiter = SlidingWindowRateLimiter(
    max_requests=settings.RATE_LIMIT_AUTH_ATTEMPTS,
    window_seconds=settings.RATE_LIMIT_AUTH_WINDOW_SECONDS,
)

upload_rate_limiter = SlidingWindowRateLimiter(
    max_requests=settings.RATE_LIMIT_UPLOAD_FILES,
    window_seconds=settings.RATE_LIMIT_UPLOAD_WINDOW_SECONDS,
)
