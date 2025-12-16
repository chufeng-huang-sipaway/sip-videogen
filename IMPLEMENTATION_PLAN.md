# Hierarchical Memory System for Brand Studio

## Overview

Add two new memory layers (Product and Project/Campaign) alongside the existing Brand Identity layer, and restructure the sidebar UI to organize content by memory scope instead of file system.

**Three Memory Layers:**
1. **Brand** (existing) - Brand identity, documents, assets, AI-generated memory
2. **Products** (new) - Individual product items with images + descriptions
3. **Projects/Campaigns** (new) - Campaign-specific instructions and generated assets

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Product descriptions | English only | User decision - defer i18n |
| Attached products state | **Frontend-only, passed with each chat() call** | Stateless API, no server state |
| Project context injection | **Per-turn prompt injection** (not system prompt) | System prompt built once at init; project/products are dynamic |
| Product image paths | **Brand-relative** (e.g., `products/night-cream/images/main.png`) | `_resolve_brand_path` only accepts brand-relative paths |
| Project asset output | **Keep under `assets/generated/`**, track project via metadata | Avoids breaking bridge.chat() diff, thumbnail APIs, propose_images |
| Deferred features | `visual_keywords`, `avoid_keywords` | Prove core value first |

---

## Storage Structure

```
~/.sip-videogen/brands/{brand-slug}/
├── identity.json              # Brand L0 (existing)
├── identity_full.json         # Brand L1 (existing)
├── memory.json                # AI memory (existing)
├── assets/                    # Brand assets (existing)
│   └── generated/             # ALL generated images (brand + project)
│       └── *.png              # Images include project_slug in metadata/filename
├── docs/                      # Brand docs (existing)
├── products/
│   ├── index.json             # ProductIndex
│   └── {product-slug}/
│       ├── product.json       # ProductSummary (L0)
│       ├── product_full.json  # ProductFull (L1)
│       └── images/            # Reference images
│           └── *.png          # Brand-relative path: products/{slug}/images/{file}.png
└── projects/
    ├── index.json             # ProjectIndex (includes active_project)
    └── {project-slug}/
        ├── project.json       # ProjectSummary (L0)
        └── project_full.json  # ProjectFull (L1)
        # NOTE: No assets folder - project images stored in assets/generated with metadata
```

**Project Asset Tracking:**
Generated images for a project are stored in `assets/generated/` (existing location) but include project membership:
- Option A: Filename prefix: `{project_slug}__{timestamp}_{hash}.png`
- Option B: Separate manifest: `projects/{slug}/assets.json` listing paths in `assets/generated/`

This preserves compatibility with:
- `bridge.chat()` diff logic (line 1045)
- Thumbnail/image APIs (line 728)
- `propose_images` normalization (line 631)

**Project Asset Listing Format (IMPORTANT):**
Whenever listing project assets (bridge/API/UI), return **assets-relative paths**
like `generated/<filename>.png` so existing frontend image loading works without changes.

---

## Implementation Phases

### Phase 1: Data Models
**File:** `src/sip_videogen/brands/models.py`
**Status:** Complete

Add new models following existing patterns:

```python
# Product Models
class ProductAttribute(BaseModel):
    key: str          # e.g., "dimensions", "material"
    value: str
    category: str     # "measurements", "texture", "use_case", etc.

class ProductSummary(BaseModel):  # L0
    slug: str
    name: str
    description: str        # English only (i18n deferred)
    primary_image: str      # Brand-relative path: products/{slug}/images/{file}.png
    attribute_count: int
    created_at: datetime
    updated_at: datetime

class ProductFull(BaseModel):  # L1
    slug: str
    name: str
    description: str        # English only
    images: List[str]       # Brand-relative paths
    primary_image: str      # Brand-relative path
    attributes: List[ProductAttribute]
    # DEFERRED: visual_keywords, avoid_keywords
    created_at: datetime
    updated_at: datetime

    def to_summary(self) -> ProductSummary: ...

class ProductIndex(BaseModel):
    version: str = "1.0"
    products: List[ProductSummary]

# Project Models
class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"

class ProjectSummary(BaseModel):  # L0
    slug: str
    name: str
    status: ProjectStatus
    asset_count: int        # Count from manifest or filename prefix search
    created_at: datetime
    updated_at: datetime

class ProjectFull(BaseModel):  # L1
    slug: str
    name: str
    status: ProjectStatus
    instructions: str  # Markdown - campaign rules/guidelines
    created_at: datetime
    updated_at: datetime

    def to_summary(self) -> ProjectSummary: ...

class ProjectIndex(BaseModel):
    version: str = "1.0"
    projects: List[ProjectSummary]
    active_project: str | None = None
```

**Success Criteria:**
- [x] All Pydantic models defined with proper Field descriptions
- [x] Models follow existing BrandSummary/BrandIdentityFull patterns
- [x] to_summary() methods work correctly
- [x] All image paths are brand-relative (not absolute, not product-relative)

---

### Phase 2: Storage Layer
**File:** `src/sip_videogen/brands/storage.py`
**Status:** Complete

Add CRUD functions following existing brand patterns:

**Product Functions:**
- `get_products_dir(brand_slug)` / `get_product_dir(brand_slug, product_slug)`
- `load_product_index(brand_slug)` / `save_product_index(brand_slug, index)`
- `create_product(brand_slug, product)` / `load_product(brand_slug, product_slug)`
- `save_product(brand_slug, product)` / `delete_product(brand_slug, product_slug)`
- `list_products(brand_slug)` / `list_product_images(brand_slug, product_slug)`
- `add_product_image(brand_slug, product_slug, filename, data)` -> returns brand-relative path
- `delete_product_image(brand_slug, product_slug, filename)`

**Project Functions:**
- `get_projects_dir(brand_slug)` / `get_project_dir(brand_slug, project_slug)`
- `load_project_index(brand_slug)` / `save_project_index(brand_slug, index)`
- `create_project(brand_slug, project)` / `load_project(brand_slug, project_slug)`
- `save_project(brand_slug, project)` / `delete_project(brand_slug, project_slug)`
- `list_projects(brand_slug)`
- `get_active_project(brand_slug)` / `set_active_project(brand_slug, project_slug)`
- `list_project_assets(brand_slug, project_slug)` -> searches `assets/generated/` by prefix or manifest
- `count_project_assets(brand_slug, project_slug)` -> for asset_count in summary

**Success Criteria:**
- [x] All CRUD functions implemented
- [x] Directory structure created correctly
- [x] Index files synced properly
- [x] All returned paths are brand-relative
- [x] Project asset listing works via prefix/manifest
- [x] Unit tests pass

---

### Phase 3: Memory & Context Layer
**Files:** `src/sip_videogen/brands/memory.py`, `src/sip_videogen/brands/context.py`
**Status:** Complete

**Memory Access (memory.py):**
- `get_product_summary(brand_slug, product_slug)`
- `get_product_detail(brand_slug, product_slug)` -> JSON string for agent
- `get_product_images_for_generation(brand_slug, product_slug)` -> list of brand-relative paths
- `get_project_summary(brand_slug, project_slug)`
- `get_project_instructions(brand_slug, project_slug)` -> markdown
- `get_project_detail(brand_slug, project_slug)` -> JSON string

**Context Builders (context.py):**
```python
class ProductContextBuilder:
    """Builds product context for agent prompts."""
    def __init__(self, brand_slug: str, product_slug: str): ...
    def build_context_section(self) -> str:
        """Returns formatted product info including brand-relative image paths."""

class ProjectContextBuilder:
    """Builds project context for agent prompts."""
    def __init__(self, brand_slug: str, project_slug: str): ...
    def build_context_section(self) -> str:
        """Returns project instructions markdown."""

class HierarchicalContextBuilder:
    """Combines brand, product, and project context for per-turn injection."""
    def __init__(self, brand_slug, product_slugs=None, project_slug=None): ...
    def build_turn_context(self) -> str:
        """Build context to prepend to user message each turn.

        Returns formatted string with:
        - Project instructions (if project active)
        - Attached product descriptions + image paths (if products attached)

        NOTE: Brand context is in system prompt (existing).
        This is ADDITIONAL context injected per-turn.
        """
```

**Success Criteria:**
- [x] Memory access functions return correct data
- [x] Context builders format output correctly
- [x] HierarchicalContextBuilder builds per-turn context (not system prompt)
- [x] All image paths in context are brand-relative

---

### Phase 3.5: Per-Turn Context Injection (CRITICAL)
**File:** `src/sip_videogen/advisor/agent.py`
**Status:** Complete

**Problem:** System prompt is built once at init (line ~144). Active project and attached products are dynamic - they can change mid-session. Cannot rebuild Agent each time.

**Solution:** Inject project+product context into the per-turn prompt (prepended to user message), not system prompt. This happens "before reasoning" without requiring tool calls.

**IMPORTANT (Skills + History):**
- Skill matching should run on the **raw user message** (no injected context), otherwise context text will skew skill selection.
- Conversation history should store the **raw user message**, not the augmented message, otherwise history balloons and repeats context every turn.

**Changes to `chat()` or `chat_with_metadata()` (around line 380):**
```python
def chat_with_metadata(
    self,
    user_message: str,
    # NEW: dynamic context passed each turn
    project_slug: str | None = None,
    attached_products: list[str] | None = None,
    # ... existing params ...
) -> ChatResult:
    """Chat with the advisor, injecting dynamic context per-turn."""

    raw_user_message = user_message

    # NEW: Build per-turn context
    turn_context = ""
    if project_slug or attached_products:
        builder = HierarchicalContextBuilder(
            brand_slug=self.brand_slug,
            product_slugs=attached_products,
            project_slug=project_slug,
        )
        turn_context = builder.build_turn_context()

    # NEW: Prepend context to user message
    if turn_context:
        augmented_message = f"""## Current Context

{turn_context}

---

## User Request

{raw_user_message}"""
    else:
        augmented_message = raw_user_message

    # Skill matching: use raw_user_message
    # LLM prompt: use augmented_message
    # History storage: store raw_user_message
    # ... existing chat logic ...
```

**Why Per-Turn, Not System Prompt:**
- System prompt is built once at `__init__`
- User can change active project mid-conversation
- User can attach/detach products between messages
- Rebuilding Agent object each time is expensive and loses conversation state

**Success Criteria:**
- [x] Project instructions injected when project is active
- [x] Attached product context injected when products attached
- [x] Context is prepended to user message, not added to system prompt
- [x] Agent does NOT need to call tools to get project/product context
- [x] Changing project/products mid-conversation works correctly
- [x] Skill matching uses raw user message (not augmented)
- [x] History stores raw user message (not augmented)

---

### Phase 3.6: Product Image Routing in generate_image (CRITICAL)
**File:** `src/sip_videogen/advisor/tools.py`
**Status:** Complete

**Problem:** Products have reference images but we need to wire them into `generate_image()`. The existing `reference_image` parameter uses `_resolve_brand_path` (line 40) which only accepts brand-relative paths.

**Solution:** Pass brand-relative product image path directly to `reference_image`. Do NOT resolve to absolute.

**Changes to `generate_image()` function (around line 96):**
```python
@function_tool
def generate_image(
    prompt: str,
    reference_image: str | None = None,  # Existing - brand-relative path
    product_slug: str | None = None,      # NEW: auto-load product's primary image
    validate_identity: bool = False,       # Existing
    # ...
) -> str:
    """Generate an image with optional product reference."""

    # NEW: If product_slug provided, use its primary image as reference
    if product_slug and not reference_image:
        brand_slug = get_active_brand()
        product = load_product(brand_slug, product_slug)
        if product and product.primary_image:
            # primary_image is already brand-relative (e.g., "products/night-cream/images/main.png")
            # Pass directly - _resolve_brand_path will handle it
            reference_image = product.primary_image
            # Enable identity validation for product consistency
            validate_identity = True

    # ... existing generation logic (reference_image goes through _resolve_brand_path) ...
```

**Path Flow:**
1. Product stored with `primary_image = "products/night-cream/images/main.png"` (brand-relative)
2. `generate_image(product_slug="night-cream")` loads product, gets `primary_image`
3. Pass to existing `reference_image` parameter
4. `_resolve_brand_path` (line 40) resolves to absolute for actual file access

**Success Criteria:**
- [x] `generate_image(product_slug="night-cream")` uses product's primary image
- [x] `validate_identity=True` auto-enabled when using product reference
- [x] Existing `reference_image` parameter still works
- [x] All paths remain brand-relative until `_resolve_brand_path` resolves them

---

### Phase 3.7: Project Asset Tagging (CRITICAL)
**File:** `src/sip_videogen/advisor/tools.py`
**Status:** Complete

**Problem:** We want to track which generated images belong to which project. But changing output location to `projects/{slug}/assets/generated/` breaks:
- `bridge.chat()` diff logic (line 1045) - only looks at `assets/generated/`
- Thumbnail/image APIs (line 728) - only reads under `assets/`
- `propose_images` normalization (line 631) - assumes `assets/` location

**Solution:** Keep all generated images in `assets/generated/` but tag with project membership.

**Option A - Filename Prefix (Recommended - simpler):**
```python
def _generate_output_filename(project_slug: str | None = None) -> str:
    """Generate filename with optional project prefix."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    hash_suffix = uuid.uuid4().hex[:8]

    if project_slug:
        # e.g., "christmas-campaign__20241215_143022_a1b2c3d4.png"
        return f"{project_slug}__{timestamp}_{hash_suffix}.png"
    else:
        # e.g., "20241215_143022_a1b2c3d4.png"
        return f"{timestamp}_{hash_suffix}.png"
```

**Changes to `generate_image()` output logic:**
```python
# Get active project for tagging
brand_slug = get_active_brand()
project_slug = get_active_project(brand_slug)

# Generate filename with project prefix
filename = _generate_output_filename(project_slug)

# Save to existing location (preserves all existing integrations)
output_path = get_brand_assets_dir(brand_slug) / "generated" / filename
```

**Project Asset Listing:**
```python
def list_project_assets(brand_slug: str, project_slug: str) -> list[str]:
    """List assets belonging to a project by filename prefix."""
    generated_dir = get_brand_assets_dir(brand_slug) / "generated"
    prefix = f"{project_slug}__"
    # Return assets-relative paths for UI compatibility (e.g., "generated/foo.png")
    return [f"generated/{f.name}" for f in generated_dir.glob(f"{prefix}*.png")]
```

**Success Criteria:**
- [x] Generated images saved to `assets/generated/` (existing location)
- [x] Project membership tracked via filename prefix
- [x] `bridge.chat()` diff continues to work unchanged
- [x] Thumbnail/image APIs continue to work unchanged
- [x] `list_project_assets()` can filter by project
- [x] Project `asset_count` calculated correctly

---

### Phase 4: Agent Tools
**File:** `src/sip_videogen/advisor/tools.py`
**Status:** Complete

Add new tools (simplified - per-turn injection handles most cases):

```python
@function_tool
def list_products() -> str:
    """List all products for the active brand."""

@function_tool
def list_projects() -> str:
    """List all projects for the active brand."""

@function_tool
def get_product_detail(product_slug: str) -> str:
    """Get detailed product info (for when agent needs more than injected context)."""

@function_tool
def get_project_detail(project_slug: str) -> str:
    """Get detailed project info (for when agent needs more than injected context)."""
```

**Note:** Context injection handles automatic loading. These tools are for explicit exploration.

**Success Criteria:**
- [x] Tools implemented and registered
- [x] Tools return brand-relative paths
- [x] Integration tests pass

---

### Phase 5: Bridge API
**File:** `src/sip_videogen/studio/bridge.py`
**Status:** Not Started

**Product Methods:**
- `get_products(brand_slug=None)` / `get_product(product_slug)`
- `create_product(name, description, images, attributes)`
- `update_product(product_slug, name=None, description=None, attributes=None)`
- `delete_product(product_slug)`
- `get_product_images(product_slug)` / `upload_product_image(product_slug, filename, data_base64)`
- `delete_product_image(product_slug, filename)` / `set_primary_product_image(product_slug, filename)`

**Project Methods:**
- `get_projects(brand_slug=None)` / `get_project(project_slug)`
- `create_project(name, instructions="")` / `update_project(project_slug, name=None, instructions=None, status=None)`
- `delete_project(project_slug)`
- `set_active_project(project_slug)` / `get_active_project()`
- `get_project_assets(project_slug)` -> uses filename prefix search

**Product Image Preview (CRITICAL for UI):**
Product images live under `products/...`, but existing thumbnail APIs only resolve inside `assets/`.
Add a dedicated thumbnail/full API for product images:
- `get_product_image_thumbnail(path)` where `path` is brand-relative and must start with `products/`
- `get_product_image_full(path)` where `path` is brand-relative and must start with `products/`

**Chat Method Update (CRITICAL):**
```python
def chat(
    self,
    message: str,
    attachments: list[dict] | None = None,
    # NEW: dynamic context passed each call
    project_slug: str | None = None,
    attached_products: list[str] | None = None,
) -> dict:
    """Chat with attached context.

    Project source of truth:
    - If project_slug is provided: set it as active at the start of the call
      (so both per-turn injection and generate_image tagging see the same project).
    - If omitted: use the persisted active project from storage.
    """
    active_brand_slug = self._get_active_slug()
    if project_slug is not None:
        set_active_project(active_brand_slug, project_slug)  # project_slug may be None to clear

    effective_project = project_slug or get_active_project(active_brand_slug)
    result = self._advisor.chat_with_metadata(
        user_message=message,
        project_slug=effective_project,
        attached_products=attached_products,
    )
```

**Removed Methods (stateless approach):**
- ~~`set_attached_products()`~~ - frontend passes with each chat() call
- ~~`get_attached_products()`~~ - frontend owns this state
- ~~`clear_chat_context()`~~ - frontend clears its own state

**Success Criteria:**
- [ ] All methods implemented
- [ ] Methods return BridgeResponse format
- [ ] `chat()` accepts `project_slug` and `attached_products` parameters
- [ ] No server-side state for attached products
- [ ] Error handling consistent with existing methods
- [ ] Product thumbnail API supports `products/...` paths
- [ ] `get_project_assets()` returns assets-relative paths (`generated/...`)

---

### Phase 6: Frontend Types & Contexts
**Status:** Not Started

**Files:**
- `src/sip_videogen/studio/frontend/src/lib/bridge.ts` - Add TypeScript interfaces
- `src/sip_videogen/studio/frontend/src/context/ProductContext.tsx` - New context
- `src/sip_videogen/studio/frontend/src/context/ProjectContext.tsx` - New context

```typescript
// Types
interface ProductEntry { slug: string; name: string; description: string; primary_image: string; attribute_count: number }
interface ProductFull { slug: string; name: string; description: string; images: string[]; primary_image: string; attributes: ProductAttribute[] }
interface ProjectEntry { slug: string; name: string; status: 'active'|'archived'; asset_count: number }
interface ProjectFull { slug: string; name: string; status: 'active'|'archived'; instructions: string }

// ProductContext - owns attached products state (frontend-only)
interface ProductContextType {
  products: ProductEntry[]
  attachedProducts: string[]  // Frontend-only state
  refresh(): Promise<void>
  attachProduct(slug: string): void
  detachProduct(slug: string): void
  clearAttachments(): void   // Called on New Chat
  createProduct(data: CreateProductInput): Promise<void>
  deleteProduct(slug: string): Promise<void>
}

// ProjectContext - activeProject persisted via bridge
interface ProjectContextType {
  projects: ProjectEntry[]
  activeProject: string | null  // Persisted server-side
  refresh(): Promise<void>
  setActiveProject(slug: string | null): Promise<void>
  createProject(name: string, instructions?: string): Promise<void>
  updateProjectInstructions(slug: string, instructions: string): Promise<void>
  deleteProject(slug: string): Promise<void>
}

// Updated bridge.chat() call
// Keep PyWebView call positional, wrap in TS for ergonomics:
// bridge.chat(message, attachments, { project_slug, attached_products })
interface ChatContext {
  project_slug?: string | null
  attached_products?: string[]
}
```

**State Ownership:**
- `attachedProducts`: Frontend-only, passed to `bridge.chat()` each call
- `activeProject`: Persisted via `bridge.set_active_project()`, loaded on startup

**Success Criteria:**
- [ ] TypeScript interfaces match Python models
- [ ] `attachedProducts` is frontend-only state
- [ ] `chat()` passes both `project_slug` and `attached_products` to bridge
- [ ] `clearAttachments()` called when New Chat clicked

---

### Phase 7: Sidebar Restructure
**Status:** Not Started

**Dependency:** Add `@radix-ui/react-accordion` to frontend dependencies.

**Files:**
- `src/sip_videogen/studio/frontend/src/components/Sidebar/index.tsx` - Restructure layout
- `src/sip_videogen/studio/frontend/src/components/Sidebar/sections/BrandSection.tsx` - New
- `src/sip_videogen/studio/frontend/src/components/Sidebar/sections/ProductsSection.tsx` - New
- `src/sip_videogen/studio/frontend/src/components/Sidebar/sections/ProjectsSection.tsx` - New
- `src/sip_videogen/studio/frontend/src/components/Sidebar/ProductCard.tsx` - New (draggable)
- `src/sip_videogen/studio/frontend/src/components/Sidebar/ProjectCard.tsx` - New

**New Sidebar Structure:**
```tsx
<aside>
  <BrandSelector />
  <BrandActions />
  <Separator />
  <ScrollArea>
    <Accordion type="multiple" defaultValue={["brand", "products", "projects"]}>
      <AccordionItem value="brand">
        <AccordionTrigger>Brand</AccordionTrigger>
        <AccordionContent>
          <BrandSection />  {/* Existing: docs, images, AI memory */}
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="products">
        <AccordionTrigger>Products</AccordionTrigger>
        <AccordionContent>
          <ProductsSection />  {/* Product list, drag-to-chat */}
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="projects">
        <AccordionTrigger>Projects</AccordionTrigger>
        <AccordionContent>
          <ProjectsSection />  {/* Project list, active selection */}
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  </ScrollArea>
</aside>
```

**Success Criteria:**
- [ ] `@radix-ui/react-accordion` added to package.json
- [ ] Sidebar organized by memory scope (not file type)
- [ ] Accordion sections expand/collapse
- [ ] Products draggable (reuse existing drag pattern from AssetTree)
- [ ] Projects show active state

---

### Phase 8: Chat Integration
**Status:** Not Started

**Files:**
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/AttachedProducts.tsx` - New
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/ProjectBanner.tsx` - New
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/index.tsx` - Modify
- `src/sip_videogen/studio/frontend/src/hooks/useChat.ts` - Modify

**Reuse Existing Drag Pipeline:**
```typescript
// Extend existing drag handler for products
const handleProductDrop = (productSlug: string) => {
  productContext.attachProduct(productSlug)
}
```

**Chat Call with Context:**
```typescript
const sendMessage = async (message: string) => {
  const result = await bridge.chat(message, attachments, {
    project_slug: projectContext.activeProject,
    attached_products: productContext.attachedProducts,
  })
  // ...
}
```

**New Chat Clears Attachments:**
```typescript
const handleNewChat = () => {
  clearMessages()
  productContext.clearAttachments()  // Clear frontend state
  // NOTE: activeProject is NOT cleared - user explicitly set it
}
```

**Success Criteria:**
- [ ] Attached products display above input (thumbnail + name + remove button)
- [ ] Project banner shows when project active (click to view instructions)
- [ ] Drag-drop reuses existing pipeline pattern
- [ ] `chat()` passes context parameters to bridge
- [ ] New Chat clears attached products but keeps active project
- [ ] Agent receives correct context (verified via chat)

---

## Agent Context Loading Rules (FINAL)

| Layer | When Loaded | How Loaded | Mandatory? |
|-------|-------------|------------|------------|
| Brand L0 Summary | Always | System prompt (at init) | Yes |
| Project Instructions | When project active | **Per-turn prompt injection** | Yes (not tool call) |
| Attached Products | When products attached | **Per-turn prompt injection** | Yes (not tool call) |
| Product Details | On-demand | Agent tool call | No |
| Project Details | On-demand | Agent tool call | No |

**Key Points:**
- Brand context: System prompt (built once at init)
- Project + Products: Per-turn injection (prepended to user message)
- Dynamic changes (project switch, product attach/detach) work without Agent rebuild

---

## Critical Files Summary

| File | Changes |
|------|---------|
| `src/sip_videogen/brands/models.py` | Add Product* and Project* models |
| `src/sip_videogen/brands/storage.py` | Add product/project CRUD, project asset listing by prefix |
| `src/sip_videogen/brands/memory.py` | Add product/project memory access |
| `src/sip_videogen/brands/context.py` | Add context builders with `build_turn_context()` |
| `src/sip_videogen/advisor/agent.py` | **CRITICAL:** Per-turn context injection in `chat_with_metadata()` |
| `src/sip_videogen/advisor/tools.py` | **CRITICAL:** Product image routing, project filename prefix tagging |
| `src/sip_videogen/studio/bridge.py` | Add product/project methods, update `chat()` signature |
| `src/sip_videogen/studio/frontend/src/lib/bridge.ts` | Add TypeScript types, update chat options |
| `src/sip_videogen/studio/frontend/src/context/ProductContext.tsx` | New context (owns attachedProducts state) |
| `src/sip_videogen/studio/frontend/src/context/ProjectContext.tsx` | New context |
| `src/sip_videogen/studio/frontend/src/components/Sidebar/index.tsx` | Restructure to accordion |
| `src/sip_videogen/studio/frontend/src/components/Sidebar/sections/*` | New section components |
| `src/sip_videogen/studio/frontend/src/components/ChatPanel/*` | Add product/project UI |
| `src/sip_videogen/studio/frontend/package.json` | Add `@radix-ui/react-accordion` |

---

## User Experience Summary

1. **Sidebar organized by memory scope**: Brand -> Products -> Projects (not by file type)
2. **Products**: Drag to chat to attach; primary image auto-used as reference in generation
3. **Projects**: Click to set active; instructions injected per-turn (mandatory)
4. **Flexibility**: Users can chat without selecting a project (general conversation)
5. **Visibility**: Users can view and update memory in each section
6. **New Chat**: Clears attached products (but keeps active project)

---

## Deferred Features

- `visual_keywords` / `avoid_keywords` on ProductFull
- Multi-language product descriptions (`descriptions: dict[lang, str]`)
- Complex sidebar editor dialogs (keep minimal for now)
- Separate project asset folders (currently using filename prefix for tracking)
