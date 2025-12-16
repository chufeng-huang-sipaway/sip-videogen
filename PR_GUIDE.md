# PR Guide: Hierarchical Memory System for Brand Studio

## Overview
This PR implements a hierarchical memory system for Brand Studio, adding Product and Project memory layers alongside the existing Brand Identity layer.

## Related Files
- **Task List**: `IMPLEMENTATION_PLAN.md`
- **Main Changes**: `src/sip_videogen/brands/models.py`, `src/sip_videogen/brands/storage.py`

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

## Remaining Tasks

### Phase 3: Memory & Context Layer
**Files**: `src/sip_videogen/brands/memory.py`, `src/sip_videogen/brands/context.py`
- Memory access functions
- Context builders for agent prompts
- HierarchicalContextBuilder for per-turn injection

### Phase 3.5: Per-Turn Context Injection
**File**: `src/sip_videogen/advisor/agent.py`
- Inject project+product context per-turn (not system prompt)

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
- All 94 storage tests pass
- Run `python -m pytest tests/test_brands_storage.py -v` to verify

## Commits
- `61e558a`: feat(models): Add Product and Project models for hierarchical memory system
- `9fe3b1f`: feat(storage): Add Product and Project storage layer functions
