"""Global rate limiter for Gemini API calls.
CRITICAL: All Gemini generate_content calls MUST use rate_limited_generate_content.
"""

import threading
import time
from collections import deque
from typing import Callable

# Gemini SDK error types
from google.genai import errors as genai_errors
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


def _is_retryable(exc: BaseException) -> bool:
    """Check if exception is retryable (429, 5xx, network errors)."""
    if isinstance(exc, genai_errors.ServerError):
        return True  # 5xx errors
    if isinstance(exc, genai_errors.ClientError):
        # 429 Too Many Requests is retryable
        return exc.code == 429
    if isinstance(exc, ConnectionError):
        return True
    return False


class GeminiRateLimiter:
    """Thread-safe rate limiter using Condition variable.
    Does NOT sleep while holding the lock - uses Condition.wait() which releases.
    Supports dependency injection for testing.
    """

    def __init__(
        self,
        max_rpm: int = 15,
        time_fn: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        self._max_rpm = max_rpm
        self._time_fn = time_fn
        self._sleep_fn = sleep_fn
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)

    def acquire(self, timeout: float = 60.0) -> bool:
        """Block until rate limit allows another request.
        Returns True if acquired, False if timeout.
        Uses injected time_fn for testability.
        """
        deadline = self._time_fn() + timeout
        with self._condition:
            while True:
                now = self._time_fn()
                # Prune timestamps older than 60s
                while self._timestamps and self._timestamps[0] < now - 60:
                    self._timestamps.popleft()
                if len(self._timestamps) < self._max_rpm:
                    self._timestamps.append(now)
                    return True
                remaining = deadline - now
                if remaining <= 0:
                    return False
                # Calculate wait time until oldest timestamp expires
                wait_time = min(self._timestamps[0] + 60 - now + 0.1, remaining)
                if wait_time > 0:
                    # Release lock while sleeping (use injected sleep_fn for testing)
                    self._condition.release()
                    try:
                        self._sleep_fn(min(wait_time, 0.1))  # Sleep in small increments
                    finally:
                        self._condition.acquire()

    def reset(self):
        """Reset limiter state (for testing)."""
        with self._lock:
            self._timestamps.clear()


# Singleton with factory for testing
_rate_limiter: GeminiRateLimiter | None = None
_limiter_lock = threading.Lock()


def get_rate_limiter(
    max_rpm: int = 15,
    time_fn: Callable[[], float] | None = None,
    sleep_fn: Callable[[float], None] | None = None,
    _reset: bool = False,
) -> GeminiRateLimiter:
    """Get or create the global rate limiter singleton.
    Args:
            max_rpm: Max requests per minute
            time_fn: Injectable time function (for testing)
            sleep_fn: Injectable sleep function (for testing)
            _reset: Force create new instance (for testing only)
    """
    global _rate_limiter
    with _limiter_lock:
        if _rate_limiter is None or _reset:
            _rate_limiter = GeminiRateLimiter(
                max_rpm=max_rpm, time_fn=time_fn or time.monotonic, sleep_fn=sleep_fn or time.sleep
            )
        return _rate_limiter


def rate_limited_generate_content(
    client, model: str, contents, config, timeout: float = 60.0, max_retries: int = 3
):
    """Rate-limited wrapper for client.models.generate_content.
    CRITICAL: Each retry attempt acquires rate limit separately.
    All Gemini image generation calls MUST use this function.
    """
    limiter = get_rate_limiter()

    @retry(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    def _call_with_rate_limit():
        # Acquire rate limit for EACH attempt (including retries)
        if not limiter.acquire(timeout):
            raise TimeoutError("Rate limiter timeout - too many concurrent requests")
        return client.models.generate_content(model=model, contents=contents, config=config)

    return _call_with_rate_limit()


# Audit helper: grep for direct generate_content calls
AUDIT_PATTERN = r"client\.models\.generate_content\("
AUDIT_ALLOWED_FILES = [
    "rate_limiter.py",
]
