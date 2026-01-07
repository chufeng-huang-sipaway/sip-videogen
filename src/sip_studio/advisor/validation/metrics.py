"""Generation metrics collection for validation tracking.
Phase 0: Includes metrics logging and debug artifact retention.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from sip_studio.config.logging import get_logger
from sip_studio.config.settings import get_settings

logger = get_logger(__name__)


@dataclass
class ProductMetric:
    """Metrics for a single product in a generation."""

    product_name: str
    similarity_score: float
    is_present: bool
    is_accurate: bool
    proportions_match: bool = True  # Phase 3
    issues: str = ""
    failure_reason: str = ""  # "identity", "proportion", "missing", or ""


@dataclass
class GenerationMetrics:
    """Comprehensive metrics for a single generation request."""

    # Request metadata
    request_id: str
    timestamp: str
    prompt_hash: str
    original_prompt: str
    aspect_ratio: str
    # Product context
    product_slugs: list[str]
    product_names: list[str]
    # Attempt tracking
    total_attempts: int
    successful_attempt: int | None  # None if all failed
    # Per-attempt details
    attempts: list[dict] = field(default_factory=list)
    # Final outcome
    final_score: float = 0.0
    passed: bool = False
    failure_category: str = ""  # "identity", "proportion", "missing", "error"
    best_attempt_reason: str = ""

    def add_attempt(
        self,
        attempt_number: int,
        prompt_used: str,
        overall_score: float,
        passed: bool,
        product_metrics: list[ProductMetric],
        improvement_suggestions: str = "",
    ) -> None:
        """Record a single attempt's metrics."""
        self.attempts.append(
            {
                "attempt_number": attempt_number,
                "prompt_hash": hashlib.sha256(prompt_used.encode()).hexdigest()[:12],
                "overall_score": overall_score,
                "passed": passed,
                "product_metrics": [asdict(pm) for pm in product_metrics],
                "improvement_suggestions": improvement_suggestions,
            }
        )


def _generate_request_id() -> str:
    """Generate a unique request ID."""
    import uuid

    return f"gen_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _get_metrics_dir(output_dir: Path) -> Path:
    """Get the metrics directory, creating if needed."""
    m = output_dir / "_metrics"
    m.mkdir(parents=True, exist_ok=True)
    return m


def _write_metrics(metrics: GenerationMetrics, output_dir: Path) -> None:
    """Write metrics to JSONL file if enabled."""
    s = get_settings()
    if not s.sip_generation_metrics_enabled:
        return
    d = _get_metrics_dir(output_dir)
    f = d / f"generation_metrics_{datetime.utcnow().strftime('%Y%m')}.jsonl"
    try:
        with open(f, "a") as fp:
            fp.write(json.dumps(asdict(metrics)) + "\n")
        logger.debug(f"Wrote generation metrics to {f}")
    except Exception as e:
        logger.warning(f"Failed to write metrics: {e}")


def _cleanup_attempt_files(
    attempts: list, best_attempt_path: Path | None, final_path: Path, output_dir: Path
) -> None:
    """Clean up attempt files based on debug mode setting."""
    s = get_settings()
    for a in attempts:
        p = Path(a.image_path) if hasattr(a, "image_path") else None
        if p is None:
            continue
        if p.exists() and p != final_path:
            if s.sip_generation_debug_mode:
                dn = p.stem + "_debug" + p.suffix
                dp = output_dir / dn
                try:
                    p.rename(dp)
                    logger.debug(f"Kept debug artifact: {dp}")
                except Exception:
                    pass
            else:
                try:
                    p.unlink()
                except Exception:
                    pass
