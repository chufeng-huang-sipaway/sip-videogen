"""Tests for the Gemini rate limiter."""

import threading
from unittest.mock import MagicMock, patch

import pytest
from google.genai import errors as genai_errors

from sip_studio.studio.services.rate_limiter import (
    GeminiRateLimiter,
    _is_retryable,
    get_rate_limiter,
    rate_limited_generate_content,
)


# Helper to create properly formatted Gemini errors
def _mk_err(code: int, msg: str):
    """Create Gemini error with proper response_json format."""
    return {"error": {"message": msg, "status": "ERROR"}}


class FakeClock:
    """Fake clock for testing rate limiter without wall time."""

    def __init__(self, start: float = 0.0):
        self._time = start
        self._lock = threading.Lock()

    def now(self) -> float:
        with self._lock:
            return self._time

    def advance(self, seconds: float):
        with self._lock:
            self._time += seconds

    def sleep(self, seconds: float):
        # Simulate time passing
        self.advance(seconds)


class TestGeminiRateLimiter:
    def test_rate_limiter_enforces_rpm(self):
        """20 calls, only 15 succeed before timeout (with max_rpm=15)."""
        clock = FakeClock()
        limiter = GeminiRateLimiter(max_rpm=15, time_fn=clock.now, sleep_fn=clock.sleep)
        acquired = 0
        # Try to acquire 20 times
        for _ in range(20):
            if limiter.acquire(timeout=0.1):
                acquired += 1
        # Only 15 should succeed (within the small timeout window)
        assert acquired == 15

    def test_rate_limiter_allows_after_window(self):
        """After 60s, older timestamps expire and new requests succeed."""
        clock = FakeClock()
        limiter = GeminiRateLimiter(max_rpm=3, time_fn=clock.now, sleep_fn=clock.sleep)
        # Acquire 3 (fill quota)
        for _ in range(3):
            assert limiter.acquire(timeout=1.0)
        # 4th should fail with short timeout
        assert not limiter.acquire(timeout=0.1)
        # Advance clock past 60s window
        clock.advance(61)
        # Now should succeed
        assert limiter.acquire(timeout=0.1)

    def test_rate_limiter_thread_safe(self):
        """10 concurrent threads, no corruption."""
        clock = FakeClock()
        limiter = GeminiRateLimiter(max_rpm=10, time_fn=clock.now, sleep_fn=clock.sleep)
        results = []
        lock = threading.Lock()

        def try_acquire():
            result = limiter.acquire(timeout=0.1)
            with lock:
                results.append(result)

        threads = [threading.Thread(target=try_acquire) for _ in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # Exactly 10 should succeed
        assert sum(1 for r in results if r) == 10
        assert sum(1 for r in results if not r) == 5

    def test_rate_limiter_timeout(self):
        """Returns False after timeout."""
        clock = FakeClock()
        limiter = GeminiRateLimiter(max_rpm=1, time_fn=clock.now, sleep_fn=clock.sleep)
        # Acquire first slot
        assert limiter.acquire(timeout=1.0)
        # Second should timeout
        assert not limiter.acquire(timeout=0.5)

    def test_rate_limiter_releases_lock_while_waiting(self):
        """Other threads can proceed while one is waiting."""
        clock = FakeClock()
        limiter = GeminiRateLimiter(max_rpm=1, time_fn=clock.now, sleep_fn=clock.sleep)
        # Fill quota
        limiter.acquire(timeout=1.0)
        # Track if reset was callable while another thread waits
        reset_called = threading.Event()

        def wait_for_slot():
            # This will block since quota is full
            limiter.acquire(timeout=5.0)

        def call_reset():
            # Sleep a tiny bit then call reset (which needs the lock)
            clock.advance(0.1)
            limiter.reset()
            reset_called.set()

        t1 = threading.Thread(target=wait_for_slot)
        t2 = threading.Thread(target=call_reset)
        t1.start()
        clock.advance(0.05)  # Let t1 start waiting
        t2.start()
        t2.join(timeout=2.0)
        t1.join(timeout=2.0)
        # Reset should have been callable (lock released during sleep)
        assert reset_called.is_set()

    def test_reset_clears_timestamps(self):
        """Reset clears all timestamps."""
        clock = FakeClock()
        limiter = GeminiRateLimiter(max_rpm=2, time_fn=clock.now, sleep_fn=clock.sleep)
        limiter.acquire(timeout=1.0)
        limiter.acquire(timeout=1.0)
        # Quota full
        assert not limiter.acquire(timeout=0.1)
        limiter.reset()
        # Should succeed now
        assert limiter.acquire(timeout=0.1)


class TestIsRetryable:
    def test_server_error_retryable(self):
        """ServerError (5xx) should be retryable."""
        err = genai_errors.ServerError(500, _mk_err(500, "server error"))
        assert _is_retryable(err)

    def test_client_error_429_retryable(self):
        """ClientError with code 429 should be retryable."""
        err = genai_errors.ClientError(429, _mk_err(429, "too many requests"))
        assert _is_retryable(err)

    def test_client_error_400_not_retryable(self):
        """ClientError with code 400 (bad request) should NOT be retryable."""
        err = genai_errors.ClientError(400, _mk_err(400, "bad request"))
        assert not _is_retryable(err)

    def test_client_error_403_not_retryable(self):
        """ClientError with code 403 (forbidden/content policy) should NOT be retryable."""
        err = genai_errors.ClientError(403, _mk_err(403, "content policy"))
        assert not _is_retryable(err)

    def test_connection_error_retryable(self):
        """ConnectionError should be retryable."""
        err = ConnectionError("network error")
        assert _is_retryable(err)

    def test_value_error_not_retryable(self):
        """ValueError should NOT be retryable."""
        err = ValueError("invalid")
        assert not _is_retryable(err)


class TestGetRateLimiter:
    def test_singleton_returns_same_instance(self):
        """get_rate_limiter returns same instance without _reset."""
        # Reset first to ensure clean state
        limiter1 = get_rate_limiter(_reset=True)
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2

    def test_reset_creates_new_instance(self):
        """_reset=True creates new instance."""
        limiter1 = get_rate_limiter(_reset=True)
        limiter2 = get_rate_limiter(_reset=True)
        assert limiter1 is not limiter2

    def test_custom_params_on_reset(self):
        """Custom time_fn/sleep_fn applied on reset."""
        clock = FakeClock()
        limiter = get_rate_limiter(max_rpm=5, time_fn=clock.now, sleep_fn=clock.sleep, _reset=True)
        # Acquire 5 (fill quota)
        for _ in range(5):
            assert limiter.acquire(timeout=1.0)
        # 6th should fail
        assert not limiter.acquire(timeout=0.1)


class TestRateLimitedGenerateContent:
    def test_successful_call(self):
        """Successful call returns result."""
        # Reset limiter for clean state
        get_rate_limiter(_reset=True)
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = "result"
        result = rate_limited_generate_content(mock_client, "model", "contents", "config")
        assert result == "result"
        mock_client.models.generate_content.assert_called_once_with(
            model="model", contents="contents", config="config"
        )

    def test_retry_on_429(self):
        """Retries TooManyRequests (429) errors."""
        get_rate_limiter(_reset=True)
        mock_client = MagicMock()
        err = genai_errors.ClientError(429, _mk_err(429, "too many requests"))
        mock_client.models.generate_content.side_effect = [err, err, "success"]
        result = rate_limited_generate_content(
            mock_client, "model", "contents", "config", max_retries=3
        )
        assert result == "success"
        assert mock_client.models.generate_content.call_count == 3

    def test_retry_on_server_error(self):
        """Retries ServerError (5xx) errors."""
        get_rate_limiter(_reset=True)
        mock_client = MagicMock()
        err = genai_errors.ServerError(500, _mk_err(500, "server error"))
        mock_client.models.generate_content.side_effect = [err, "success"]
        result = rate_limited_generate_content(
            mock_client, "model", "contents", "config", max_retries=3
        )
        assert result == "success"
        assert mock_client.models.generate_content.call_count == 2

    def test_no_retry_on_content_policy(self):
        """Does NOT retry InvalidArgument/content policy (4xx non-429) errors."""
        get_rate_limiter(_reset=True)
        mock_client = MagicMock()
        err = genai_errors.ClientError(400, _mk_err(400, "content policy violation"))
        mock_client.models.generate_content.side_effect = err
        with pytest.raises(genai_errors.ClientError):
            rate_limited_generate_content(mock_client, "model", "contents", "config", max_retries=3)
        # Should only try once (no retry)
        assert mock_client.models.generate_content.call_count == 1

    def test_retry_acquires_rate_limit_each_time(self):
        """Each retry attempt acquires rate limit separately."""
        clock = FakeClock()
        limiter = get_rate_limiter(max_rpm=10, time_fn=clock.now, sleep_fn=clock.sleep, _reset=True)
        mock_client = MagicMock()
        err = genai_errors.ServerError(500, _mk_err(500, "server error"))
        mock_client.models.generate_content.side_effect = [err, err, "success"]
        # Verify rate limit is acquired for each retry
        with patch.object(limiter, "acquire", wraps=limiter.acquire) as mock_acquire:
            result = rate_limited_generate_content(
                mock_client, "model", "contents", "config", max_retries=3
            )
            # 3 API calls = 3 rate limit acquisitions
            assert mock_acquire.call_count == 3
        assert result == "success"

    def test_timeout_raises_error(self):
        """Rate limiter timeout raises TimeoutError."""
        clock = FakeClock()
        # max_rpm=1, fill it up
        limiter = get_rate_limiter(max_rpm=1, time_fn=clock.now, sleep_fn=clock.sleep, _reset=True)
        limiter.acquire(timeout=1.0)  # Fill quota
        mock_client = MagicMock()
        with pytest.raises(TimeoutError, match="Rate limiter timeout"):
            rate_limited_generate_content(mock_client, "model", "contents", "config", timeout=0.1)
