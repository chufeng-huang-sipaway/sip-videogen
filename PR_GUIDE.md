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

#### Task 1.2.2: `update_brand_identity_section(section: str, data: dict)` ✅
**Commit**: `ecd4b1d`

**Implementation**:
- Added `update_brand_identity_section()` method to `src/sip_videogen/studio/bridge.py`
- Supports sections: `core`, `visual`, `voice`, `audience`, `positioning`, `constraints_avoid`
- **Pydantic validation**: Validates section data before saving to prevent corrupt identity files
  - Uses `BrandCoreIdentity.model_validate()`, `VisualIdentity.model_validate()`, etc.
  - Special handling for `constraints_avoid` which maps to two separate lists
- Uses `save_brand()` to persist changes and sync brand index (name/category updates reflected)
- **Auto-refreshes advisor context** after successful update (preserves chat history)
- Returns full identity with `model_dump(mode="json")` for datetime serialization
- Added imports: `BrandCoreIdentity`, `VisualIdentity`, `VoiceGuidelines`, `AudienceProfile`, `CompetitivePositioning`, `save_brand`

**Testing**:
- Method signature verified
- Bridge imports and instantiates successfully
- Linter passes (`ruff check` - no new errors from this change)
- Existing brand tests pass (6 pre-existing failures unrelated to this change)

#### Task 1.2.3: `regenerate_brand_identity(confirm: bool)` ✅
**Commit**: `4a659e3`

**Implementation**:
- Added `regenerate_brand_identity()` method to `src/sip_videogen/studio/bridge.py`
- **Safety check**: Requires `confirm=True` to proceed (prevents accidental regeneration)
- **Backup before regenerate**: Creates backup via `backup_brand_identity()` before any changes
- **Reads docs/ folder**: Iterates brand's docs/ directory for source materials
- **4800 char truncation limit**: Truncates concept if exceeds limit (same as create_brand_from_materials)
- **Preserves slug**: Forces original slug on regenerated identity (never changes during regeneration)
- **Error handling**:
  - Returns error if no brand selected
  - Returns error if brand not found
  - Returns error if no documents in docs/ folder
  - Returns error if backup fails
- **AI regeneration**: Uses `develop_brand_with_output()` with `existing_brand_slug` parameter
- **Auto-refresh advisor context**: Calls `self._advisor.set_brand(slug, preserve_history=True)` after success
- Uses `model_dump(mode="json")` for JSON-safe datetime serialization
- Added import: `backup_brand_identity` from storage module

**Testing**:
- Method signature verified: `(confirm: bool) -> dict`
- Bridge imports and instantiates successfully
- Linter passes (no new errors from this change)
- Existing brand tests pass (6 pre-existing failures unrelated to this change)

#### Task 1.2.4: `list_identity_backups()` ✅
**Commit**: `af5732b`

**Implementation**:
- Added `list_identity_backups()` method to `src/sip_videogen/studio/bridge.py`
- Returns all identity backups for the active brand from `history/` folder
- Response format: `{ backups: [{ filename, timestamp, size_bytes }] }`
- Sorted by timestamp descending (most recent first)
- Returns empty list if no backups exist
- Returns error if no brand selected
- Uses `list_brand_backups()` storage function internally

**Testing**:
- Method signature verified
- Bridge imports and instantiates successfully
- `list_identity_backups` method exists on bridge instance
- No new linter errors from this change

#### Task 1.2.5: `restore_identity_backup(filename: str)` ✅
**Commit**: `acac592`

**Implementation**:
- Added `restore_identity_backup()` method to `src/sip_videogen/studio/bridge.py`
- Restores brand identity from a backup file in the `history/` folder
- **Security validations** (before passing to storage):
  - Validates filename contains no path separators (`/`, `\`)
  - Validates filename ends with `.json`
- Uses `restore_brand_backup()` storage function for backup loading and additional validation
- **Enforces slug stability**: Forces restored identity slug to current brand slug
- **Saves restored identity**: Uses `save_brand()` to persist and sync index
- **Auto-refresh advisor context**: Calls `self._advisor.set_brand(slug, preserve_history=True)` after success
- Uses `model_dump(mode="json")` for JSON-safe datetime serialization
- Added import: `restore_brand_backup` from storage module

**Testing**:
- Method signature verified: `(filename: str) -> dict`
- Bridge imports and instantiates successfully
- `restore_identity_backup` method exists on bridge instance
- No new linter errors from this change

---

### Stage 1.3: AI Context Sync

#### Task 1.3.1: Verify `model_dump(mode="json")` and AI context refresh ✅
**Commit**: (verification only - no code changes needed)

**Verification**:
All bridge methods returning identity data have been verified to use `model_dump(mode="json")` for JSON-safe datetime serialization:

1. **`get_brand_identity()`** (line 365): ✅ `identity.model_dump(mode="json")`
2. **`update_brand_identity_section()`** (line 458): ✅ `identity.model_dump(mode="json")`
3. **`regenerate_brand_identity()`** (line 582): ✅ `new_identity.model_dump(mode="json")`
4. **`restore_identity_backup()`** (line 683): ✅ `restored_identity.model_dump(mode="json")`

**AI Context Auto-Refresh**:
All modifying methods automatically refresh the advisor context after successful updates:

1. **`update_brand_identity_section()`** (lines 452-453): ✅ `self._advisor.set_brand(slug, preserve_history=True)`
2. **`regenerate_brand_identity()`** (lines 576-577): ✅ `self._advisor.set_brand(slug, preserve_history=True)`
3. **`restore_identity_backup()`** (lines 677-678): ✅ `self._advisor.set_brand(slug, preserve_history=True)`

**Result**: Stage 1 (Backend) is now **COMPLETE**. All storage helpers and bridge methods are implemented with proper datetime serialization and AI context synchronization.

---

### Stage 2.1: TypeScript Types

#### Task 2.1.1: Create TypeScript types file ✅
**Commit**: `7e6199c`

**Implementation**:
- Created `src/sip_videogen/studio/frontend/src/types/brand-identity.ts`
- All types use **snake_case** to match Python models exactly (no mapping layer)
- Defined interfaces matching Python Pydantic models:
  - `ColorDefinition` - hex, name, usage
  - `TypographyRule` - role, family, weight, style_notes
  - `BrandCoreIdentity` - name, tagline, mission, brand_story, values
  - `VisualIdentity` - colors, typography, imagery, logo, aesthetic
  - `VoiceGuidelines` - personality, tone, messages, examples
  - `AudienceProfile` - demographics, interests, pain_points, desires
  - `CompetitivePositioning` - market, competitors, differentiation
  - `BrandIdentityFull` - full L1 model with all sections
  - `IdentitySection` - union type for section names
  - `ConstraintsAvoidData` - constraints[] + avoid[]
  - `BackupEntry` - filename, timestamp, size_bytes

**Testing**:
- Frontend builds successfully (`npm run build`)
- No TypeScript errors
- Types properly exported for use in bridge.ts and components

---

## Next Tasks

### Stage 2.2: Bridge Functions
- [ ] Task 2.2.1: Extend `PyWebViewAPI` interface and add bridge functions in `bridge.ts`

---

## Files Modified
- `src/sip_videogen/brands/storage.py` - Added backup, list_backups, and restore_backup functions
- `src/sip_videogen/studio/bridge.py` - Added get_brand_identity, update_brand_identity_section, regenerate_brand_identity, list_identity_backups, and restore_identity_backup bridge methods
- `src/sip_videogen/studio/frontend/src/types/brand-identity.ts` - NEW: TypeScript types for brand identity
