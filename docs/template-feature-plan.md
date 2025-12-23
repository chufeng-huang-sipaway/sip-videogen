# Template Feature Plan (Layout Template)

## Overview
Add a new "Layout Template" feature that lets users attach a template in chat,
replace a single product slot, and control strictness with a "Strictly Follow"
toggle (default ON). Templates are analyzed once using Gemini Vision into a
structured JSON layout description and stored locally. Generation uses JSON
only (no template image as a reference input).

## Key Decisions (Confirmed)
- Single product slot only (v1).
- JSON includes geometry + semantic description.
- "Strictly Follow" toggle per chat (default ON), with per-template default as fallback.
- Use JSON only for generation (no template image reference in Gemini calls).

## Naming
- Internal name: "Layout Template" (code + data model).
- UI label: "Template" (short and user-friendly).

## UX Flows
### Create Template
1. User creates a template from 1-2 images.
2. App analyzes image(s) with Gemini Vision using a template JSON schema.
3. Template saved locally with images + analysis JSON.
4. Template appears in sidebar list for drag and drop.

### Use Template in Chat
1. User drags a template into chat.
2. Chat shows attached template card with "Strictly Follow" toggle (default ON).
3. User also attaches a product (existing flow).
4. Agent generates image:
   - Strict ON: replace product only, everything else identical.
   - Strict OFF: replace product, allow creative changes to other elements.

## Data Model
Add template models to `src/sip_videogen/brands/models.py`:
- `TemplateSummary` (L0)
- `TemplateFull` (L1)
- `TemplateAnalysis` (layout JSON)

Proposed fields:
```
TemplateSummary:
  slug, name, description, primary_image, created_at, updated_at
  default_strict: bool

TemplateFull:
  slug, name, description
  images: list[str]
  primary_image: str
  analysis: TemplateAnalysis
  default_strict: bool
  created_at, updated_at

TemplateAnalysis:
  version: "1.0"
  canvas: { width_px?, height_px?, aspect_ratio, background }
  message: { intent, audience?, key_claims? }
  style: { palette, lighting, mood, materials }
  elements: [
    {
      id, type, role,
      geometry: { x, y, w, h, rotation?, z_index? },
      appearance: { color?, texture?, typography?, effects? },
      content: { text?, image_desc?, icon_desc? },
      constraints: { locked?: bool, notes?: string }
    }
  ]
  product_slot: {
    id,
    geometry,
    appearance,
    interaction: { shadow, contact_surface, perspective }
  }
```

## Storage Layout
Under `~/.sip-videogen/brands/{brand}/templates/`:
```
templates/
  index.json
  {template-slug}/
    template.json
    template_full.json
    images/
      *.png
```

## Backend / Services
Add template storage + APIs mirroring product services.

### Storage
`src/sip_videogen/brands/storage.py`
- create/load/save/delete/list templates
- add/delete template images
- set primary template image

### Services + Bridge
`src/sip_videogen/studio/services/template_service.py`
`src/sip_videogen/studio/bridge.py`
`src/sip_videogen/studio/frontend/src/lib/bridge.ts`
- CRUD + image ops
- analyze template image(s) and store JSON

## Gemini Template Analysis
Add a new analyzer module:
`src/sip_videogen/advisor/template_analyzer.py`
- Use Gemini Vision with a JSON-only prompt for TemplateAnalysis.
- Support 1-2 images; if 2 images, ask for best-consensus layout.
- Cache analysis result in template_full.json.

## Agent Integration
### Chat Context
Extend `ChatContext` and per-turn context injection:
- `attached_templates`: list of { template_slug, strict }
- Inject template context in `HierarchicalContextBuilder`.

### Template Context Builder
Add to `src/sip_videogen/brands/context.py`:
- `TemplateContextBuilder` similar to ProductContextBuilder.
- Include layout JSON and strictness mode.

### Prompt Strategy
Add helper to convert TemplateAnalysis into prompt constraints:
`src/sip_videogen/advisor/template_prompt.py`
- Strict: enforce all elements locked except product slot.
- Loose: preserve message intent + key composition hints, allow variation.

### Generate Image Tooling
No template image reference is sent to Gemini.
- Agent uses template JSON to build a detailed prompt.
- Product remains a reference via `generate_image(product_slug=...)`.

## Frontend
### Sidebar
Add "Templates" section in sidebar (like Products).
`src/sip_videogen/studio/frontend/src/components/Sidebar/sections/TemplatesSection.tsx`

### Create/Edit Dialog
Dialogs similar to products with image upload + analyze.
`src/sip_videogen/studio/frontend/src/components/Sidebar/CreateTemplateDialog.tsx`
`src/sip_videogen/studio/frontend/src/components/Sidebar/EditTemplateDialog.tsx`

### Chat Attachment
`AttachedTemplates` component with "Strictly Follow" toggle (default ON).
- Toggle state stored in context and sent in `ChatContext`.

## Timeline
### Phase 0 (Now -> Dec 30)
- Data model + storage + index.
- Bridge/service CRUD.
- Frontend list + create/edit dialogs.

### Phase 1 (Dec 30 -> Jan 10)
- Gemini template analyzer + JSON schema.
- Persist analysis in template_full.json.
- Basic template detail view.

### Phase 2 (Jan 10 -> Jan 20)
- Chat context + attached templates.
- Strict toggle UI + context injection.
- Prompt helper for strict mode.

### Phase 3 (Jan 20 -> Jan 31)
- Loose mode prompt strategy + variation guidance.
- QA + tests + polish.

## Success Metrics
- Strict mode: consistently replaces product with minimal drift on other elements.
- Loose mode: user can create meaningful variations while preserving message intent.
- Template analysis runs once and is reusable without re-prompting.

## Open Questions
- None at this stage (decisions confirmed). If we want multi-slot support later,
  we should extend `elements` with multiple product slots and slot selectors.
