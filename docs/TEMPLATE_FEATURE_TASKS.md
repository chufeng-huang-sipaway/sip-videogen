# Layout Template Feature - Developer Tasks (Revised)

## Introduction
This feature adds reusable layout templates so users can start from proven visuals instead of prompting from scratch. Template images are analyzed once into structured JSON (geometry + semantics) and stored locally. In chat, attaching a template with the "Strictly Follow" toggle lets users either preserve the layout exactly (replace product only) or allow controlled variation. This reduces time-to-output while keeping brand visuals consistent.

## Phase 0: Data Model + Storage + CRUD (Target: Dec 30)

**Sub-Milestones (Parallelizable):**
- 0A Models + storage scaffolding (tasks 1-2)
- 0B Service + bridge + frontend types (tasks 3-5) depends on 0A
- 0C Template context + sidebar list + drag payload (tasks 6-7) depends on 0B
- 0D Create/Edit dialogs + image upload UX (task 8) depends on 0B

### - [x] 1. Data Models
**File:** `src/sip_videogen/brands/models.py`

- Add `TemplateAnalysis` Pydantic model with fields:
  - `version: str` ("1.0")
  - `canvas: CanvasSpec` (aspect_ratio, background, optional width/height)
  - `message: MessageSpec` (intent, audience, key_claims)
  - `style: StyleSpec` (palette, lighting, mood, materials)
  - `elements: list[LayoutElement]` (id, type, role, geometry, appearance, content, constraints)
  - `product_slot: ProductSlot` (id, geometry, appearance, interaction)
- Add sub-models for schema validation:
  - `CanvasSpec`, `MessageSpec`, `StyleSpec`, `LayoutElement`, `GeometrySpec`,
    `AppearanceSpec`, `ContentSpec`, `ConstraintSpec`, `ProductSlot`, `InteractionSpec`
- Add `TemplateSummary` (L0) model: slug, name, description, primary_image, default_strict, created_at, updated_at
- Add `TemplateFull` (L1) model: all summary fields + images + analysis (nullable before analysis)
- Add `TemplateIndex` model for `index.json`

### - [x] 2. Storage Layer
**File:** `src/sip_videogen/brands/storage.py`

- Add `get_templates_dir`, `get_template_dir`, `get_template_index_path`
- Update `create_brand` to initialize `templates/` and `templates/index.json` (empty index)
- `create_template(brand_slug, template)` -> creates folder + initial JSON
- `load_template(brand_slug, template_slug)` -> returns TemplateFull
- `load_template_summary(brand_slug, template_slug)` -> returns TemplateSummary
- `save_template(brand_slug, template)` -> writes template.json + template_full.json
- `delete_template(brand_slug, template_slug)` -> removes folder + updates index
- `list_templates(brand_slug)` -> returns list[TemplateSummary]
- `list_template_images(brand_slug, template_slug)` -> returns list[str]
- `add_template_image(brand_slug, template_slug, filename, data)` -> saves to images/
- `delete_template_image(brand_slug, template_slug, filename)`
- `set_primary_template_image(brand_slug, template_slug, filename)`
- (Optional) `sync_template_index(brand_slug)` -> reconcile index.json with filesystem

### - [x] 3. Template Service
**File:** `src/sip_videogen/studio/services/template_service.py` (new)

- `TemplateService` class wrapping storage + analysis calls (use active brand like ProductService)
- `get_templates(brand_slug: str | None = None)` -> summaries
- `get_template(template_slug)` -> TemplateFull
- `create_template(name, description, images, default_strict)` -> save + analyze
- `update_template(template_slug, name?, description?, default_strict?)`
- `reanalyze_template(template_slug)` -> re-run Gemini analysis
- `get_template_images(template_slug)`
- `upload_template_image(template_slug, filename, data_base64)`
- `delete_template_image(template_slug, filename)`
- `set_primary_template_image(template_slug, filename)`
- `get_template_image_thumbnail(path)`
- `get_template_image_full(path)`

### - [x] 4. Bridge API
**File:** `src/sip_videogen/studio/bridge.py`

- Instantiate `TemplateService` in `StudioBridge.__init__`
- `get_templates(brand_slug: str | None = None)` -> list summaries
- `get_template(template_slug)` -> full template
- `create_template(name, description, images, default_strict)` -> returns new template
- `update_template(template_slug, name?, description?, default_strict?)`
- `delete_template(template_slug)`
- `get_template_images(template_slug)`
- `upload_template_image(template_slug, filename, data_base64)`
- `delete_template_image(template_slug, filename)`
- `set_primary_template_image(template_slug, filename)`
- `get_template_image_thumbnail(path)`
- `get_template_image_full(path)`

### - [x] 5. Frontend Bridge Types
**File:** `src/sip_videogen/studio/frontend/src/lib/bridge.ts`

- Add `TemplateSummary`, `TemplateFull`, and `TemplateAnalysis` TypeScript interfaces
- Add bridge function types: `getTemplates`, `getTemplate`, `createTemplate`, `updateTemplate`, `deleteTemplate`
- Add image ops: `getTemplateImages`, `uploadTemplateImage`, `deleteTemplateImage`, `setPrimaryTemplateImage`, `getTemplateImageThumbnail`, `getTemplateImageFull`
- Extend `ChatContext` type to include `attached_templates: AttachedTemplate[]`

### - [x] 6. Frontend: Template Context
**File:** `src/sip_videogen/studio/frontend/src/context/TemplateContext.tsx` (new)

- Provide list + CRUD wrappers (similar to ProductContext)
- Track attached templates with strict toggle: `attachedTemplates: { slug, strict }[]`
- Methods: `attachTemplate`, `detachTemplate`, `setTemplateStrictness`, `clearTemplateAttachments`

### - [x] 7. Frontend: Sidebar Templates Section
**File:** `src/sip_videogen/studio/frontend/src/components/Sidebar/sections/TemplatesSection.tsx` (new)

- Template list component (similar to ProductsSection)
- Display template cards with thumbnail + name
- Drag-and-drop support for attaching to chat
- "Add Template" button opens create dialog
- Add drag payload type `application/x-brand-template`
- Wire into `Sidebar/index.tsx` with new section

### - [ ] 8. Frontend: Create/Edit Dialogs
**Files:**
- `src/sip_videogen/studio/frontend/src/components/Sidebar/CreateTemplateDialog.tsx` (new)
- `src/sip_videogen/studio/frontend/src/components/Sidebar/EditTemplateDialog.tsx` (new)

- CreateTemplateDialog: name, description, default_strict toggle, image upload (1-2 images)
- EditTemplateDialog: edit name, description, default_strict, manage images
- Show loading state during Gemini analysis
- Display analysis summary after creation

### Phase 0 Definition of Done
- Template CRUD works on disk under `templates/` with index updates
- Template images upload/list/primary/thumbnail/full path operations work end-to-end
- Bridge endpoints and frontend types are wired and return data in dev app
- Sidebar list renders templates and drag payloads are emitted
- Create/Edit dialogs save metadata + images and tolerate `analysis: null` (pending)

---

## Phase 1: Template Analyzer (Target: Jan 10)

### - [ ] 9. Gemini Template Analyzer
**File:** `src/sip_videogen/advisor/template_analyzer.py` (new)

- `analyze_template(images: list[bytes | str]) -> TemplateAnalysis`
- Build Gemini Vision prompt with JSON schema for TemplateAnalysis
- Handle 1-2 images; if 2, request best-consensus layout
- Parse response into TemplateAnalysis model
- Add retry logic + error handling

### - [ ] 10. Integration with Template Service

- Wire `TemplateService.create_template` to call analyzer
- Store analysis result in `template_full.json`
- Add `reanalyze_template` to re-run analysis on demand

### - [ ] 11. Frontend: Template Detail View
**File:** `src/sip_videogen/studio/frontend/src/components/Sidebar/TemplateDetailView.tsx` (new)

- Show template images
- Display analysis summary (canvas, style, element count, product slot info)
- "Re-analyze" button
- Edit/delete actions

### Phase 1 Definition of Done
- Gemini analyzer returns valid `TemplateAnalysis` for 1-2 images
- Analysis persisted in `template_full.json` and returned by `get_template`
- Re-analyze updates stored analysis and UI summary
- Analyzer errors surfaced to UI without breaking template CRUD

---

## Phase 2: Chat Integration (Target: Jan 20)

### - [ ] 12. Chat Context Extension (Frontend + Bridge + Backend)
**Files:**
- `src/sip_videogen/studio/frontend/src/lib/bridge.ts`
- `src/sip_videogen/studio/frontend/src/hooks/useChat.ts`
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/index.tsx`
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/MessageList.tsx`
- `src/sip_videogen/studio/bridge.py`
- `src/sip_videogen/studio/services/chat_service.py`
- `src/sip_videogen/advisor/agent.py`

- Extend `ChatContext` with `attached_templates: AttachedTemplate[]`
- `AttachedTemplate = { template_slug: string, strict: boolean }`
- Update `bridge.chat(..., attached_templates)` signature
- Pass `attached_templates` through `ChatService` to `BrandAdvisor.chat_with_metadata`
- Store attached templates in message history and render in `MessageList`

### - [ ] 13. Template Context Builder
**File:** `src/sip_videogen/brands/context.py`

- `TemplateContextBuilder` class (similar to ProductContextBuilder)
- Build context string from TemplateAnalysis + strictness mode
- Inject into `HierarchicalContextBuilder`

### - [ ] 14. Template Prompt Helper
**File:** `src/sip_videogen/advisor/template_prompt.py` (new)

- `build_template_constraints(analysis: TemplateAnalysis, strict: bool) -> str`
- Strict mode: all elements locked except product_slot, enforce exact geometry/style
- Loose mode: preserve message intent + key composition, allow variation
- Used by `TemplateContextBuilder` to format constraints for the agent

### - [ ] 15. Agent Prompt Integration
**File:** `src/sip_videogen/advisor/prompts/advisor.md`

- Add template handling rules:
  - Strict ON: replace product only, everything else identical
  - Strict OFF: preserve message intent, allow variation
- Reminder: template JSON is the only template reference (no image reference)

### - [ ] 16. Frontend: Chat Template Attachment
**File:** `src/sip_videogen/studio/frontend/src/components/ChatPanel/AttachedTemplates.tsx` (new)

- Display attached template card in chat input area
- "Strictly Follow" toggle per attached template (default ON)
- Remove template button
- Store toggle state in chat context

### - [ ] 17. Frontend: Drag and Drop to Chat

- Enable dragging template from sidebar to chat area
- Add `application/x-brand-template` handling in `ChatPanel` native drop
- On drop, add to attached templates with default strict=ON (or template default)

### Phase 2 Definition of Done
- Attached template cards show in chat with Strictly Follow toggle (default ON)
- Chat payload includes `attached_templates` and is persisted in message history
- Backend passes template context into `BrandAdvisor` turn context
- Agent prompt includes strict/loose handling rules and uses JSON-only template info

---

## Phase 3: Polish + Testing (Target: Jan 31)

### - [ ] 18. Loose Mode Refinement

- Test and tune loose mode prompt for meaningful variations
- Add guidance hints for variation (e.g., "try different background", "vary composition slightly")

### - [ ] 19. Unit Tests
**File:** `tests/test_template_*.py` (new)

- Test TemplateAnalysis model validation
- Test storage CRUD operations
- Test template analyzer with mocked Gemini responses
- Test context builder output for strict/loose modes
- Test chat payload wiring for attached templates

### - [ ] 20. Integration Tests

- End-to-end: create template -> analyze -> attach to chat -> generate image
- Test strict mode produces consistent results
- Test loose mode produces variations

### - [ ] 21. UI Polish

- Loading states for analysis
- Error handling + user feedback
- Responsive layout for template cards
- Keyboard navigation in template list

### Phase 3 Definition of Done
- Unit tests for templates and context wiring pass
- Integration test covers create -> analyze -> attach -> generate
- Manual QA: strict mode preserves layout; loose mode produces acceptable variations
- UI polish complete with stable loading/error states

---

## File Summary

| Phase | New Files |
|-------|-----------|
| 0 | `services/template_service.py`, `context/TemplateContext.tsx`, `Sidebar/sections/TemplatesSection.tsx`, `CreateTemplateDialog.tsx`, `EditTemplateDialog.tsx` |
| 1 | `advisor/template_analyzer.py`, `Sidebar/TemplateDetailView.tsx` |
| 2 | `advisor/template_prompt.py`, `ChatPanel/AttachedTemplates.tsx` |
| 3 | `tests/test_template_*.py` |

## Notes for Developers

1. **Follow existing patterns**: Mirror the Products feature architecture (storage, service, bridge, frontend sections)
2. **No over-engineering**: Single product slot only for v1, multi-slot is future scope
3. **JSON-only generation**: Template image is NOT sent to Gemini during generation, only the analyzed JSON
4. **Default strict=ON**: Users expect exact reproduction by default; loose mode is opt-in
5. **Reuse components**: Leverage existing dialog, card, and list components from Products feature
