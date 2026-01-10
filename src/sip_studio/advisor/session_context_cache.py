"""Session context cache with persistence and version-based invalidation.
Per IMPLEMENTATION_PLAN.md Stage 3 - Lean Context Loading.
Provides caching for expensive context lookups (brand summaries, product details)
with TTL and source version invalidation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
from typing import Any

from sip_studio.advisor.session_manager import atomic_write, get_session_dir, safe_read
from sip_studio.config.logging import get_logger

logger = get_logger(__name__)
__all__ = ["SessionContextCache", "CacheEntryData", "register_cache", "invalidate_caches_for_brand"]
SCHEMA_VERSION = 1


@dataclass
class CacheEntryData:
    """A single cache entry with expiration and version tracking."""

    value: str
    expires_at: str  # ISO UTC with Z suffix
    source_version: str  # = SessionMeta.updated_at or Product.updated_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "expires_at": self.expires_at,
            "source_version": self.source_version,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CacheEntryData":
        return cls(value=d["value"], expires_at=d["expires_at"], source_version=d["source_version"])


class SessionContextCache:
    """Persisted cache with version-based invalidation.
    Caches expensive context lookups (brand summaries, product details)
    to reduce redundant I/O and API calls across chat turns.
    Usage:
        cache = SessionContextCache("brand-slug", "session-id")
        val = cache.get("product:coffee-mug", current_version="2024-01-01T00:00:00Z")
        if val is None:
            val = expensive_lookup()
            cache.set("product:coffee-mug", val, source_version="2024-01-01T00:00:00Z")
    """

    def __init__(self, brand_slug: str, session_id: str):
        self.brand_slug = brand_slug
        self.session_id = session_id
        self._cache_path = get_session_dir(brand_slug, session_id) / "context_cache.json"
        self._cache: dict[str, CacheEntryData] = {}
        self._load()
        register_cache(self)

    def _load(self) -> None:
        """Load cache from disk."""
        data = safe_read(self._cache_path)
        if data and data.get("schema_version") == SCHEMA_VERSION:
            entries = data.get("entries", {})
            self._cache = {}
            for k, v in entries.items():
                try:
                    self._cache[k] = CacheEntryData.from_dict(v)
                except (TypeError, KeyError):
                    pass  # Skip invalid entries

    def _save(self) -> None:
        """Save cache to disk."""
        data = {
            "schema_version": SCHEMA_VERSION,
            "entries": {k: v.to_dict() for k, v in self._cache.items()},
        }
        atomic_write(self._cache_path, data)

    def get(self, key: str, current_version: str | None = None) -> str | None:
        """Get cached value if valid.
        Args:
            key: Cache key (e.g., "product:coffee-mug")
            current_version: Current source version for validation
        Returns:
            Cached value or None if invalid/missing
        """
        entry = self._cache.get(key)
        if not entry:
            return None
        # Version invalidation (source_version = entity.updated_at)
        if current_version and entry.source_version != current_version:
            del self._cache[key]
            self._save()
            return None
        # TTL invalidation
        try:
            expires = datetime.fromisoformat(entry.expires_at.replace("Z", "+00:00"))
            if expires < datetime.now(timezone.utc):
                del self._cache[key]
                self._save()
                return None
        except ValueError:
            del self._cache[key]
            self._save()
            return None
        return entry.value

    def set(self, key: str, value: str, source_version: str, ttl_minutes: int = 30) -> None:
        """Set cached value with TTL and version.
        Args:
            key: Cache key
            value: Value to cache
            source_version: Source version (e.g., entity.updated_at)
            ttl_minutes: Time-to-live in minutes (default 30)
        """
        expires = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        self._cache[key] = CacheEntryData(
            value=value,
            expires_at=expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
            source_version=source_version,
        )
        self._save()

    def invalidate(self, pattern: str) -> None:
        """Invalidate cache entries matching pattern.
        Args:
            pattern: Glob pattern (e.g., "product:*" or "*")
        """
        keys_to_remove = [k for k in self._cache if fnmatch(k, pattern)]
        for key in keys_to_remove:
            del self._cache[key]
        if keys_to_remove:
            self._save()
            logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for pattern '{pattern}'")

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache = {}
        self._save()

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return {"entry_count": len(self._cache)}


# region Global Cache Registry
_active_caches: dict[str, SessionContextCache] = {}


def register_cache(cache: SessionContextCache) -> None:
    """Register a cache for global invalidation."""
    key = f"{cache.brand_slug}:{cache.session_id}"
    _active_caches[key] = cache


def unregister_cache(cache: SessionContextCache) -> None:
    """Unregister a cache."""
    key = f"{cache.brand_slug}:{cache.session_id}"
    _active_caches.pop(key, None)


def invalidate_caches_for_brand(brand_slug: str, pattern: str) -> None:
    """Invalidate cache entries across all active sessions for a brand.
    Args:
        brand_slug: Brand identifier
        pattern: Glob pattern to match keys (e.g., "product:*")
    """
    for key, cache in _active_caches.items():
        if key.startswith(f"{brand_slug}:"):
            cache.invalidate(pattern)


# endregion
