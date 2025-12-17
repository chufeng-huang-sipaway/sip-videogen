# Brand Memory Refactor - Progress Guide

## Overview
This PR implements the Brand Memory feature - a dedicated panel that shows what the AI agent "knows" about the brand, with full edit capability.

**Task List**: See `TASKS.md` for complete task breakdown.

---

## Completed Tasks

### Stage 1.1: Storage Helpers

#### Task 1.1.1: `backup_brand_identity(slug: str) -> str` ✅
**Commit**: `238d603`

**Implementation**:
- Added `backup_brand_identity()` function to `src/sip_videogen/brands/storage.py`
- Creates timestamped backup of `identity_full.json` in brand's `history/` folder
- Returns backup filename (e.g., `identity_full_20240115_143022.json`)
- Raises `ValueError` if brand doesn't exist or identity file not found

**Testing**:
- Function signature verified
- Error handling tested (non-existent brand raises ValueError)
- All existing tests pass (1 pre-existing failure unrelated to this change)

#### Task 1.1.2: `list_brand_backups(slug: str) -> list[dict]` ✅
**Commit**: `441a198`

**Implementation**:
- Added `list_brand_backups()` function to `src/sip_videogen/brands/storage.py`
- Lists all identity backups in brand's `history/` folder
- Returns list of `{filename, timestamp, size_bytes}` dicts
- Timestamp extracted from filename and formatted as ISO string
- Sorted by timestamp descending (most recent first)
- Returns empty list if no history directory exists
- Raises `ValueError` for non-existent brands

**Testing**:
- Function signature verified
- Error handling tested (non-existent brand raises ValueError)
- Linter passes (`ruff check`)
- All existing brand tests pass

#### Task 1.1.3: `restore_brand_backup(slug: str, filename: str) -> BrandIdentityFull` ✅
**Commit**: `a349b87`

**Implementation**:
- Added `restore_brand_backup()` function to `src/sip_videogen/brands/storage.py`
- Loads a backup from brand's `history/` folder and returns parsed `BrandIdentityFull`
- **Security validations** (prevent directory traversal):
  - Validates filename contains no path separators (`/`, `\`)
  - Validates filename ends with `.json`
  - Validates filename starts with `identity_full_`
  - Extra check: verifies resolved path is within `history/` dir
- Enforces slug stability: forces current brand slug on restored identity
- Raises `ValueError` for non-existent brand, invalid filename, or backup not found

**Testing**:
- Function signature verified (`(slug: str, filename: str) -> BrandIdentityFull`)
- All security validations tested:
  - Path traversal with `/` → blocked
  - Path traversal with `\` → blocked
  - Wrong extension → blocked
  - Wrong prefix → blocked
  - Non-existent backup → proper error
- Linter passes (`ruff check`)
- All existing brand tests pass

---

### Stage 1.2: Bridge Methods

#### Task 1.2.1: `get_brand_identity()` ✅
**Commit**: `d5e5793`

**Implementation**:
- Added `get_brand_identity()` method to `src/sip_videogen/studio/bridge.py`
- Returns full brand identity (L1 data) for the active brand
- Uses `load_brand()` from storage module to fetch `BrandIdentityFull`
- Serializes response using `model_dump(mode="json")` for proper datetime handling
- Returns error if no brand selected or brand not found

**Testing**:
- Method signature verified
- Import verified (`load_brand` properly imported from storage)
- Bridge instantiation verified
- Linter passes (`ruff check` - no new errors)

---

## Next Tasks

### Stage 1.2: Bridge Methods (continued)
- [ ] Task 1.2.2: `update_brand_identity_section(section: str, data: dict)`
- [ ] Task 1.2.3: `regenerate_brand_identity(confirm: bool)`
- [ ] Task 1.2.4: `list_identity_backups()`
- [ ] Task 1.2.5: `restore_identity_backup(filename: str)`

---

## Files Modified
- `src/sip_videogen/brands/storage.py` - Added backup, list_backups, and restore_backup functions
- `src/sip_videogen/studio/bridge.py` - Added get_brand_identity bridge method
