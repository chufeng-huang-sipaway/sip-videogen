# PR Guide: Layout Template Feature

## Overview
This PR implements the Layout Template feature for Brand Studio, allowing users to create reusable layout templates from proven visuals.

## Task List Reference
See `docs/TEMPLATE_FEATURE_TASKS.md` for the complete task breakdown.

## Progress

### Completed Tasks
- [x] **Task 1: Data Models** - Added Pydantic models in `src/sip_videogen/brands/models.py`
  - `TemplateAnalysis` with sub-models (CanvasSpec, MessageSpec, StyleSpec, LayoutElement, etc.)
  - `TemplateSummary` (L0 layer)
  - `TemplateFull` (L1 layer)
  - `TemplateIndex` for registry

- [x] **Task 2: Storage Layer** - Added template storage functions in `src/sip_videogen/brands/storage.py`
  - Path helpers: `get_templates_dir`, `get_template_dir`, `get_template_index_path`
  - Index ops: `load_template_index`, `save_template_index`
  - CRUD: `create_template`, `load_template`, `load_template_summary`, `save_template`, `delete_template`, `list_templates`
  - Image ops: `list_template_images`, `add_template_image`, `delete_template_image`, `set_primary_template_image`
  - Sync: `sync_template_index` for filesystem reconciliation
  - Updated `create_brand` to initialize `templates/` with empty index

- [x] **Task 3: Template Service** - Created `src/sip_videogen/studio/services/template_service.py`
  - `TemplateService` class wrapping storage + BridgeState pattern
  - CRUD: `get_templates`, `get_template`, `create_template`, `update_template`, `delete_template`
  - Image ops: `get_template_images`, `upload_template_image`, `delete_template_image`
  - `set_primary_template_image`, `get_template_image_thumbnail`, `get_template_image_full`
  - `reanalyze_template` placeholder (analyzer in Phase 1)
  - Exported from `services/__init__.py`

- [x] **Task 4: Bridge API** - Wired TemplateService to `src/sip_videogen/studio/bridge.py`
  - Imported and instantiated `TemplateService` in `StudioBridge.__init__`
  - Added bridge methods: `get_templates`, `get_template`, `create_template`, `update_template`, `delete_template`
  - Added image ops: `get_template_images`, `upload_template_image`, `delete_template_image`, `set_primary_template_image`
  - Added thumbnail/full ops: `get_template_image_thumbnail`, `get_template_image_full`

- [x] **Task 5: Frontend Bridge Types** - Added TypeScript interfaces in `src/sip_videogen/studio/frontend/src/lib/bridge.ts`
  - Added complete template type interfaces (TemplateAnalysis, TemplateSummary, TemplateFull)
  - Added sub-model interfaces (CanvasSpec, MessageSpec, StyleSpec, GeometrySpec, etc.)
  - Added AttachedTemplate interface for chat integration
  - Added PyWebViewAPI template method signatures (11 methods)
  - Added bridge wrapper functions for all template operations
  - Extended ChatContext with `attached_templates: AttachedTemplate[]`

- [x] **Task 6: Frontend Template Context** - Created `src/sip_videogen/studio/frontend/src/context/TemplateContext.tsx`
  - `TemplateProvider` component with state management (templates, attachedTemplates, isLoading, error)
  - CRUD wrappers: `createTemplate`, `updateTemplate`, `deleteTemplate`, `getTemplate`
  - Attachment methods: `attachTemplate`, `detachTemplate`, `setTemplateStrictness`, `clearTemplateAttachments`
  - Image ops: `getTemplateImages`, `uploadTemplateImage`, `deleteTemplateImage`, `setPrimaryTemplateImage`
  - Auto-refresh on brand change with mock data fallback for dev mode
  - Wired `TemplateProvider` into `main.tsx` provider hierarchy

- [x] **Task 7: Frontend Sidebar Templates Section** - Created `src/sip_videogen/studio/frontend/src/components/Sidebar/sections/TemplatesSection.tsx`
  - `TemplatesSection` component following ProductsSection pattern
  - `TemplateCard` with draggable support (`application/x-brand-template` payload)
  - `TemplateThumbnail` and `TemplatePreview` components for inline expansion
  - Context menu with attach/detach, strict toggle, edit, delete actions
  - Lock/Unlock icons indicating strict/loose mode for attached templates
  - Wired into `Sidebar/index.tsx` with Layout icon and accordion section

- [x] **Task 8: Frontend Create/Edit Dialogs** - Created `CreateTemplateDialog.tsx` and `EditTemplateDialog.tsx`
  - `CreateTemplateDialog`: name, description, default_strict toggle, image upload (1-2 images)
  - `EditTemplateDialog`: edit name, description, default_strict, manage images with primary selection
  - Custom switch toggle for "Strictly Follow by Default" setting
  - Show analysis summary in edit dialog when analysis exists
  - Loading states during template operations
  - Wired dialogs into `TemplatesSection.tsx`

- [x] **Task 9: Gemini Template Analyzer** - Created `src/sip_videogen/advisor/template_analyzer.py`
  - `analyze_template(images)` extracts layout specs using Gemini Vision API
  - Supports 1-2 images; multi-image mode finds consensus layout
  - Returns `TemplateAnalysis` with canvas, elements, style, product_slot
  - Tenacity retry logic (3 attempts with exponential backoff)
  - JSON parsing with markdown code fence handling

- [x] **Task 10: Integration with Template Service** - Wired analyzer to TemplateService
  - `create_template()` now auto-analyzes uploaded images
  - `reanalyze_template()` re-runs Gemini analysis on demand
  - Analysis stored in `template_full.json`
  - Added `reanalyze_template` bridge method and frontend wrapper

- [x] **Task 11: Frontend Template Detail View** - Created `src/sip_videogen/studio/frontend/src/components/Sidebar/TemplateDetailView.tsx`
  - Full template info display with collapsible sections
  - Shows template images with primary indicator
  - Analysis summary: Canvas, Message, Style, Elements, Product Slot
  - Re-analyze button to regenerate Gemini analysis
  - Edit/Delete action buttons
  - Modal overlay triggered via context menu "View Details"

- [x] **Task 12: Chat Context Extension** - Extended ChatContext with attached_templates
  - Frontend types already wired in `bridge.ts` with `AttachedTemplate` interface
  - `useChat.ts` stores attached templates in message history
  - `ChatPanel/index.tsx` passes templates via context to `sendMessage`
  - `bridge.py` accepts and forwards `attached_templates` to ChatService
  - `chat_service.py` passes templates to `BrandAdvisor.chat_with_metadata`
  - `MessageList.tsx` renders attached templates with Lock/Unlock icons

- [x] **Task 13: Template Context Builder** - Added `TemplateContextBuilder` in `src/sip_videogen/brands/context.py`
  - `TemplateContextBuilder` class builds context from TemplateAnalysis
  - Strict mode: exact layout constraints, preserve all elements
  - Loose mode: preserve intent, allow controlled variation
  - Integrated into `HierarchicalContextBuilder.build_turn_context()`
  - Supports multiple attached templates with per-template strictness

### Next Task
- [ ] **Task 14: Template Prompt Helper** - Create template_prompt.py with constraint builders

## Files Changed
- `src/sip_videogen/brands/models.py` - Added 170+ lines of template models
- `src/sip_videogen/brands/storage.py` - Added 300+ lines of template storage functions
- `src/sip_videogen/brands/context.py` - Added TemplateContextBuilder + HierarchicalContextBuilder integration
- `src/sip_videogen/studio/services/template_service.py` - TemplateService with analyzer integration (180+ lines)
- `src/sip_videogen/studio/services/__init__.py` - Export TemplateService
- `src/sip_videogen/studio/bridge.py` - Added template bridge methods (13 methods)
- `src/sip_videogen/studio/frontend/src/lib/bridge.ts` - Added 140+ lines of template TypeScript types
- `src/sip_videogen/studio/frontend/src/context/TemplateContext.tsx` - TemplateProvider with reanalyze (120 lines)
- `src/sip_videogen/studio/frontend/src/main.tsx` - Wired TemplateProvider
- `src/sip_videogen/studio/frontend/src/components/Sidebar/sections/TemplatesSection.tsx` - TemplatesSection with dialog wiring
- `src/sip_videogen/studio/frontend/src/components/Sidebar/index.tsx` - Added Templates accordion section
- `src/sip_videogen/studio/frontend/src/components/Sidebar/CreateTemplateDialog.tsx` - New CreateTemplateDialog (90+ lines)
- `src/sip_videogen/studio/frontend/src/components/Sidebar/EditTemplateDialog.tsx` - New EditTemplateDialog (130+ lines)
- `src/sip_videogen/advisor/template_analyzer.py` - New Gemini Vision analyzer (110+ lines)
- `src/sip_videogen/studio/frontend/src/components/Sidebar/TemplateDetailView.tsx` - New TemplateDetailView (160+ lines)
- `docs/TEMPLATE_FEATURE_TASKS.md` - Task list with tasks 1-13 marked complete

## Testing
```bash
source .venv/bin/activate
python3 -c "from sip_videogen.brands.models import TemplateAnalysis, TemplateSummary, TemplateFull, TemplateIndex; print('OK')"
python3 -c "from sip_videogen.brands.storage import get_templates_dir, create_template, load_template, list_templates; print('OK')"
python3 -c "from sip_videogen.brands.context import TemplateContextBuilder, build_template_context; print('OK')"
python3 -c "from sip_videogen.studio.services import TemplateService; print('OK')"
python3 -c "from sip_videogen.advisor.template_analyzer import analyze_template; print('OK')"
python3 -c "from sip_videogen.studio.bridge import StudioBridge; b = StudioBridge(); print('Template methods:', [m for m in dir(b) if 'template' in m.lower()])"
python -m pytest tests/test_models.py -v
```

## Branch
`creation-template`
