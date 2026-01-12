"""Visual Directive and Feedback Log storage operations."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from sip_studio.utils.file_utils import write_atomically

from ..models import FeedbackInstance, FeedbackLog, VisualDirective
from .base import get_brand_dir

logger = logging.getLogger(__name__)


# Visual Directive storage
def get_visual_directive_path(brand_slug: str) -> Path:
    """Get path to visual directive file."""
    return get_brand_dir(brand_slug) / "visual_directive.json"


def load_visual_directive(brand_slug: str) -> VisualDirective | None:
    """Load visual directive for a brand.
    Returns None if not found or brand doesn't exist."""
    p = get_visual_directive_path(brand_slug)
    if not p.exists():
        logger.info("[VisualDirective] File not found: %s", p)
        return None
    try:
        data = json.loads(p.read_text())
        directive = VisualDirective.model_validate(data)
        learned_count = len(directive.learned_rules)
        logger.info(
            "[VisualDirective] Loaded v%d for '%s' with %d learned rules",
            directive.version,
            brand_slug,
            learned_count,
        )
        return directive
    except Exception as e:
        logger.error("[VisualDirective] Failed to load for %s: %s", brand_slug, e)
        return None


def save_visual_directive(brand_slug: str, directive: VisualDirective) -> None:
    """Save visual directive for a brand."""
    bd = get_brand_dir(brand_slug)
    if not bd.exists():
        logger.error("[VisualDirective] Brand directory does not exist: %s", brand_slug)
        raise FileNotFoundError(f"Brand '{brand_slug}' does not exist")
    directive.updated_at = datetime.utcnow()
    p = get_visual_directive_path(brand_slug)
    write_atomically(p, directive.model_dump_json(indent=2))
    logger.info(
        "[VisualDirective] Saved v%d for '%s' (%d learned rules)",
        directive.version,
        brand_slug,
        len(directive.learned_rules),
    )


def delete_visual_directive(brand_slug: str) -> bool:
    """Delete visual directive for a brand. Returns True if deleted."""
    p = get_visual_directive_path(brand_slug)
    if not p.exists():
        return False
    p.unlink()
    logger.info("Deleted visual directive for brand: %s", brand_slug)
    return True


def visual_directive_exists(brand_slug: str) -> bool:
    """Check if a visual directive exists for a brand."""
    return get_visual_directive_path(brand_slug).exists()


# Feedback Log storage
def get_feedback_log_path(brand_slug: str) -> Path:
    """Get path to feedback log file."""
    return get_brand_dir(brand_slug) / "feedback_log.json"


def load_feedback_log(brand_slug: str) -> FeedbackLog:
    """Load feedback log for a brand.
    Returns empty log if not found."""
    p = get_feedback_log_path(brand_slug)
    if not p.exists():
        return FeedbackLog(brand_slug=brand_slug)
    try:
        data = json.loads(p.read_text())
        return FeedbackLog.model_validate(data)
    except Exception as e:
        logger.error("Failed to load feedback log for %s: %s", brand_slug, e)
        return FeedbackLog(brand_slug=brand_slug)


def save_feedback_log(brand_slug: str, log: FeedbackLog) -> None:
    """Save feedback log for a brand."""
    bd = get_brand_dir(brand_slug)
    if not bd.exists():
        logger.error("Brand directory does not exist: %s", brand_slug)
        raise FileNotFoundError(f"Brand '{brand_slug}' does not exist")
    p = get_feedback_log_path(brand_slug)
    write_atomically(p, log.model_dump_json(indent=2))
    logger.debug("Saved feedback log for brand: %s (%d instances)", brand_slug, len(log.instances))


def add_feedback(
    brand_slug: str,
    user_message: str,
    original_prompt: str = "",
    project_slug: str | None = None,
    attached_products: list[str] | None = None,
    attached_style: str | None = None,
    session_id: str = "",
) -> FeedbackInstance:
    """Add a feedback instance to the log.
    This is a convenience function that loads, appends, and saves."""
    log = load_feedback_log(brand_slug)
    feedback = FeedbackInstance(
        id=str(uuid.uuid4()),
        brand_slug=brand_slug,
        project_slug=project_slug,
        user_message=user_message,
        original_prompt=original_prompt,
        attached_products=attached_products or [],
        attached_style=attached_style,
        session_id=session_id,
    )
    log.add_feedback(feedback)
    save_feedback_log(brand_slug, log)
    logger.debug("Added feedback for brand %s: %s", brand_slug, user_message[:50])
    return feedback


def get_unprocessed_feedback_count(brand_slug: str) -> int:
    """Get count of unprocessed feedback instances."""
    log = load_feedback_log(brand_slug)
    return len(log.get_unprocessed())
