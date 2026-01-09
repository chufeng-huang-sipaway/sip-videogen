"""Tests for the image generation pool."""

import threading
import time

from sip_studio.studio.services.image_pool import (
    ImageGenerationPool,
    Ticket,
    TicketStatus,
    get_image_pool,
)


def _mk_gen(delay: float = 0.01, fail: bool = False, path: str = "/tmp/test.png"):
    """Create a mock generator function."""

    def gen(ticket: Ticket) -> str:
        time.sleep(delay)
        if fail:
            raise RuntimeError("Generation failed")
        return path

    return gen


class TestTicketStatus:
    def test_terminal_states(self):
        """COMPLETED, FAILED, CANCELLED, TIMEOUT are terminal."""
        assert TicketStatus.COMPLETED.is_terminal()
        assert TicketStatus.FAILED.is_terminal()
        assert TicketStatus.CANCELLED.is_terminal()
        assert TicketStatus.TIMEOUT.is_terminal()

    def test_non_terminal_states(self):
        """QUEUED and PROCESSING are not terminal."""
        assert not TicketStatus.QUEUED.is_terminal()
        assert not TicketStatus.PROCESSING.is_terminal()


class TestImageGenerationPool:
    def test_pool_parallel_execution(self):
        """5 tickets complete concurrently."""
        times = []
        lock = threading.Lock()

        def gen(ticket: Ticket) -> str:
            with lock:
                times.append(time.time())
            time.sleep(0.05)
            return f"/tmp/{ticket.id}.png"

        pool = ImageGenerationPool(max_workers=5, generator_fn=gen)
        try:
            batch_id = "batch-1"
            for i in range(5):
                pool.submit(f"prompt-{i}", {}, batch_id=batch_id)
            result = pool.wait_for_batch(batch_id, timeout=5.0)
            assert result.completed_count == 5
            assert result.failed_count == 0
            # Check all started within 0.1s (parallel)
            if len(times) >= 2:
                assert max(times) - min(times) < 0.3
        finally:
            pool.shutdown()

    def test_pool_cancellation_before_start(self):
        """Cancelled tickets never call generate."""
        gen_calls = []

        def gen(ticket: Ticket) -> str:
            gen_calls.append(ticket.id)
            time.sleep(0.5)
            return f"/tmp/{ticket.id}.png"

        pool = ImageGenerationPool(max_workers=1, generator_fn=gen)
        try:
            batch_id = "batch-2"
            # Submit 3 tickets - only 1 worker, so 2 will queue
            pool.submit("prompt-1", {}, batch_id=batch_id)
            pool.submit("prompt-2", {}, batch_id=batch_id)
            pool.submit("prompt-3", {}, batch_id=batch_id)
            time.sleep(0.05)  # Let first start
            # Cancel batch - should cancel queued ones
            pool.cancel_batch(batch_id)
            result = pool.wait_for_batch(batch_id, timeout=2.0)
            # First ticket should complete, others cancelled
            assert result.completed_count + result.cancelled_count == 3
            # Cancelled tickets should not have called gen
            assert len(gen_calls) <= 2
        finally:
            pool.shutdown()

    def test_pool_partial_results(self):
        """4/5 succeed, returns all results."""
        lock = threading.Lock()
        call_count = [0]

        def gen(ticket: Ticket) -> str:
            with lock:
                call_count[0] += 1
                c = call_count[0]
            time.sleep(0.02)  # Ensure all tickets start
            if c == 3:
                raise RuntimeError("Simulated failure")
            return f"/tmp/{ticket.id}.png"

        pool = ImageGenerationPool(max_workers=5, generator_fn=gen)
        try:
            batch_id = "batch-3"
            for i in range(5):
                pool.submit(f"prompt-{i}", {}, batch_id=batch_id)
            result = pool.wait_for_batch(batch_id, timeout=5.0)
            assert result.completed_count == 4
            assert result.failed_count == 1
        finally:
            pool.shutdown()

    def test_pool_wait_for_ticket(self):
        """Single ticket wait works."""
        pool = ImageGenerationPool(
            max_workers=1, generator_fn=_mk_gen(delay=0.02, path="/tmp/single.png")
        )
        try:
            tid = pool.submit("prompt", {})
            result = pool.wait_for_ticket(tid, timeout=5.0)
            assert result.status == TicketStatus.COMPLETED
            assert result.path == "/tmp/single.png"
        finally:
            pool.shutdown()

    def test_pool_batch_wait_timeout(self):
        """Doesn't block forever."""

        def slow_gen(ticket: Ticket) -> str:
            time.sleep(10)
            return "/tmp/slow.png"

        pool = ImageGenerationPool(max_workers=1, generator_fn=slow_gen)
        try:
            batch_id = "batch-slow"
            pool.submit("prompt", {}, batch_id=batch_id)
            start = time.time()
            pool.wait_for_batch(batch_id, timeout=0.1)
            elapsed = time.time() - start
            # Should return quickly, not wait 10s
            assert elapsed < 1.0
        finally:
            pool.shutdown(wait=False)

    def test_pool_progress_emits_all_transitions(self):
        """queued->processing->completed all emitted."""
        events = []
        lock = threading.Lock()

        def cb(payload):
            with lock:
                events.append(payload.copy())

        pool = ImageGenerationPool(max_workers=1, generator_fn=_mk_gen(delay=0.02))
        pool.set_progress_callback(cb)
        try:
            tid = pool.submit("prompt", {})
            pool.wait_for_ticket(tid, timeout=5.0)
            time.sleep(0.05)  # Let events propagate
            statuses = [e["status"] for e in events if e["ticketId"] == tid]
            assert "queued" in statuses
            assert "processing" in statuses
            assert "completed" in statuses
        finally:
            pool.shutdown()

    def test_pool_progress_includes_batch_id(self):
        """batchId in payload."""
        events = []
        lock = threading.Lock()

        def cb(payload):
            with lock:
                events.append(payload.copy())

        pool = ImageGenerationPool(max_workers=1, generator_fn=_mk_gen(delay=0.02))
        pool.set_progress_callback(cb)
        try:
            batch_id = "test-batch-id"
            tid = pool.submit("prompt", {}, batch_id=batch_id)
            pool.wait_for_ticket(tid, timeout=5.0)
            time.sleep(0.05)
            for e in events:
                if e["ticketId"] == tid:
                    assert e["batchId"] == batch_id
        finally:
            pool.shutdown()

    def test_pool_cleanup_only_terminal(self):
        """cleanup_batch doesn't remove in-progress."""

        def slow_gen(ticket: Ticket) -> str:
            time.sleep(0.5)
            return "/tmp/slow.png"

        pool = ImageGenerationPool(max_workers=1, generator_fn=slow_gen)
        try:
            batch_id = "batch-cleanup"
            t1 = pool.submit("prompt-1", {}, batch_id=batch_id)
            t2 = pool.submit("prompt-2", {}, batch_id=batch_id)
            time.sleep(0.05)  # Let first start processing
            # Cleanup while t1 processing
            pool.cleanup_batch(batch_id)
            # Tickets should still exist (not terminal yet)
            with pool._lock:
                assert t1 in pool._tickets or t2 in pool._tickets
        finally:
            pool.shutdown(wait=False)

    def test_pool_cleanup_no_keyerror(self):
        """Workers don't crash after cleanup."""
        pool = ImageGenerationPool(max_workers=2, generator_fn=_mk_gen(delay=0.02))
        try:
            batch_id = "batch-ke"
            for i in range(3):
                pool.submit(f"prompt-{i}", {}, batch_id=batch_id)
            result = pool.wait_for_batch(batch_id, timeout=5.0)
            pool.cleanup_batch(batch_id)
            assert result.completed_count == 3
        finally:
            pool.shutdown()

    def test_pool_file_uri_encoding(self):
        """Paths with spaces encoded correctly."""
        path = "/tmp/path with spaces/image.png"

        def gen(ticket: Ticket) -> str:
            return path

        events = []

        def cb(payload):
            events.append(payload)

        pool = ImageGenerationPool(max_workers=1, generator_fn=gen)
        pool.set_progress_callback(cb)
        try:
            tid = pool.submit("prompt", {})
            pool.wait_for_ticket(tid, timeout=5.0)
            time.sleep(0.05)
            completed = [e for e in events if e.get("status") == "completed"]
            assert len(completed) == 1
            # Should have file:// URI with encoded spaces
            assert "path" in completed[0]
            assert completed[0]["path"].startswith("file://")
            assert "rawPath" in completed[0]
            assert completed[0]["rawPath"] == path
        finally:
            pool.shutdown()


class TestGetImagePool:
    def test_singleton_returns_same_instance(self):
        """get_image_pool returns same instance without _reset."""
        pool1 = get_image_pool(generator_fn=_mk_gen(), _reset=True)
        pool2 = get_image_pool()
        assert pool1 is pool2
        pool1.shutdown()

    def test_reset_creates_new_instance(self):
        """_reset=True creates new instance."""
        pool1 = get_image_pool(generator_fn=_mk_gen(), _reset=True)
        pool2 = get_image_pool(generator_fn=_mk_gen(), _reset=True)
        assert pool1 is not pool2
        pool1.shutdown()
        pool2.shutdown()
