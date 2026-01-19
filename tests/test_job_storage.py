"""Tests for job storage persistence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from sip_studio.brands.research import job_storage
from sip_studio.brands.research.models import BrandCreationJob


@pytest.fixture
def mock_jobs_dir(tmp_path):
    """Mock jobs directory to use temp path."""
    jobs_dir = tmp_path / "jobs"
    with patch.object(job_storage, "get_jobs_dir", return_value=jobs_dir):
        yield jobs_dir


class TestJobStorage:
    def test_create_job_success(self, mock_jobs_dir):
        job = job_storage.create_job(
            brand_name="Test", website_url="https://test.com", slug="test", job_id="job-1"
        )
        assert job is not None
        assert job.job_id == "job-1"
        assert job.status == "pending"
        assert job.phase == "starting"
        # Verify file created
        assert (mock_jobs_dir / "job.json").exists()

    def test_create_job_rejects_concurrent(self, mock_jobs_dir):
        j1 = job_storage.create_job(
            brand_name="T1", website_url="https://t1.com", slug="t1", job_id="j1"
        )
        assert j1 is not None
        # Second job should fail while first is running
        j2 = job_storage.create_job(
            brand_name="T2", website_url="https://t2.com", slug="t2", job_id="j2"
        )
        assert j2 is None
        # Verify first job still exists
        loaded = job_storage.load_job()
        assert loaded is not None
        assert loaded.job_id == "j1"

    def test_create_job_replaces_completed(self, mock_jobs_dir):
        j1 = job_storage.create_job(
            brand_name="T1", website_url="https://t1.com", slug="t1", job_id="j1"
        )
        assert j1 is not None
        job_storage.complete_job("j1")
        # New job should succeed
        j2 = job_storage.create_job(
            brand_name="T2", website_url="https://t2.com", slug="t2", job_id="j2"
        )
        assert j2 is not None
        assert j2.job_id == "j2"

    def test_create_job_replaces_failed(self, mock_jobs_dir):
        j1 = job_storage.create_job(
            brand_name="T1", website_url="https://t1.com", slug="t1", job_id="j1"
        )
        assert j1 is not None
        job_storage.fail_job("j1", "Some error")
        # New job should succeed
        j2 = job_storage.create_job(
            brand_name="T2", website_url="https://t2.com", slug="t2", job_id="j2"
        )
        assert j2 is not None
        assert j2.job_id == "j2"

    def test_load_job_returns_none_when_empty(self, mock_jobs_dir):
        job = job_storage.load_job()
        assert job is None

    def test_save_and_load_job(self, mock_jobs_dir):
        original = BrandCreationJob(
            job_id="j1",
            brand_name="Test",
            website_url="https://test.com",
            slug="test",
            status="running",
            phase="researching",
            percent_complete=50,
        )
        job_storage.save_job(original)
        loaded = job_storage.load_job()
        assert loaded is not None
        assert loaded.job_id == "j1"
        assert loaded.status == "running"
        assert loaded.phase == "researching"
        assert loaded.percent_complete == 50

    def test_update_job_progress(self, mock_jobs_dir):
        job_storage.create_job("T", "https://t.com", "t", "j1")
        ok = job_storage.update_job_progress(
            "j1", status="running", phase="researching", percent_complete=30
        )
        assert ok
        loaded = job_storage.load_job()
        assert loaded is not None
        assert loaded.status == "running"
        assert loaded.phase == "researching"
        assert loaded.percent_complete == 30

    def test_update_job_wrong_id(self, mock_jobs_dir):
        job_storage.create_job("T", "https://t.com", "t", "j1")
        ok = job_storage.update_job_progress("wrong-id", status="running")
        assert not ok

    def test_update_job_no_job(self, mock_jobs_dir):
        ok = job_storage.update_job_progress("j1", status="running")
        assert not ok

    def test_complete_job(self, mock_jobs_dir):
        job_storage.create_job("T", "https://t.com", "t", "j1")
        ok = job_storage.complete_job("j1")
        assert ok
        loaded = job_storage.load_job()
        assert loaded is not None
        assert loaded.status == "completed"
        assert loaded.phase == "complete"
        assert loaded.percent_complete == 100
        assert loaded.completed_at is not None

    def test_fail_job(self, mock_jobs_dir):
        job_storage.create_job("T", "https://t.com", "t", "j1")
        ok = job_storage.fail_job("j1", "Connection failed", "NETWORK_ERROR")
        assert ok
        loaded = job_storage.load_job()
        assert loaded is not None
        assert loaded.status == "failed"
        assert loaded.phase == "failed"
        assert loaded.error == "Connection failed"
        assert loaded.error_code == "NETWORK_ERROR"

    def test_cancel_job(self, mock_jobs_dir):
        job_storage.create_job("T", "https://t.com", "t", "j1")
        ok = job_storage.cancel_job("j1")
        assert ok
        loaded = job_storage.load_job()
        assert loaded is not None
        assert loaded.status == "cancelled"
        assert loaded.phase == "failed"

    def test_cancel_job_already_completed(self, mock_jobs_dir):
        job_storage.create_job("T", "https://t.com", "t", "j1")
        job_storage.complete_job("j1")
        ok = job_storage.cancel_job("j1")
        assert not ok

    def test_request_cancellation(self, mock_jobs_dir):
        job_storage.create_job("T", "https://t.com", "t", "j1")
        ok = job_storage.request_cancellation("j1")
        assert ok
        assert job_storage.is_cancellation_requested("j1")

    def test_request_cancellation_not_running(self, mock_jobs_dir):
        job_storage.create_job("T", "https://t.com", "t", "j1")
        job_storage.complete_job("j1")
        ok = job_storage.request_cancellation("j1")
        assert not ok

    def test_is_cancellation_requested_no_job(self, mock_jobs_dir):
        assert not job_storage.is_cancellation_requested("nonexistent")

    def test_clear_job_failed(self, mock_jobs_dir):
        job_storage.create_job("T", "https://t.com", "t", "j1")
        job_storage.fail_job("j1", "Error")
        ok = job_storage.clear_job()
        assert ok
        assert job_storage.load_job() is None

    def test_clear_job_running_rejected(self, mock_jobs_dir):
        job_storage.create_job("T", "https://t.com", "t", "j1")
        ok = job_storage.clear_job()
        assert not ok
        # Job still exists
        assert job_storage.load_job() is not None

    def test_clear_job_no_job(self, mock_jobs_dir):
        ok = job_storage.clear_job()
        assert ok

    def test_has_active_job(self, mock_jobs_dir):
        assert not job_storage.has_active_job()
        job_storage.create_job("T", "https://t.com", "t", "j1")
        assert job_storage.has_active_job()
        job_storage.complete_job("j1")
        assert not job_storage.has_active_job()


class TestStartupCleanup:
    def test_cleanup_orphaned_running_job(self, mock_jobs_dir):
        job = BrandCreationJob(
            job_id="j1",
            brand_name="T",
            website_url="https://t.com",
            slug="orphan",
            status="running",
            phase="researching",
        )
        job_storage.save_job(job)
        released = job_storage.cleanup_on_startup()
        assert "orphan" in released
        loaded = job_storage.load_job()
        assert loaded is not None
        assert loaded.status == "failed"
        assert loaded.error_code == "APP_RESTART"

    def test_cleanup_orphaned_pending_job(self, mock_jobs_dir):
        job = BrandCreationJob(
            job_id="j1",
            brand_name="T",
            website_url="https://t.com",
            slug="pending-orphan",
            status="pending",
            phase="starting",
        )
        job_storage.save_job(job)
        released = job_storage.cleanup_on_startup()
        assert "pending-orphan" in released
        loaded = job_storage.load_job()
        assert loaded is not None
        assert loaded.status == "failed"

    def test_cleanup_completed_job_within_ttl(self, mock_jobs_dir):
        job = BrandCreationJob(
            job_id="j1",
            brand_name="T",
            website_url="https://t.com",
            slug="t",
            status="completed",
            phase="complete",
            completed_at=datetime.now(timezone.utc),
        )
        job_storage.save_job(job)
        released = job_storage.cleanup_on_startup()
        assert len(released) == 0
        # Job still exists
        assert job_storage.load_job() is not None

    def test_cleanup_completed_job_past_ttl(self, mock_jobs_dir):
        old_time = datetime.now(timezone.utc) - timedelta(hours=2)
        job = BrandCreationJob(
            job_id="j1",
            brand_name="T",
            website_url="https://t.com",
            slug="t",
            status="completed",
            phase="complete",
            completed_at=old_time,
        )
        job_storage.save_job(job)
        released = job_storage.cleanup_on_startup()
        assert len(released) == 0
        # Job deleted
        assert job_storage.load_job() is None

    def test_cleanup_failed_job_persists(self, mock_jobs_dir):
        job = BrandCreationJob(
            job_id="j1",
            brand_name="T",
            website_url="https://t.com",
            slug="t",
            status="failed",
            phase="failed",
            error="Previous error",
        )
        job_storage.save_job(job)
        released = job_storage.cleanup_on_startup()
        assert len(released) == 0
        # Job still exists
        loaded = job_storage.load_job()
        assert loaded is not None
        assert loaded.status == "failed"

    def test_cleanup_no_job(self, mock_jobs_dir):
        released = job_storage.cleanup_on_startup()
        assert len(released) == 0


class TestCorruptedJobFile:
    def test_load_invalid_json(self, mock_jobs_dir):
        mock_jobs_dir.mkdir(parents=True, exist_ok=True)
        (mock_jobs_dir / "job.json").write_text("not valid json{{{")
        job = job_storage.load_job()
        assert job is None
        # File should be removed
        assert not (mock_jobs_dir / "job.json").exists()

    def test_load_invalid_schema(self, mock_jobs_dir):
        mock_jobs_dir.mkdir(parents=True, exist_ok=True)
        (mock_jobs_dir / "job.json").write_text('{"invalid":"schema"}')
        job = job_storage.load_job()
        assert job is None
        # File should be removed
        assert not (mock_jobs_dir / "job.json").exists()
