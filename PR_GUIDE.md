# Brand Management System - Implementation Progress

## Task List Reference
- **Source**: `BRAND_SYSTEM_TODO.md`
- **Feature**: Persistent brand management system with hierarchical memory

## Progress Summary

| Stage | Description | Status |
|-------|-------------|--------|
| 1 | Brand Storage Foundation | ✅ Complete (7/7 tasks) |
| 2 | Hierarchical Memory System | ✅ Complete (4/4 tasks) |
| 3 | Brand Agent Team | ✅ Complete (7/7 tasks) |
| 4 | Interactive Brand Menu | 🔄 In Progress (1/5 tasks) |
| 5 | Integration & Polish | ⏳ Pending |

## Completed Tasks

### Task 1.1: Create brands package structure ✅
**Commit**: `ee5451f`

**Files Created**:
- `src/sip_videogen/brands/__init__.py` - Package init with module docstring and exports (commented until modules exist)

**Acceptance Criteria**:
- [x] Directory `src/sip_videogen/brands/` exists
- [x] `__init__.py` has docstring explaining the package
- [x] Running `python -c "from sip_videogen import brands"` doesn't error

---

### Task 1.2: Define BrandSummary model (L0 - Always in Context) ✅
**Commit**: `2f5ce80`

**Files Created**:
- `src/sip_videogen/brands/models.py` - BrandSummary Pydantic model for L0 memory layer

**Model Fields**:
- Core Identity: slug, name, tagline, category, tone (all required)
- Visual Essence: primary_colors, visual_style, logo_path (optional with defaults)
- Audience: audience_summary (optional)
- Memory Pointers: available_details, asset_count, last_generation
- Agent Guidance: exploration_hint

**Acceptance Criteria**:
- [x] `BrandSummary` model defined with all fields documented
- [x] Model can be instantiated with minimal required fields
- [x] `model.model_dump_json()` produces valid JSON under 2000 characters (actual: 457 chars)
- [x] All fields have `description` parameter in Field()

### Task 1.3: Define supporting identity models ✅
**Commit**: `36c7532`

**Files Modified**:
- `src/sip_videogen/brands/models.py` - Added 6 supporting models for L1 layer

**Models Added**:
- `ColorDefinition`: Single color with hex, name, and usage
- `TypographyRule`: Typography specification by role (headings, body, accent)
- `VisualIdentity`: Complete visual design system (12 fields)
- `VoiceGuidelines`: Brand voice and messaging (7 fields)
- `AudienceProfile`: Target audience demographics/psychographics (10 fields)
- `CompetitivePositioning`: Market positioning and differentiation (5 fields)

**Acceptance Criteria**:
- [x] All 4 supporting models defined: VisualIdentity, VoiceGuidelines, AudienceProfile, CompetitivePositioning
- [x] Each model can be instantiated with no arguments (all fields have defaults)
- [x] ColorDefinition and TypographyRule helper models defined
- [x] All fields have descriptions

### Task 1.4: Define BrandIdentityFull model (L1 - On Demand) ✅
**Commit**: `8eee1fc`

**Files Modified**:
- `src/sip_videogen/brands/models.py` - Added BrandCoreIdentity and BrandIdentityFull models
- `src/sip_videogen/brands/__init__.py` - Updated exports with all models

**Models Added**:
- `BrandCoreIdentity`: Fundamental brand identity elements
  - `name`, `tagline`, `mission`, `brand_story`, `values`
- `BrandIdentityFull`: Complete L1 layer model
  - Metadata: `slug`, `created_at`, `updated_at`
  - Identity sections: `core`, `visual`, `voice`, `audience`, `positioning`
  - Constraints: `constraints`, `avoid` lists
  - `to_summary()` method to extract L0 BrandSummary from full identity

**Acceptance Criteria**:
- [x] BrandIdentityFull model defined with all sections
- [x] `to_summary()` method correctly extracts BrandSummary
- [x] Can round-trip: create full identity → extract summary → summary has correct values
- [x] All fields have `description` parameter in Field()

---

### Task 1.5: Define BrandIndex model ✅
**Commit**: `aa8bd44`

**Files Modified**:
- `src/sip_videogen/brands/models.py` - Added BrandIndexEntry and BrandIndex models
- `src/sip_videogen/brands/__init__.py` - Updated exports

**Models Added**:
- `BrandIndexEntry`: Entry for quick brand listing
  - `slug`, `name`, `category` fields
  - Timestamps: `created_at`, `updated_at`, `last_accessed`
- `BrandIndex`: Registry of all brands
  - `version` field for format versioning
  - `brands` list and `active_brand` tracking
  - Helper methods: `get_brand()`, `add_brand()`, `remove_brand()`
  - `remove_brand()` clears `active_brand` if removing the active brand

**Acceptance Criteria**:
- [x] BrandIndex model defined with brands list and active_brand
- [x] `get_brand()` returns entry or None
- [x] `add_brand()` adds new and updates existing
- [x] `remove_brand()` removes and clears active if needed
- [x] Test: add brand, get brand, remove brand cycle works

---

### Task 1.6: Implement brand storage functions ✅
**Commit**: `6cd0461`

**Files Created**:
- `src/sip_videogen/brands/storage.py` - CRUD functions for brand persistence

**Files Modified**:
- `src/sip_videogen/brands/__init__.py` - Updated exports with storage functions

**Functions Implemented**:
- Path helpers: `get_brands_dir()`, `get_brand_dir()`, `get_index_path()`
- `slugify()` function to convert names to URL-safe slugs
- Index management: `load_index()`, `save_index()`
- CRUD: `create_brand()`, `load_brand()`, `load_brand_summary()`, `save_brand()`, `delete_brand()`, `list_brands()`
- Active brand: `get_active_brand()`, `set_active_brand()`

**Directory Structure Created**:
```
{brand-slug}/
├── identity.json          # L0 summary
├── identity_full.json     # L1 full identity
├── assets/
│   ├── logo/
│   ├── packaging/
│   ├── lifestyle/
│   ├── mascot/
│   └── marketing/
└── history/
```

**Acceptance Criteria**:
- [x] All CRUD functions implemented: create, load, save, delete, list
- [x] `get_active_brand()` and `set_active_brand()` work
- [x] Brand directory structure is created correctly
- [x] Index is updated on all operations
- [x] slugify() converts names to URL-safe slugs correctly

---

### Task 1.7: Write tests for brand storage ✅
**Commit**: `6815f60`

**Files Created**:
- `tests/test_brands_storage.py` - Comprehensive test suite for brand storage (45 tests)

**Test Classes**:
- `TestSlugify`: 9 tests for slugify function covering various inputs
- `TestPathHelpers`: 3 tests for path helper functions
- `TestIndexManagement`: 3 tests for index load/save operations
- `TestBrandCRUD`: 19 tests for create, load, save, delete, list operations
- `TestActiveBrand`: 5 tests for active brand management
- `TestBrandToSummaryConversion`: 7 tests for L1 to L0 conversion

**Key Implementation Details**:
- Uses `temp_brands_dir` fixture with `unittest.mock.patch` to isolate tests
- Tests use `tmp_path` pytest fixture for temporary directories
- All tests are deterministic and don't use real user data

**Acceptance Criteria**:
- [x] Test file created with all test classes
- [x] All tests pass: `python -m pytest tests/test_brands_storage.py -v` (45 tests)
- [x] Tests use temporary directories, not real user data
- [x] Coverage includes: create, load, save, delete, list, active brand

---

### Task 2.1: Implement memory layer access functions ✅
**Commit**: `06fadd7`

**Files Created**:
- `src/sip_videogen/brands/memory.py` - Hierarchical memory access functions

**Files Modified**:
- `src/sip_videogen/brands/__init__.py` - Updated exports with memory functions

**Functions Implemented**:
- `get_brand_summary(slug)`: Returns L0 `BrandSummary` or `None` (wrapper for `load_brand_summary`)
- `get_brand_detail(slug, detail_type)`: Returns JSON string of L1 detail section
  - Supports: `visual_identity`, `voice_guidelines`, `audience_profile`, `positioning`, `full_identity`
  - Returns error message string if brand not found or invalid detail type
- `list_brand_assets(slug, category)`: Returns `list[dict]` of asset info
  - Filters by category: logo, packaging, lifestyle, mascot, marketing
  - Returns path, category, name, filename for each image file

**Type Definition**:
- `DetailType`: Literal type with 5 valid detail types for type safety

**Key Design Decision**:
- These are **internal functions** that return Python types
- Agent **tool functions** in Task 2.2 will wrap these and return JSON strings for agent consumption

**Acceptance Criteria**:
- [x] `get_brand_summary()` returns `BrandSummary` or `None`
- [x] `get_brand_detail()` returns JSON string for each detail type
- [x] `list_brand_assets()` returns `list[dict]` (internal use)
- [x] Invalid detail type returns error message string (not exception)

---

### Task 2.2: Create agent tools for memory access ✅
**Commit**: `09d48d6`

**Files Created**:
- `src/sip_videogen/brands/tools.py` - Agent-callable tool functions for brand memory access

**Files Modified**:
- `src/sip_videogen/brands/__init__.py` - Updated exports with tool functions

**Functions Implemented**:
- `set_brand_context(slug)`: Set current brand context for tools (called before running agents)
- `get_brand_context()`: Get current brand context
- `fetch_brand_detail(detail_type)`: Agent tool to fetch L1 brand information
  - Supports: `visual_identity`, `voice_guidelines`, `audience_profile`, `positioning`, `full_identity`
  - Returns JSON string or error message if no context set
- `browse_brand_assets(category)`: Agent tool to explore L2 asset listings
  - Optional category filter: logo, packaging, lifestyle, mascot, marketing
  - Returns JSON list or "No assets found" message

**Key Design Decision**:
- Global `_current_brand_slug` variable tracks which brand agents are working with
- All tool functions return strings (JSON or error messages) for agent consumption
- Detailed docstrings included since agents see them when using tools

**Acceptance Criteria**:
- [x] `set_brand_context()` and `get_brand_context()` work
- [x] `fetch_brand_detail()` returns JSON or error message
- [x] `browse_brand_assets()` returns JSON list or "No assets" message
- [x] Functions have detailed docstrings (agents see these)

---

### Task 2.3: Create BrandContextBuilder for prompt injection ✅
**Commit**: `ba197be`

**Files Created**:
- `src/sip_videogen/brands/context.py` - Brand context builder for agent prompts

**Files Modified**:
- `src/sip_videogen/brands/__init__.py` - Updated exports with context builder

**Classes/Functions Implemented**:
- `BrandContextBuilder` class:
  - `__init__(slug)`: Initialize with brand slug, raises `ValueError` if brand not found
  - `build_context_section()`: Build formatted brand context string for agent prompts
  - `_format_available_details()`: Format the available details list with descriptions
  - `inject_into_prompt(base_prompt, placeholder)`: Replace placeholder with context in prompts
- `build_brand_context(slug)`: Convenience function that returns context or error message
- `DETAIL_DESCRIPTIONS`: Dict mapping detail types to human-readable descriptions

**Context Output Format**:
The generated context includes:
1. Brand summary (name, tagline, category, tone, colors, style, audience)
2. Available brand details list with descriptions
3. Asset library count
4. Memory Exploration Protocol instructions for agents

**Acceptance Criteria**:
- [x] `BrandContextBuilder` constructs context from summary
- [x] Context includes: brand info, available details list, exploration protocol
- [x] `inject_into_prompt()` replaces placeholder correctly
- [x] `build_brand_context()` convenience function works

---

### Task 2.4: Write tests for memory system ✅
**Commit**: `795ed87`

**Files Created**:
- `tests/test_brands_memory.py` - Comprehensive test suite for memory system (39 tests)

**Test Classes**:
- `TestGetBrandSummary`: 2 tests for L0 summary retrieval
- `TestGetBrandDetail`: 7 tests for L1 detail fetching (all 5 detail types + error cases)
- `TestListBrandAssets`: 7 tests for L2 asset listing with category filters
- `TestBrandContext`: 3 tests for context management
- `TestFetchBrandDetailTool`: 3 tests for agent tool with/without context
- `TestBrowseBrandAssetsTool`: 5 tests for asset browsing tool
- `TestBrandContextBuilder`: 8 tests for prompt context generation
- `TestBuildBrandContext`: 2 tests for convenience function
- `TestDetailDescriptions`: 2 tests for DETAIL_DESCRIPTIONS constant

**Key Implementation Details**:
- Uses `temp_brands_dir` fixture with `unittest.mock.patch` to isolate tests
- Uses `brand_with_assets` fixture that creates test image files
- Tests verify non-image files are filtered from asset listings
- Tests verify Memory Exploration Protocol is included in context

**Acceptance Criteria**:
- [x] Tests for `get_brand_detail()` with each detail type
- [x] Tests for `list_brand_assets()` with and without category filter
- [x] Tests for `BrandContextBuilder` output format
- [x] Tests for tool functions with and without brand context set
- [x] All tests pass

---

### Task 3.1: Define agent output models ✅
**Commit**: `5de3b85`

**Files Created**:
- `src/sip_videogen/models/brand_agent_outputs.py` - Output models for brand agents

**Models Added**:
- `BrandStrategyOutput`: Output from Brand Strategist agent
  - Contains: `core_identity`, `audience_profile`, `positioning`, `strategy_notes`
- `VisualIdentityOutput`: Output from Visual Identity Designer agent
  - Contains: `visual_identity`, `design_rationale`, `logo_brief`
- `BrandVoiceOutput`: Output from Brand Voice Writer agent
  - Contains: `voice_guidelines`, `sample_copy`, `voice_rationale`
- `BrandValidationIssue`: Single validation issue for Brand Guardian
  - Contains: `category`, `severity`, `description`, `recommendation`
- `BrandGuardianOutput`: Output from Brand Guardian agent
  - Contains: `is_valid`, `issues`, `consistency_score`, `validation_notes`
- `BrandDirectorOutput`: Output from Brand Director orchestrator
  - Contains: `brand_identity`, `creative_rationale`, `validation_passed`, `next_steps`

**Key Design Decisions**:
- All models reuse existing brand identity models from `sip_videogen.brands.models`
- Follows same patterns as existing `agent_outputs.py`
- All fields have descriptive `Field()` parameters

**Acceptance Criteria**:
- [x] Output models defined for all 5 agents
- [x] Each model can be instantiated
- [x] Models match what agents will return

---

### Task 3.2: Create Brand Strategist agent ✅
**Commit**: `6333d14`

**Files Created**:
- `src/sip_videogen/agents/brand_strategist.py` - Agent definition with develop_brand_strategy function
- `src/sip_videogen/agents/prompts/brand_strategist.md` - Comprehensive prompt with guidelines

**Agent Implementation**:
- `brand_strategist_agent`: Agent with `output_type=BrandStrategyOutput`
- Tools registered: `fetch_brand_detail`, `browse_brand_assets`
- `develop_brand_strategy(concept, existing_brand_slug)`: Async function for brand strategy development

**Prompt Features**:
- Role definition as senior brand strategist with 15+ years experience
- Core Identity Development: Name, tagline, mission, story, values guidelines
- Audience Development: Demographics, psychographics, pain points, desires
- Market Positioning: Category, UVP, competitors, positioning statement
- Memory Exploration Protocol for evolving existing brands
- Quality checklist for output verification
- Weak vs Strong examples for guidance

**Acceptance Criteria**:
- [x] Agent defined with `output_type=BrandStrategyOutput`
- [x] Prompt loaded from markdown file
- [x] Prompt includes Memory Exploration Protocol
- [x] Agent has clear, specific role (not generic)

---

### Task 3.3: Create Visual Identity Designer agent ✅
**Commit**: `7d9c7c9`

**Files Created**:
- `src/sip_videogen/agents/visual_designer.py` - Agent definition with develop_visual_identity function
- `src/sip_videogen/agents/prompts/visual_designer.md` - Comprehensive prompt with visual design guidelines

**Agent Implementation**:
- `visual_designer_agent`: Agent with `output_type=VisualIdentityOutput`
- Tools registered: `fetch_brand_detail`, `browse_brand_assets`
- `develop_visual_identity(brand_strategy, existing_brand_slug)`: Async function for visual identity development

**Prompt Features**:
- Role definition as senior visual identity designer with 15+ years experience
- Color Theory Application: Primary, secondary, accent colors with psychology guidance
- Typography System: Heading, body, accent fonts with pairing rules
- Imagery Direction: Style, keywords (5-10), avoidances (3-5)
- Materials & Textures guidance
- Logo Brief generation guidelines
- Memory Exploration Protocol for evolving existing brands
- Quality checklist for output verification
- Weak vs Strong examples for guidance (7738 chars total)

**Acceptance Criteria**:
- [x] Agent defined with `output_type=VisualIdentityOutput`
- [x] Prompt includes color theory guidance
- [x] Prompt includes Memory Exploration Protocol

---

### Task 3.4: Create Brand Voice Writer agent ✅
**Commit**: `e2cbb3b`

**Files Created**:
- `src/sip_videogen/agents/brand_voice.py` - Agent definition with develop_brand_voice function
- `src/sip_videogen/agents/prompts/brand_voice.md` - Comprehensive prompt with copywriting guidelines

**Agent Implementation**:
- `brand_voice_agent`: Agent with `output_type=BrandVoiceOutput`
- Tools registered: `fetch_brand_detail`, `browse_brand_assets`
- `develop_brand_voice(brand_strategy, existing_brand_slug)`: Async function for voice development

**Prompt Features**:
- Role definition as senior brand voice writer with 15+ years experience
- Voice Personality Development: Character traits, speaking style, voice spectrum
- Tone Attributes: Voice vs tone distinction, tone variations by context
- Messaging Framework: Key messages, do's and don'ts (4-6 each)
- Writing Examples: Headlines, taglines, sample copy
- Copywriting Best Practices: Clarity, active voice, specificity
- Memory Exploration Protocol for evolving existing brands
- Quality checklist for output verification
- Weak vs Strong examples demonstrating guidelines

**Acceptance Criteria**:
- [x] Agent defined with `output_type=BrandVoiceOutput`
- [x] Prompt includes copywriting guidance
- [x] Prompt includes Memory Exploration Protocol

---

### Task 3.5: Create Brand Guardian agent ✅
**Commit**: `4a9fb00`

**Files Created**:
- `src/sip_videogen/agents/brand_guardian.py` - Agent definition with validation functions
- `src/sip_videogen/agents/prompts/brand_guardian.md` - Comprehensive validation prompt

**Agent Implementation**:
- `brand_guardian_agent`: Agent with `output_type=BrandGuardianOutput`
- Tools registered: `fetch_brand_detail`, `browse_brand_assets`
- `validate_brand_identity(brand_identity_json, brand_slug)`: Validate a complete identity
- `validate_brand_work(strategy_output, visual_output, voice_output, brand_slug)`: Validate specialist work

**Prompt Features**:
- Role definition as senior brand quality assurance specialist
- 4-section validation checklist:
  - Strategic consistency (name, tagline, mission, values alignment)
  - Visual consistency (colors, typography, imagery coherence)
  - Voice consistency (personality, tone, messaging)
  - Cross-section consistency (all elements reinforce each other)
- Severity levels: error (blocks), warning (should fix), suggestion (nice to have)
- Scoring guidelines: 0.0-1.0 scale with clear meanings
- Memory Exploration Protocol: Always fetch full details before validating
- Weak vs Strong examples demonstrating proper validation output

**Acceptance Criteria**:
- [x] Agent defined with `output_type=BrandGuardianOutput`
- [x] Prompt includes validation checklist
- [x] Agent ALWAYS fetches brand details before validating

---

### Task 3.6: Create Brand Director orchestrator ✅
**Commit**: `1f422d6`

**Files Created**:
- `src/sip_videogen/agents/brand_director.py` - Orchestrator agent with agent-as-tool pattern
- `src/sip_videogen/agents/prompts/brand_director.md` - Comprehensive orchestration prompt

**Agent Implementation**:
- `brand_director_agent`: Agent with `output_type=BrandDirectorOutput`
- Specialist agents registered as tools:
  - `brand_strategist`: Develops core identity, audience, positioning
  - `visual_designer`: Creates visual identity and design system
  - `brand_voice`: Establishes voice and messaging guidelines
  - `brand_guardian`: Validates brand consistency
- Memory tools registered: `fetch_brand_detail`, `browse_brand_assets`
- `develop_brand(concept, existing_brand_slug, progress_callback)`: Main entry point
- `develop_brand_with_output()`: Returns full BrandDirectorOutput with rationale

**Progress Tracking**:
- `BrandAgentProgress` dataclass for progress updates
- `BrandProgressTrackingHooks` class implementing RunHooks interface
- Progress callback support for real-time UI updates

**Prompt Features**:
- Role definition as senior brand director with 20+ years experience
- Team description with each specialist's responsibilities
- Process flow for new brands and evolving existing brands
- Memory tools documentation with available detail types
- Quality standards checklist
- DO/DON'T guidelines for orchestration
- Example flow demonstrating full brand development

**Acceptance Criteria**:
- [x] Agent has specialist agents registered as tools
- [x] Agent has memory tools registered
- [x] `develop_brand()` async function implemented
- [x] Progress callback supported

---

### Task 3.7: Write tests for brand agents ✅
**Commit**: `3454bb7`

**Files Created**:
- `tests/test_brand_agents.py` - Comprehensive test suite for brand agents (51 tests)

**Test Classes**:
- `TestBrandStrategyOutput`: 2 tests for output model validation
- `TestVisualIdentityOutput`: 2 tests for output model validation
- `TestBrandVoiceOutput`: 2 tests for output model validation
- `TestBrandGuardianOutput`: 4 tests for validation output with/without issues
- `TestBrandDirectorOutput`: 2 tests for orchestrator output
- `TestBrandStrategistAgent`: 2 tests for async function with mocked Runner
- `TestVisualDesignerAgent`: 2 tests for async function with mocked Runner
- `TestBrandVoiceAgent`: 2 tests for async function with mocked Runner
- `TestBrandGuardianAgent`: 4 tests for validation functions
- `TestBrandDirectorAgent`: 7 tests for orchestrator (success, errors, progress callback)
- `TestBrandDevelopmentError`: 2 tests for custom exception
- `TestBrandAgentProgress`: 2 tests for progress dataclass
- `TestBrandProgressTrackingHooks`: 6 tests for RunHooks implementation
- `TestBrandAgentPrompts`: 5 tests verifying all prompt files exist
- `TestAgentDefinitions`: 7 tests verifying agent output_type and tools

**Key Implementation Details**:
- Uses `unittest.mock.AsyncMock` to mock `agents.Runner.run`
- Patches `sip_videogen.brands.context.build_brand_context` and `sip_videogen.brands.tools.set_brand_context` for existing brand tests
- Tests both success paths and error handling (empty/whitespace/too long input)
- Fixtures create realistic mock data for all agent output types

**Acceptance Criteria**:
- [x] Output model validation tests for all 5 agent types
- [x] Mock agent execution tests with mocked Runner.run
- [x] Orchestration flow tests including progress callback
- [x] All 51 tests pass: `python -m pytest tests/test_brand_agents.py -v`

---

### Task 4.1: Create brand picker menu ✅
**Commit**: `79917d0`

**Files Modified**:
- `src/sip_videogen/cli.py` - Added `_show_brand_picker()` function

**Implementation Details**:
- Added `_show_brand_picker()` function for interactive brand selection
- Displays brands sorted by last accessed (most recent first) with relative timestamps
- Active brand marked with ★ indicator
- Shows category in parentheses if available
- Includes options: Create New Brand, Brand Settings, Back to Main Menu
- Uses questionary for arrow-key navigation with styled choices
- Handles empty brands list with "No brands found" message

**Acceptance Criteria**:
- [x] Menu shows all brands with metadata (name, category, last accessed time)
- [x] Active brand marked with indicator (★)
- [x] Arrow key navigation works (questionary.select)
- [x] Returns selected brand slug or action (create_new, settings, back, None)

---

## Next Task

### Task 4.2: Create brand detail view
**Description**: Add rich panel display for brand details.

**Files to Modify**:
- `src/sip_videogen/cli.py`

**Key Points**:
- Create `_display_brand_detail()` function
- Show brand summary in formatted panel
- Display color palette visually if possible
- Show asset counts by category
- Display actions menu

## Feature Overview

The brand management system transforms the one-shot brand kit generator into a production-ready system with:
- Persistent brands stored in `~/.sip-videogen/brands/`
- 3-layer memory hierarchy (L0: Summary, L1: Details, L2: Assets)
- Agent team (Brand Director, Strategist, Visual Designer, Voice Writer, Guardian)
- Interactive CLI menu for brand selection and management

## Architecture

### File Structure
```
~/.sip-videogen/
├── config.json
├── brands/
│   ├── index.json                 # Registry of all brands
│   └── {brand-slug}/
│       ├── identity.json          # L0 Summary (~500 tokens)
│       ├── identity_full.json     # L1 Details
│       └── assets/
│           ├── logo/
│           ├── packaging/
│           ├── lifestyle/
│           ├── mascot/
│           └── marketing/
```

### Memory Hierarchy
| Layer | Name | Size | When Loaded |
|-------|------|------|-------------|
| L0 | Summary | ~500 tokens | Always in agent context |
| L1 | Details | ~2000 tokens | Agent requests via tool |
| L2 | Assets | N/A (file refs) | Agent requests via tool |
