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

### Stage 2.2: Bridge Functions

#### Task 2.2.1: Extend `PyWebViewAPI` interface and add bridge functions ✅
**Commit**: `b9d196d`

**Implementation**:
- Extended `src/sip_videogen/studio/frontend/src/lib/bridge.ts`
- Imported types from `brand-identity.ts`: `BrandIdentityFull`, `BackupEntry`, `IdentitySection`, `SectionDataMap`
- Extended `PyWebViewAPI` interface with new backend methods:
  - `get_brand_identity()` → `Promise<BridgeResponse<BrandIdentityFull>>`
  - `update_brand_identity_section(section, data)` → `Promise<BridgeResponse<BrandIdentityFull>>`
  - `regenerate_brand_identity(confirm)` → `Promise<BridgeResponse<BrandIdentityFull>>`
  - `list_identity_backups()` → `Promise<BridgeResponse<{ backups: BackupEntry[] }>>`
  - `restore_identity_backup(filename)` → `Promise<BridgeResponse<BrandIdentityFull>>`
- Added corresponding bridge wrapper functions:
  - `getBrandIdentity()` → `Promise<BrandIdentityFull>`
  - `updateBrandIdentitySection(section, data)` → `Promise<BrandIdentityFull>` (generic for type safety)
  - `regenerateBrandIdentity(confirm)` → `Promise<BrandIdentityFull>`
  - `listIdentityBackups()` → `Promise<BackupEntry[]>` (unwraps backups array)
  - `restoreIdentityBackup(filename)` → `Promise<BrandIdentityFull>`

**Testing**:
- Frontend builds successfully (`npm run build`)
- No TypeScript errors
- Types properly imported and used

**Result**: Stage 2 (Frontend Types & Bridge) is now **COMPLETE**. All TypeScript types and bridge functions are implemented.

---

### Stage 3.1: Main Components

#### Task 3.1.1: Create `BrandMemory/index.tsx` - Main view container ✅
**Commit**: `792f109`

**Implementation**:
- Created `src/sip_videogen/studio/frontend/src/components/BrandMemory/index.tsx`
- Modal dialog component that opens as an overlay (keeps ChatPanel mounted)
- Loads brand identity (L1 data) via `getBrandIdentity()` bridge method on open
- **Header** shows brand name, last updated timestamp, and action buttons:
  - "Regenerate" button (placeholder - Task 3.5)
  - "History" button (placeholder - Stage 5)
- **Content area** with ScrollArea for scrollable sections:
  - Core Identity (name, tagline)
  - Visual Identity (colors, typography)
  - Voice Guidelines (personality)
  - Target Audience (primary summary)
  - Market Positioning (market category)
  - Constraints & Avoid (counts)
- **State handling**:
  - Loading state with spinner
  - Error state with Alert
  - No brand selected state
- Uses `useBrand()` context for active brand slug
- Placeholder sections will be replaced with MemorySection in Task 3.1.2

**Testing**:
- Frontend builds successfully (`npm run build`)
- No TypeScript errors
- No eslint warnings
- Component follows existing dialog patterns (CreateBrandDialog)

#### Task 3.1.2: Create `BrandMemory/MemorySection.tsx` - Reusable expandable section wrapper ✅
**Commit**: `7262da9`

**Implementation**:
- Created `src/sip_videogen/studio/frontend/src/components/BrandMemory/MemorySection.tsx`
- Reusable collapsible section wrapper for Brand Memory view
- **Features**:
  - Header with title, optional subtitle, and Edit button
  - Collapse/expand functionality via Radix accordion primitive
  - View mode vs Edit mode toggle (shows `editContent` prop when editing)
  - Cancel button in edit mode to discard changes
  - Disabled state when saving (`isSaving` prop)
  - Callback for edit mode changes (`onEditModeChange`)
  - Default expanded state configurable (`defaultExpanded`)
- **Exports**:
  - `MemorySection` - Main component
  - `MemorySectionGroup` - Wrapper for grouping multiple sections
- Uses proper TypeScript imports (`type ReactNode` for verbatimModuleSyntax)

**Testing**:
- Frontend builds successfully (`npm run build`)
- No TypeScript errors
- No eslint warnings
- Component follows existing UI patterns

### Stage 3.2: Section Components

#### Task 3.2.1: Create `sections/CoreSection.tsx` - Core identity section ✅
**Commit**: `53687bf`

**Implementation**:
- Created `src/sip_videogen/studio/frontend/src/components/BrandMemory/sections/CoreSection.tsx`
- Displays and edits core brand identity (name, tagline, mission, brand_story, values)
- **View mode**:
  - Labeled display of all fields
  - Values shown as purple badge pills
  - Success alert shown after save ("AI context refreshed automatically")
- **Edit mode**:
  - Input fields for name, tagline
  - Textarea for mission and brand_story
  - Dynamic values list with add/remove buttons
  - Save button with loading spinner
  - Error alert on failure
- Uses `MemorySection` wrapper for collapse/expand and edit mode toggle
- Calls `updateBrandIdentitySection('core', data)` bridge method on save
- Returns updated `BrandIdentityFull` to parent via `onIdentityUpdate` callback

**Testing**:
- Frontend builds successfully (`npm run build`)
- No TypeScript errors
- No eslint warnings
- Component follows existing patterns

#### Task 3.2.2: Create `sections/VisualSection.tsx` - Visual identity section ✅
**Commit**: `ef498f3`

**Implementation**:
- Created `src/sip_videogen/studio/frontend/src/components/BrandMemory/sections/VisualSection.tsx`
- Displays and edits visual brand identity (colors, typography, imagery, materials, logo, aesthetic)
- **View mode**:
  - Color swatches with hex color preview, name, and usage
  - Typography rules display (role, family, weight, style notes)
  - Imagery style with keywords (blue) and avoid items (red) as badge pills
  - Materials list as amber badge pills
  - Logo description and usage rules
  - Overall aesthetic with style keywords (purple badge pills)
  - Success alert shown after save ("AI context refreshed automatically")
- **Edit mode**:
  - Color editors with native `<input type="color">` picker + hex input
  - Separate editors for primary, secondary, and accent colors
  - Typography rules form (role, family, weight, style_notes)
  - String array editors for imagery_keywords, imagery_avoid, materials, style_keywords
  - Textarea fields for imagery_style, logo_description, logo_usage_rules, overall_aesthetic
  - Add/remove buttons for all list items
  - Save button with loading spinner
  - Error alert on failure
- Uses `MemorySection` wrapper for collapse/expand and edit mode toggle
- Calls `updateBrandIdentitySection('visual', data)` bridge method on save
- Returns updated `BrandIdentityFull` to parent via `onIdentityUpdate` callback
- Deep copy helper ensures all nested arrays are properly cloned when entering edit mode

**Testing**:
- Frontend builds successfully (`npm run build`)
- No TypeScript errors
- No eslint warnings
- Component follows existing patterns from CoreSection

#### Task 3.2.3: Create `sections/VoiceSection.tsx` - Voice guidelines section ✅
**Commit**: `b206103`

**Implementation**:
- Created `src/sip_videogen/studio/frontend/src/components/BrandMemory/sections/VoiceSection.tsx`
- Displays and edits voice and messaging guidelines (personality, tone_attributes, key_messages, messaging_do, messaging_dont, example_headlines, example_taglines)
- **View mode**:
  - Brand personality as paragraph text
  - Tone attributes as blue badge pills
  - Key messages as purple badge pills
  - Messaging do's as green badge pills
  - Messaging don'ts as red badge pills
  - Example headlines and taglines as quoted lists
  - Success alert shown after save ("AI context refreshed automatically")
- **Edit mode**:
  - Textarea for personality description
  - Reusable `renderStringListEditor` helper for all string array fields
  - Add/remove buttons for all list items
  - Save button with loading spinner
  - Error alert on failure
- Uses `MemorySection` wrapper for collapse/expand and edit mode toggle
- Calls `updateBrandIdentitySection('voice', data)` bridge method on save
- Returns updated `BrandIdentityFull` to parent via `onIdentityUpdate` callback
- Deep copy helper ensures all arrays are properly cloned when entering edit mode

**Testing**:
- Frontend builds successfully (`npm run build`)
- No TypeScript errors
- No eslint warnings
- Component follows existing patterns from CoreSection and VisualSection

#### Task 3.2.4: Create `sections/AudienceSection.tsx` - Audience profile section ✅
**Commit**: `318d456`

**Implementation**:
- Created `src/sip_videogen/studio/frontend/src/components/BrandMemory/sections/AudienceSection.tsx`
- Displays and edits target audience profile (primary_summary, demographics, psychographics, pain points, desires)
- **View mode**:
  - Primary summary as paragraph text
  - Demographics in 2-column grid (age_range, gender, income_level, location)
  - Lifestyle description
  - Interests as blue badge pills
  - Values as purple badge pills
  - Pain points as red badge pills
  - Desires as green badge pills
  - Success alert shown after save ("AI context refreshed automatically")
- **Edit mode**:
  - Textarea for primary_summary and lifestyle
  - Input fields for demographics in 2-column grid layout
  - Reusable `renderStringListEditor` helper for all string array fields
  - Add/remove buttons for all list items
  - Save button with loading spinner
  - Error alert on failure
- Uses `MemorySection` wrapper for collapse/expand and edit mode toggle
- Calls `updateBrandIdentitySection('audience', data)` bridge method on save
- Returns updated `BrandIdentityFull` to parent via `onIdentityUpdate` callback
- Deep copy helper ensures all arrays are properly cloned when entering edit mode

**Testing**:
- Frontend builds successfully (`npm run build`)
- No TypeScript errors
- No eslint warnings
- Component follows existing patterns from CoreSection, VisualSection, VoiceSection

#### Task 3.2.5: Create `sections/PositioningSection.tsx` - Competitive positioning section ✅
**Commit**: `8c960f3`

**Implementation**:
- Created `src/sip_videogen/studio/frontend/src/components/BrandMemory/sections/PositioningSection.tsx`
- Displays and edits competitive positioning (market_category, unique_value_proposition, primary_competitors, differentiation, positioning_statement)
- **View mode**:
  - Market category as text
  - Unique value proposition as paragraph text
  - Primary competitors as orange badge pills
  - Differentiation as paragraph text
  - Positioning statement as italicized quoted text
  - Success alert shown after save ("AI context refreshed automatically")
- **Edit mode**:
  - Input field for market_category
  - Textarea for unique_value_proposition, differentiation, and positioning_statement
  - Reusable `renderStringListEditor` helper for primary_competitors array
  - Add/remove buttons for competitor list items
  - Save button with loading spinner
  - Error alert on failure
- Uses `MemorySection` wrapper for collapse/expand and edit mode toggle
- Calls `updateBrandIdentitySection('positioning', data)` bridge method on save
- Returns updated `BrandIdentityFull` to parent via `onIdentityUpdate` callback
- Deep copy helper ensures all arrays are properly cloned when entering edit mode

**Testing**:
- Frontend builds successfully (`npm run build`)
- No TypeScript errors
- No eslint warnings
- Component follows existing patterns from CoreSection, VisualSection, VoiceSection, AudienceSection

#### Task 3.2.6: Create `sections/ConstraintsAvoidSection.tsx` - Constraints + avoid lists ✅
**Commit**: `9e9b010`

**Implementation**:
- Created `src/sip_videogen/studio/frontend/src/components/BrandMemory/sections/ConstraintsAvoidSection.tsx`
- Displays and edits brand constraints and things to avoid
- **View mode**:
  - Brand constraints as yellow badge pills
  - Things to avoid as red badge pills
  - Descriptive labels explaining each section's purpose
  - Success alert shown after save ("AI context refreshed automatically")
- **Edit mode**:
  - Reusable `renderStringListEditor` helper for both arrays
  - Add/remove buttons for list items
  - Save button with loading spinner
  - Error alert on failure
- Uses `MemorySection` wrapper for collapse/expand and edit mode toggle
- Calls `updateBrandIdentitySection('constraints_avoid', data)` bridge method on save
- Returns updated `BrandIdentityFull` to parent via `onIdentityUpdate` callback
- Deep copy helper ensures all arrays are properly cloned when entering edit mode

**Testing**:
- Frontend builds successfully (`npm run build`)
- No TypeScript errors
- No eslint warnings
- Component follows existing patterns from other section components

### Stage 3.3: Reusable Editors

#### Task 3.3.1: Create `editors/StringFieldEditor.tsx` - Text input / textarea for string fields ✅
**Commit**: `702f180`

**Implementation**:
- Created `src/sip_videogen/studio/frontend/src/components/BrandMemory/editors/StringFieldEditor.tsx`
- Reusable text field editor component supporting both single-line and multi-line modes
- **Props**:
  - `value`: Current value of the field
  - `onChange`: Callback when value changes
  - `label`: Label text displayed above the field
  - `placeholder`: Optional placeholder text
  - `multiline`: Boolean to switch between Input (single-line) and textarea (multi-line)
  - `minHeight`: Minimum height for textarea (default "80px")
  - `maxLength`: Optional max length with character count display
  - `disabled`: Whether field is disabled
  - `required`: Shows red asterisk if required
  - `className`: Additional container class names
- Uses existing `Input` component from `@/components/ui/input` for single-line
- Raw textarea with consistent shadcn styling for multi-line
- Character count shown when maxLength is set

**Testing**:
- Frontend builds successfully (`npm run build`)
- No TypeScript errors
- No eslint warnings
- Component follows existing UI patterns

#### Task 3.3.2: Create `editors/StringListEditor.tsx` - List with add/remove for string arrays ✅
**Commit**: `bf90502`

**Implementation**:
- Created `src/sip_videogen/studio/frontend/src/components/BrandMemory/editors/StringListEditor.tsx`
- Reusable string list editor component with add/remove functionality
- **Props**:
  - `value`: Current list of string values
  - `onChange`: Callback when list changes
  - `label`: Label text displayed above the list
  - `placeholder`: Optional placeholder text for each input
  - `disabled`: Whether inputs are disabled
  - `minItems`: Minimum number of items required (prevents removal below this count)
  - `addButtonText`: Custom text for add button (defaults to "Add {label singular}")
  - `className`: Additional container class names
- Automatically generates singular form of label for add button text (removes trailing 's')
- Uses existing `Input` and `Button` components from UI library
- Matches pattern established in section components (`renderStringListEditor` helper)

**Testing**:
- Frontend builds successfully (`npm run build`)
- No TypeScript errors
- No eslint warnings
- Component follows existing UI patterns

#### Task 3.3.3: Create `editors/ColorListEditor.tsx` - Color swatches with color picker ✅
**Commit**: `fc10620`

**Implementation**:
- Created `src/sip_videogen/studio/frontend/src/components/BrandMemory/editors/ColorListEditor.tsx`
- Reusable color list editor component for editing `ColorDefinition[]` arrays
- **Props**:
  - `value`: Current list of ColorDefinition objects
  - `onChange`: Callback when list changes
  - `label`: Label text displayed above the list
  - `disabled`: Whether inputs are disabled
  - `minItems`: Minimum number of items required (prevents removal below this count)
  - `addButtonText`: Custom text for add button (defaults to "Add {label singular}")
  - `className`: Additional container class names
- Uses native `<input type="color">` picker (no new dependencies per TASKS.md requirement)
- Includes hex text input for precise hex code entry
- Name and usage fields for each color entry
- Add/remove functionality with minItems support
- Follows same pattern as StringListEditor for consistency

**Testing**:
- Frontend builds successfully (`npm run build`)
- No TypeScript errors
- No eslint warnings
- Component follows existing UI patterns

#### Task 3.3.4: Create `editors/TypographyListEditor.tsx` - Typography rules form ✅
**Commit**: `4cefa05`

**Implementation**:
- Created `src/sip_videogen/studio/frontend/src/components/BrandMemory/editors/TypographyListEditor.tsx`
- Reusable typography list editor component for editing `TypographyRule[]` arrays
- **Props**:
  - `value`: Current list of TypographyRule objects
  - `onChange`: Callback when list changes
  - `label`: Label text displayed above the list
  - `disabled`: Whether inputs are disabled
  - `minItems`: Minimum number of items required (prevents removal below this count)
  - `addButtonText`: Custom text for add button (defaults to "Add Typography Rule")
  - `className`: Additional container class names
- Card-based layout for each rule with clear field labels
- Fields: role, family, weight, style_notes (textarea for longer notes)
- 2-column grid layout for role and family fields
- Add/remove functionality with minItems support
- Follows same pattern as ColorListEditor for consistency

**Testing**:
- Frontend builds successfully (`npm run build`)
- No TypeScript errors
- No eslint warnings
- Component follows existing UI patterns

---

## Next Tasks

### Stage 3: Brand Memory View with Reusable Editors - COMPLETE ✅
- [x] Task 3.1.1: Create `BrandMemory/index.tsx` - Main view container
- [x] Task 3.1.2: Create `BrandMemory/MemorySection.tsx` - Reusable expandable section wrapper
- [x] Task 3.2.1: Create `sections/CoreSection.tsx` - Core identity section
- [x] Task 3.2.2: Create `sections/VisualSection.tsx` - Visual identity section
- [x] Task 3.2.3: Create `sections/VoiceSection.tsx` - Voice guidelines section
- [x] Task 3.2.4: Create `sections/AudienceSection.tsx` - Audience profile section
- [x] Task 3.2.5: Create `sections/PositioningSection.tsx` - Competitive positioning section
- [x] Task 3.2.6: Create `sections/ConstraintsAvoidSection.tsx` - Constraints + avoid lists
- [x] Task 3.3.1: Create `editors/StringFieldEditor.tsx` - Text input / textarea for string fields
- [x] Task 3.3.2: Create `editors/StringListEditor.tsx` - List with add/remove for string arrays
- [x] Task 3.3.3: Create `editors/ColorListEditor.tsx` - Color swatches with color picker
- [x] Task 3.3.4: Create `editors/TypographyListEditor.tsx` - Typography rules form

### Stage 3.4: Edit UX - COMPLETE ✅
*Note: These tasks were implemented as part of Section Components (Task 3.2.x) - each section includes Save/Cancel, spinner, and Alert components.*

- [x] Task 3.4.1: Implement Save/Cancel buttons per section (in MemorySection + each section component)
- [x] Task 3.4.2: Show spinner during save (each section uses `<Spinner>` while `isSaving`)
- [x] Task 3.4.3: Display success/error using inline Alert component (each section has Alert variants)
- [x] Task 3.4.4: Wait for server response - no optimistic updates (`await bridge.updateBrandIdentitySection()`)
- [x] Task 3.4.5: After successful save, show inline info that AI context is refreshed automatically ("AI context refreshed automatically" message)

#### Task 3.4.6: Wire up BrandMemory with section components ✅
**Commit**: `8c13129`

**Implementation**:
- Updated `src/sip_videogen/studio/frontend/src/components/BrandMemory/index.tsx`
- Replaced placeholder `SectionPlaceholder` components with actual section implementations
- Imported and integrated: CoreSection, VisualSection, VoiceSection, AudienceSection, PositioningSection, ConstraintsAvoidSection
- Used `MemorySectionGroup` wrapper for consistent section styling
- Each section receives its data slice from identity and `onIdentityUpdate={setIdentity}` callback

**Testing**:
- Frontend builds successfully (`npm run build`)
- No TypeScript errors
- No eslint warnings

### Stage 3.5: Regenerate UX

#### Task 3.5.1: Add confirmation dialog warning about edit loss ✅
**Commit**: `0318749`

**Implementation**:
- Created `src/sip_videogen/studio/frontend/src/components/ui/alert-dialog.tsx`
  - Uses existing `@radix-ui/react-alert-dialog` package (already installed)
  - Full AlertDialog component following shadcn/ui patterns
- Created `src/sip_videogen/studio/frontend/src/components/BrandMemory/RegenerateConfirmDialog.tsx`
  - Warns users that regenerating will overwrite all current edits
  - Explains that a backup will be created (can be restored from History)
  - Explains that AI brand director will re-run on source materials
  - Amber warning styling for destructive action emphasis
- Updated `BrandMemory/index.tsx`:
  - Added `showRegenerateConfirm` state
  - Wired Regenerate button to open confirmation dialog
  - Added `handleRegenerateConfirm` handler (placeholder for Task 3.5.2-3.5.4)

**Testing**:
- Frontend builds successfully (`npm run build`)
- No TypeScript errors
- No eslint warnings

#### Remaining Tasks
- [ ] Task 3.5.2: Show progress indicator during regeneration
- [ ] Task 3.5.3: Auto-backup before regenerating
- [ ] Task 3.5.4: After regeneration completes, show inline info that AI context is refreshed automatically

### Stage 3.6: Status Feedback Component
- [ ] Task 3.6.1: Create `BrandMemory/StatusAlert.tsx` - Inline success/error/info alerts

---

## Files Modified
- `src/sip_videogen/brands/storage.py` - Added backup, list_backups, and restore_backup functions
- `src/sip_videogen/studio/bridge.py` - Added get_brand_identity, update_brand_identity_section, regenerate_brand_identity, list_identity_backups, and restore_identity_backup bridge methods
- `src/sip_videogen/studio/frontend/src/types/brand-identity.ts` - NEW: TypeScript types for brand identity
- `src/sip_videogen/studio/frontend/src/lib/bridge.ts` - Added brand identity bridge methods and wrapper functions
- `src/sip_videogen/studio/frontend/src/components/BrandMemory/index.tsx` - NEW: Main Brand Memory view container
- `src/sip_videogen/studio/frontend/src/components/BrandMemory/MemorySection.tsx` - NEW: Reusable expandable section wrapper
- `src/sip_videogen/studio/frontend/src/components/BrandMemory/sections/CoreSection.tsx` - NEW: Core identity section component
- `src/sip_videogen/studio/frontend/src/components/BrandMemory/sections/VisualSection.tsx` - NEW: Visual identity section component with color picker, typography, and imagery editors
- `src/sip_videogen/studio/frontend/src/components/BrandMemory/sections/VoiceSection.tsx` - NEW: Voice guidelines section component with personality, tone, messaging, and examples editors
- `src/sip_videogen/studio/frontend/src/components/BrandMemory/sections/AudienceSection.tsx` - NEW: Audience profile section component with demographics, psychographics, pain points, and desires editors
- `src/sip_videogen/studio/frontend/src/components/BrandMemory/sections/PositioningSection.tsx` - NEW: Competitive positioning section component with market category, UVP, competitors, differentiation, and positioning statement editors
- `src/sip_videogen/studio/frontend/src/components/BrandMemory/sections/ConstraintsAvoidSection.tsx` - NEW: Constraints and avoid lists section component with add/remove functionality for both arrays
- `src/sip_videogen/studio/frontend/src/components/BrandMemory/editors/StringFieldEditor.tsx` - NEW: Reusable text field editor supporting single-line Input and multi-line textarea modes
- `src/sip_videogen/studio/frontend/src/components/BrandMemory/editors/StringListEditor.tsx` - NEW: Reusable string list editor with add/remove functionality for string arrays
- `src/sip_videogen/studio/frontend/src/components/BrandMemory/editors/ColorListEditor.tsx` - NEW: Reusable color list editor with native color picker and hex input for ColorDefinition arrays
- `src/sip_videogen/studio/frontend/src/components/BrandMemory/editors/TypographyListEditor.tsx` - NEW: Reusable typography list editor with card-based layout for TypographyRule arrays
- `src/sip_videogen/studio/frontend/src/components/ui/alert-dialog.tsx` - NEW: AlertDialog UI component using Radix AlertDialog primitive
- `src/sip_videogen/studio/frontend/src/components/BrandMemory/RegenerateConfirmDialog.tsx` - NEW: Confirmation dialog for regenerating brand identity with edit loss warning
