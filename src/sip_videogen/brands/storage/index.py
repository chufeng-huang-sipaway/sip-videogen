"""Brand index management."""

from __future__ import annotations

import json
import logging

from sip_videogen.utils.file_utils import write_atomically

from ..models import BrandIndex
from .base import get_index_path

logger = logging.getLogger(__name__)


def load_index() -> BrandIndex:
    """Load the brand index from disk."""
    ip = get_index_path()
    if ip.exists():
        try:
            data = json.loads(ip.read_text())
            idx = BrandIndex.model_validate(data)
            logger.debug("Loaded brand index with %d brands", len(idx.brands))
            return idx
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON in brand index: %s", e)
        except Exception as e:
            logger.warning("Failed to load brand index: %s", e)
    logger.debug("Creating new brand index")
    return BrandIndex()


def save_index(index: BrandIndex) -> None:
    """Save the brand index to disk atomically."""
    ip = get_index_path()
    write_atomically(ip, index.model_dump_json(indent=2))
    logger.debug("Saved brand index with %d brands", len(index.brands))
