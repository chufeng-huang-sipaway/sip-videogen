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

### Phase 3.6: Product Image Routing ✅
**File**: `src/sip_videogen/advisor/tools.py`

Wired product images to `generate_image()` tool for automatic reference-based generation:

**Changes to `generate_image()` and `_impl_generate_image()`:**
- Added `product_slug` parameter to both functions
- Auto-loads product's primary image as reference when `product_slug` provided
- Auto-enables `validate_identity=True` when using product reference
- Explicit `reference_image` parameter takes precedence over `product_slug`

**Path Flow:**
1. Product stored with `primary_image = "products/night-cream/images/main.png"` (brand-relative)
2. `generate_image(product_slug="night-cream")` loads product, gets `primary_image`
3. Pass to existing `reference_image` parameter
4. `_resolve_brand_path` resolves to absolute for actual file access

**Tests Added:**
- 5 new tests in `tests/test_advisor_tools.py` covering:
  - `test_generate_image_with_product_slug`: Auto-loads primary image
  - `test_generate_image_with_product_slug_not_found`: Error handling
  - `test_generate_image_with_product_slug_no_primary_image`: Graceful fallback
  - `test_generate_image_with_product_slug_no_active_brand`: Error handling
  - `test_generate_image_with_product_slug_reference_image_takes_precedence`: Priority check

### Phase 3.7: Project Asset Tagging ✅
**File**: `src/sip_videogen/advisor/tools.py`

Implemented project asset tagging via filename prefix for tracking generated images per project:

**New Helper Function:**
- `_generate_output_filename(project_slug)`: Generates filename with optional project prefix
  - With project: `{project_slug}__{timestamp}_{hash}.png` (e.g., `christmas-campaign__20241215_143022_a1b2c3d4.png`)
  - Without project: `{timestamp}_{hash}.png` (e.g., `20241215_143022_a1b2c3d4.png`)

**Changes to `_impl_generate_image()`:**
- Import `get_active_project` from storage module
- When no explicit filename is provided, check for active project
- Tag generated images with project prefix when project is active
- Explicit `filename` parameter bypasses project tagging

**Key Implementation Details:**
- Generated images remain in `assets/generated/` (no path change)
- Project membership tracked via filename prefix (`{project_slug}__`)
- Integrates with existing `list_project_assets()` and `count_project_assets()` in storage.py
- Preserves compatibility with bridge.chat() diff logic, thumbnail APIs, and propose_images

**Tests Added:**
- 4 new tests in `tests/test_advisor_tools.py` for project tagging:
  - `test_generate_image_with_active_project_tags_filename`: Project prefix added
  - `test_generate_image_without_active_project_no_prefix`: No prefix when no project
  - `test_generate_image_explicit_filename_ignores_project`: Explicit filename bypasses tagging
  - `test_generate_image_no_brand_no_project_check`: No project check without brand
- 3 new tests for `_generate_output_filename` helper:
  - `test_generate_output_filename_with_project`: Correct format with project
  - `test_generate_output_filename_without_project`: Correct format without project
  - `test_generate_output_filename_unique`: Unique hash per call

### Phase 4: Agent Tools ✅
**File**: `src/sip_videogen/advisor/tools.py`

Added four new agent tools for explicit product/project exploration:

**New Tools:**
- `list_products()`: List all products with names, slugs, attribute counts, and primary images
- `list_projects()`: List all projects with status, asset counts, and active project marker
- `get_product_detail(product_slug)`: Get detailed product info as formatted markdown
- `get_project_detail(project_slug)`: Get detailed project info including instructions and assets

**Implementation Details:**
- Implementation functions (`_impl_*`) for testing, wrapped with `@function_tool`
- Tools return formatted markdown for agent consumption
- Active project shown with "★ ACTIVE" marker in list_projects
- Descriptions truncated to 100 chars in list view
- Assets truncated to first 10 in get_project_detail

**Tests Added:**
- 17 new tests in `tests/test_advisor_tools.py`:
  - TestListProducts: 4 tests (no brand, empty, with products, truncation)
  - TestListProjects: 4 tests (no brand, empty, with projects, active marker)
  - TestGetProductDetail: 3 tests (no brand, not found, formatted output)
  - TestGetProjectDetail: 6 tests (no brand, not found, formatted output, no instructions, inactive, truncation)

### Phase 5: Bridge API ✅
**File**: `src/sip_videogen/studio/bridge.py`

Added comprehensive Bridge API for products and projects:

**Product Methods:**
- `get_products(brand_slug)` / `get_product(product_slug)`: List and retrieve products
- `create_product(name, description, images, attributes)`: Create new product with optional images
- `update_product(product_slug, name, description, attributes)`: Update existing product
- `delete_product(product_slug)`: Delete product and all its files
- `get_product_images(product_slug)`: List product images (brand-relative paths)
- `upload_product_image(product_slug, filename, data_base64)`: Upload image to product
- `delete_product_image(product_slug, filename)`: Delete product image
- `set_primary_product_image(product_slug, filename)`: Set primary image for product
- `get_product_image_thumbnail(path)`: Get thumbnail for product image (base64 data URL)
- `get_product_image_full(path)`: Get full-resolution product image (base64 data URL)

**Project Methods:**
- `get_projects(brand_slug)` / `get_project(project_slug)`: List and retrieve projects
- `create_project(name, instructions)`: Create new project
- `update_project(project_slug, name, instructions, status)`: Update project
- `delete_project(project_slug)`: Delete project (keeps generated assets)
- `set_active_project(project_slug)` / `get_active_project()`: Active project management
- `get_project_assets(project_slug)`: List assets generated for project

**Chat Integration:**
- Updated `chat()` method signature to accept:
  - `project_slug`: Sets active project if provided, otherwise uses persisted
  - `attached_products`: List of product slugs for context injection
- Context passed to advisor's `chat_with_metadata()` for per-turn injection

**Key Implementation Details:**
- All methods return `BridgeResponse` format
- Product images support dedicated thumbnail/full APIs (paths must start with `products/`)
- Project assets returned as assets-relative paths (`generated/...`)
- No server-side state for attached products (frontend owns this state)
- Slug generation from name using regex normalization

### Phase 6: Frontend Types & Contexts ✅
**Files**: `src/sip_videogen/studio/frontend/src/lib/bridge.ts`, `src/sip_videogen/studio/frontend/src/context/ProductContext.tsx`, `src/sip_videogen/studio/frontend/src/context/ProjectContext.tsx`, `src/sip_videogen/studio/frontend/src/hooks/useChat.ts`

Added TypeScript interfaces and React contexts for products and projects:

**TypeScript Interfaces (bridge.ts):**
- `ProductAttribute`: Key-value-category triplet for product properties
- `ProductEntry`: L0 summary for product list display
- `ProductFull`: L1 complete product data with images and attributes
- `ProjectEntry`: L0 summary for project list display (with status)
- `ProjectFull`: L1 complete project data with instructions and assets
- `ChatContext`: Context object for passing `project_slug` and `attached_products` to chat

**Bridge Wrapper Functions:**
- Product CRUD: `getProducts`, `getProduct`, `createProduct`, `updateProduct`, `deleteProduct`
- Product images: `getProductImages`, `uploadProductImage`, `deleteProductImage`, `setPrimaryProductImage`, `getProductImageThumbnail`, `getProductImageFull`
- Project CRUD: `getProjects`, `getProject`, `createProject`, `updateProject`, `deleteProject`
- Project state: `setActiveProject`, `getActiveProject`, `getProjectAssets`
- Updated `chat()` to accept optional `ChatContext` parameter

**ProductContext (ProductContext.tsx):**
- `products`: List of ProductEntry from backend
- `attachedProducts`: Frontend-only state for products attached to chat (not persisted)
- `attachProduct(slug)` / `detachProduct(slug)` / `clearAttachments()`: Manage attachments
- `createProduct`, `updateProduct`, `deleteProduct`: CRUD operations
- `getProduct`, `getProductImages`, `uploadProductImage`, `deleteProductImage`, `setPrimaryProductImage`: Product detail operations

**ProjectContext (ProjectContext.tsx):**
- `projects`: List of ProjectEntry from backend
- `activeProject`: Persisted server-side via bridge.setActiveProject()
- `setActiveProject(slug | null)`: Set or clear active project
- `createProject`, `updateProject`, `deleteProject`: CRUD operations
- `getProject`, `getProjectAssets`: Project detail operations

**useChat Updates:**
- `sendMessage(content, context?)` now accepts optional `ChatContext`
- Passes context to `bridge.chat()` for per-turn injection

**Key Design Decisions:**
- `attachedProducts` is frontend-only state, passed with each chat() call (stateless API)
- `activeProject` is persisted server-side, loaded on context initialization
- Both contexts depend on `BrandContext` and refresh when brand changes
- Attachments cleared when brand changes
- Mock data provided for dev mode (not running in PyWebView)

## Remaining Tasks

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
- All 63 advisor tools tests pass: `python -m pytest tests/test_advisor_tools.py -v`
- Total: 269 tests for brands + advisor modules

## Commits
- `61e558a`: feat(models): Add Product and Project models for hierarchical memory system
- `9fe3b1f`: feat(storage): Add Product and Project storage layer functions
- `bd581b0`: feat(memory): Add Product and Project memory and context layer functions
- `c5410ab`: feat(advisor): Add per-turn context injection for products and projects
- `3ac807d`: feat(tools): Add product_slug parameter to generate_image for automatic product reference
- `2cc0285`: feat(tools): Add project asset tagging via filename prefix
- `ddf88b6`: feat(tools): Add product and project exploration tools for agent
- `94c8ea6`: feat(bridge): Add product and project API methods
- `715faff`: feat(frontend): Add Product and Project types and contexts
