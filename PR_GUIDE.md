# PR Guide: Hierarchical Memory System for Brand Studio

## Overview
This PR implements a hierarchical memory system for Brand Studio, adding Product and Project memory layers alongside the existing Brand Identity layer.

## Related Files
- **Task List**: `IMPLEMENTATION_PLAN.md`
- **Main Changes**: `src/sip_videogen/brands/models.py`, `src/sip_videogen/brands/storage.py`, `src/sip_videogen/advisor/agent.py`

## Completed Tasks

### Phase 1: Data Models ✅
**File**: `src/sip_videogen/brands/models.py`

Added new Pydantic models following existing patterns:

**Product Models:**
- `ProductAttribute`: Key-value pairs for product properties (dimensions, material, etc.)
- `ProductSummary`: L0 layer - slug, name, description, primary_image, attribute_count
- `ProductFull`: L1 layer - full details including images list and attributes
- `ProductIndex`: Registry with get/add/remove methods

**Project Models:**
- `ProjectStatus`: Enum (ACTIVE, ARCHIVED)
- `ProjectSummary`: L0 layer - slug, name, status, asset_count
- `ProjectFull`: L1 layer - instructions markdown
- `ProjectIndex`: Registry with active_project tracking

**Key Design Decisions:**
- All image paths are brand-relative (e.g., `products/night-cream/images/main.png`)
- `to_summary()` methods convert L1 to L0 layer
- Project asset_count requires external filesystem access (passed as parameter)
- Index classes follow BrandIndex pattern with get/add/remove methods

### Phase 2: Storage Layer ✅
**File**: `src/sip_videogen/brands/storage.py`

Added CRUD functions following existing brand storage patterns:

**Product Functions:**
- Path helpers: `get_products_dir`, `get_product_dir`, `get_product_index_path`
- Index: `load_product_index`, `save_product_index`
- CRUD: `create_product`, `load_product`, `save_product`, `delete_product`
- Listing: `list_products`, `load_product_summary`
- Images: `add_product_image`, `delete_product_image`, `list_product_images`, `set_primary_product_image`

**Project Functions:**
- Path helpers: `get_projects_dir`, `get_project_dir`, `get_project_index_path`
- Index: `load_project_index`, `save_project_index`
- CRUD: `create_project`, `load_project`, `save_project`, `delete_project`
- Listing: `list_projects`, `load_project_summary`
- Active project: `get_active_project`, `set_active_project`
- Asset tracking: `count_project_assets`, `list_project_assets` (filename prefix search)

**Key Implementation Details:**
- All paths returned are brand-relative (e.g., `products/night-cream/images/main.png`)
- Project assets tracked via filename prefix in `assets/generated/` (e.g., `christmas-campaign__timestamp_hash.png`)
- `list_project_assets` returns assets-relative paths for UI compatibility (`generated/...`)
- Asset count recalculated on project save

**Tests Added:**
- 49 new tests in `tests/test_brands_storage.py` covering:
  - Product path helpers, index management, CRUD operations
  - Product image management (add, delete, list, set primary)
  - Project path helpers, index management, CRUD operations
  - Active project management
  - Project asset counting and listing

### Phase 3: Memory & Context Layer ✅
**Files**: `src/sip_videogen/brands/memory.py`, `src/sip_videogen/brands/context.py`

**Memory Access Functions (memory.py):**
- `get_product_summary(brand_slug, product_slug)`: Get L0 product summary
- `get_product_detail(brand_slug, product_slug)`: Get L1 product JSON for agents
- `get_product_full(brand_slug, product_slug)`: Get full ProductFull object
- `get_product_images_for_generation(brand_slug, product_slug)`: Get brand-relative image paths
- `get_project_summary(brand_slug, project_slug)`: Get L0 project summary
- `get_project_detail(brand_slug, project_slug)`: Get L1 project JSON for agents
- `get_project_full(brand_slug, project_slug)`: Get full ProjectFull object
- `get_project_instructions(brand_slug, project_slug)`: Get instructions markdown

**Context Builders (context.py):**
- `ProductContextBuilder`: Builds formatted product context including:
  - Product name, slug, description
  - Attributes list
  - Reference images with primary marker
- `ProjectContextBuilder`: Builds formatted project context including:
  - Project name, slug, status
  - Instructions markdown
- `HierarchicalContextBuilder`: Combines project + products for per-turn injection
  - Project context comes first (more global)
  - Attached products section follows
  - Graceful degradation: silently skips missing products/projects
- Convenience functions: `build_product_context()`, `build_project_context()`, `build_turn_context()`

**Key Design Decisions:**
- All image paths remain brand-relative throughout
- `HierarchicalContextBuilder` builds per-turn context (NOT system prompt)
- Missing products/projects are silently skipped for graceful degradation
- Project context appears before product context in combined output

**Tests Added:**
- 41 new tests in `tests/test_brands_memory.py` covering:
  - Product memory functions (summary, detail, images, full)
  - Project memory functions (summary, instructions, detail, full)
  - ProductContextBuilder (raises for nonexistent, builds correct output)
  - ProjectContextBuilder (raises for nonexistent, includes instructions)
  - HierarchicalContextBuilder (empty without context, includes both, ordering, graceful skip)
  - Convenience functions (build_product_context, build_project_context, build_turn_context)

### Phase 3.5: Per-Turn Context Injection ✅
**File**: `src/sip_videogen/advisor/agent.py`

Implemented per-turn context injection to dynamically inject project and product context into user messages:

**Changes to BrandAdvisor:**
- `chat_with_metadata()` accepts new parameters: `project_slug`, `attached_products`
- `chat()` accepts same new parameters
- `chat_stream()` accepts same new parameters
- All three methods use `HierarchicalContextBuilder` to build per-turn context

**Per-Turn Context Injection Pattern:**
```python
# Context is prepended to user message, NOT added to system prompt
augmented_message = f"""## Current Context

{turn_context}

---

## User Request

{raw_user_message}"""
```

**Key Implementation Details:**
- Skill matching uses **raw user message** (not augmented) - prevents context skewing skill selection
- History stores **raw user message** (not augmented) - prevents history from ballooning
- Context injection only happens when `brand_slug` is set AND (`project_slug` or `attached_products` provided)
- Dynamic context changes work mid-conversation without rebuilding the Agent

**Tests Added:**
- 9 new tests in `tests/test_brand_advisor.py` covering:
  - `test_chat_with_project_context`: Project context injected
  - `test_chat_with_attached_products`: Product context injected
  - `test_chat_with_project_and_products`: Both contexts together
  - `test_chat_without_context_does_not_augment`: No context when params empty
  - `test_skill_matching_uses_raw_message`: Skills match raw message
  - `test_history_stores_raw_message`: History stores raw message
  - `test_chat_with_metadata_accepts_context_params`: API accepts params
  - `test_no_brand_slug_skips_context_injection`: No context without brand

## Remaining Tasks

### Phase 3.6: Product Image Routing
**File**: `src/sip_videogen/advisor/tools.py`
- Wire product images to generate_image()

### Phase 3.7: Project Asset Tagging
**File**: `src/sip_videogen/advisor/tools.py`
- Tag generated images with project prefix

### Phase 4: Agent Tools
**File**: `src/sip_videogen/advisor/tools.py`
- Add list_products, list_projects, get_product_detail, get_project_detail tools

### Phase 5: Bridge API
**File**: `src/sip_videogen/studio/bridge.py`
- Product and project CRUD methods
- Update chat() signature

### Phase 6: Frontend Types & Contexts
**Files**: Frontend TypeScript files
- Add TypeScript interfaces
- ProductContext and ProjectContext

### Phase 7: Sidebar Restructure
- Accordion-based organization by memory scope

### Phase 8: Chat Integration
- Attached products display
- Project banner
- Context passing in chat calls

## Testing Notes
- All 94 storage tests pass: `python -m pytest tests/test_brands_storage.py -v`
- All 81 memory/context tests pass: `python -m pytest tests/test_brands_memory.py -v`
- All 31 advisor tests pass: `python -m pytest tests/test_brand_advisor.py -v`
- Total: 206 tests for brands + advisor modules

## Commits
- `61e558a`: feat(models): Add Product and Project models for hierarchical memory system
- `9fe3b1f`: feat(storage): Add Product and Project storage layer functions
- `bd581b0`: feat(memory): Add Product and Project memory and context layer functions
- `c5410ab`: feat(advisor): Add per-turn context injection for products and projects
