"""Migrations for advisor module."""

from sip_studio.advisor.migrations.migrate_legacy_history import (
    MigrationResult,
    migrate_all_brands,
    migrate_legacy_history,
)

__all__ = ["MigrationResult", "migrate_legacy_history", "migrate_all_brands"]
