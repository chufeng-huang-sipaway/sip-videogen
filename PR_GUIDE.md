# PR Guide: Hierarchical Memory System for Brand Studio

## Overview
This PR implements a hierarchical memory system for Brand Studio, adding Product and Project memory layers alongside the existing Brand Identity layer.

## Related Files
- **Task List**: `IMPLEMENTATION_PLAN.md`
- **Main Changes**: `src/sip_videogen/brands/models.py`

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

## Remaining Tasks

### Phase 2: Storage Layer
**File**: `src/sip_videogen/brands/storage.py`
- Add product CRUD functions
- Add project CRUD functions with active project management
- Implement project asset listing via filename prefix

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
- All new models pass manual testing
- Existing test suite has 2 pre-existing failures (unrelated to this PR)
- Run `python -m pytest tests/test_models.py` to verify

## Commits
- `61e558a`: feat(models): Add Product and Project models for hierarchical memory system
