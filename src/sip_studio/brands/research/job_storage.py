"""Job storage for brand creation background jobs.
Handles persistence in ~/.sip-studio/jobs/ with filelock for cross-process safety.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from filelock import FileLock

from sip_studio.utils.file_utils import write_atomically

from .models import BrandCreationJob

logger = logging.getLogger(__name__)
TOMBSTONE_TTL = timedelta(hours=1)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_jobs_dir() -> Path:
    return Path.home() / ".sip-studio" / "jobs"


def get_job_path() -> Path:
    return get_jobs_dir() / "job.json"


def get_lock_path() -> Path:
    return get_jobs_dir() / "job.lock"


def _ensure_jobs_dir() -> None:
    get_jobs_dir().mkdir(parents=True, exist_ok=True)


def _load_job_unlocked() -> BrandCreationJob | None:
    """Load job from disk without lock (caller must hold lock)."""
    jp = get_job_path()
    if not jp.exists():
        return None
    try:
        data = json.loads(jp.read_text())
        return BrandCreationJob.from_json_dict(data)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Invalid job file, removing: %s", e)
        jp.unlink(missing_ok=True)
        return None


def _save_job_unlocked(job: BrandCreationJob) -> None:
    """Save job to disk without lock (caller must hold lock)."""
    _ensure_jobs_dir()
    job.updated_at = _utcnow()
    write_atomically(get_job_path(), json.dumps(job.to_json_dict(), indent=2))
    logger.debug("Saved job %s status=%s phase=%s", job.job_id, job.status, job.phase)


def _delete_job_unlocked() -> None:
    """Delete job file without lock (caller must hold lock)."""
    jp = get_job_path()
    jp.unlink(missing_ok=True)
    logger.debug("Deleted job file")


def load_job() -> BrandCreationJob | None:
    """Load current job with file lock."""
    _ensure_jobs_dir()
    with FileLock(get_lock_path()):
        return _load_job_unlocked()


def save_job(job: BrandCreationJob) -> None:
    """Save job with file lock."""
    _ensure_jobs_dir()
    with FileLock(get_lock_path()):
        _save_job_unlocked(job)


def create_job(
    brand_name: str, website_url: str, slug: str, job_id: str
) -> BrandCreationJob | None:
    """Create new job if none exists. Returns None if job already running."""
    _ensure_jobs_dir()
    with FileLock(get_lock_path()):
        existing = _load_job_unlocked()
        if existing and existing.status in ("pending", "running"):
            logger.warning("Job already running: %s", existing.job_id)
            return None
        # Remove old completed/failed job
        if existing:
            _delete_job_unlocked()
        now = _utcnow()
        job = BrandCreationJob(
            job_id=job_id,
            brand_name=brand_name,
            website_url=website_url,
            slug=slug,
            status="pending",
            phase="starting",
            created_at=now,
            updated_at=now,
        )
        _save_job_unlocked(job)
        logger.info("Created job %s for brand %s", job_id, brand_name)
        return job


def update_job_progress(
    job_id: str,
    status: str | None = None,
    phase: str | None = None,
    phase_detail: str | None = None,
    percent_complete: int | None = None,
) -> bool:
    """Update job progress. Returns False if job not found or wrong job_id."""
    _ensure_jobs_dir()
    with FileLock(get_lock_path()):
        job = _load_job_unlocked()
        if not job or job.job_id != job_id:
            return False
        if status:
            job.status = status  # type: ignore[assignment]
        if phase:
            job.phase = phase  # type: ignore[assignment]
        if phase_detail is not None:
            job.phase_detail = phase_detail
        if percent_complete is not None:
            job.percent_complete = percent_complete
        _save_job_unlocked(job)
        return True


def complete_job(job_id: str) -> bool:
    """Mark job as completed with tombstone timestamp."""
    _ensure_jobs_dir()
    with FileLock(get_lock_path()):
        job = _load_job_unlocked()
        if not job or job.job_id != job_id:
            return False
        job.status = "completed"
        job.phase = "complete"
        job.percent_complete = 100
        job.completed_at = _utcnow()
        _save_job_unlocked(job)
        logger.info("Completed job %s", job_id)
        return True


def fail_job(job_id: str, error: str, error_code: str | None = None) -> bool:
    """Mark job as failed with error message."""
    _ensure_jobs_dir()
    with FileLock(get_lock_path()):
        job = _load_job_unlocked()
        if not job or job.job_id != job_id:
            return False
        job.status = "failed"
        job.phase = "failed"
        job.error = error
        job.error_code = error_code
        _save_job_unlocked(job)
        logger.info("Failed job %s: %s", job_id, error)
        return True


def cancel_job(job_id: str) -> bool:
    """Mark job as cancelled."""
    _ensure_jobs_dir()
    with FileLock(get_lock_path()):
        job = _load_job_unlocked()
        if not job or job.job_id != job_id:
            return False
        if job.status not in ("pending", "running"):
            return False
        job.status = "cancelled"
        job.phase = "failed"
        job.error = "Cancelled by user"
        _save_job_unlocked(job)
        logger.info("Cancelled job %s", job_id)
        return True


def request_cancellation(job_id: str) -> bool:
    """Set cancel_requested flag for cooperative cancellation."""
    _ensure_jobs_dir()
    with FileLock(get_lock_path()):
        job = _load_job_unlocked()
        if not job or job.job_id != job_id:
            return False
        if job.status not in ("pending", "running"):
            return False
        job.cancel_requested = True
        _save_job_unlocked(job)
        logger.info("Requested cancellation for job %s", job_id)
        return True


def is_cancellation_requested(job_id: str) -> bool:
    """Check if cancellation was requested."""
    _ensure_jobs_dir()
    with FileLock(get_lock_path()):
        job = _load_job_unlocked()
        if not job or job.job_id != job_id:
            return False
        return job.cancel_requested


def clear_job() -> bool:
    """Clear failed/cancelled/completed job. Returns False if job is running."""
    _ensure_jobs_dir()
    with FileLock(get_lock_path()):
        job = _load_job_unlocked()
        if not job:
            return True
        if job.status in ("pending", "running"):
            logger.warning("Cannot clear running job %s", job.job_id)
            return False
        _delete_job_unlocked()
        logger.info("Cleared job %s", job.job_id)
        return True


def cleanup_on_startup() -> list[str]:
    """Clean up jobs on app startup. Returns list of slugs to release from reservation.
    - Mark running jobs as failed (app restarted)
    - Delete completed jobs past TTL
    """
    _ensure_jobs_dir()
    released_slugs: list[str] = []
    with FileLock(get_lock_path()):
        job = _load_job_unlocked()
        if not job:
            return released_slugs
        # Mark running/pending as failed
        if job.status in ("pending", "running"):
            logger.warning(
                "Found orphaned job %s (status=%s), marking failed", job.job_id, job.status
            )
            job.status = "failed"
            job.phase = "failed"
            job.error = "App restarted during job execution"
            job.error_code = "APP_RESTART"
            released_slugs.append(job.slug)
            _save_job_unlocked(job)
        # Delete completed jobs past TTL
        elif job.status == "completed" and job.completed_at:
            age = _utcnow() - job.completed_at
            if age > TOMBSTONE_TTL:
                logger.info("Removing tombstoned job %s (age=%s)", job.job_id, age)
                _delete_job_unlocked()
    return released_slugs


def has_active_job() -> bool:
    """Check if there's an active (pending/running) job."""
    _ensure_jobs_dir()
    with FileLock(get_lock_path()):
        job = _load_job_unlocked()
        return job is not None and job.status in ("pending", "running")
