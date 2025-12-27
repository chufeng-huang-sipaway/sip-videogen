# PR Handoff: Gemini 3.0 Pro Prompting Enhancement + Workstation Drag-and-Drop

**Branch:** `img-prompt-flow-update`
**Last Updated:** 2025-12-26

## Context

### Problem
1. Our image generation prompting doesn't fully leverage Gemini 3.0 Pro ("Nano-Banana Pro") advanced capabilities
2. Users cannot drag images from Workstation to chat for editing workflows

### Solution Approach
1. Enhance the `image-prompt-engineering` skill with advanced prompting techniques
2. Add drag-and-drop from Workstation images to chat panel for seamless editing workflows

## Key Files to Focus On

**Critical files** (start here):
- `src/sip_videogen/advisor/skills/image_prompt_engineering/SKILL.md` - Primary skill file with prompting techniques
- `src/sip_videogen/advisor/prompts/advisor.md` - Agent behavior for edit detection + preservation principle

**Drag-and-drop files:**
- `src/sip_videogen/studio/frontend/src/context/DragContext.tsx` - **NEW** Shared drag state context (bypasses PyWebView/WebKit limitations)
- `src/sip_videogen/studio/frontend/src/components/Workstation/ImageDisplay.tsx` - Main image viewer (drag enabled + drag image thumbnail)
- `src/sip_videogen/studio/frontend/src/components/Workstation/ImageGrid.tsx` - Grid view (drag enabled + drag image thumbnail)
- `src/sip_videogen/studio/frontend/src/components/Workstation/ThumbnailStrip.tsx` - Thumbnail strip (drag enabled + drag image thumbnail)
- `src/sip_videogen/studio/frontend/src/components/Workstation/index.tsx` - Fixed `originalPath` mapping
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/index.tsx` - Drop handling via DragContext
- `src/sip_videogen/studio/frontend/src/App.tsx` - Wrapped with DragProvider
- `src/sip_videogen/studio/frontend/src/index.css` - Added `.is-dragging` CSS to prevent text selection

**Reference files:**
- `docs/IMPLEMENTATION_PLAN-gemini-prompting-v2.md` - Detailed task list with critical concerns
- `docs/SPEC-gemini-prompting-v2.md` - Technical specification with example content

## Progress Summary

### Completed

#### Workstation Drag-and-Drop Feature
- **DragContext**: Created shared React context to bypass PyWebView/WebKit drag event limitations
  - `DragContext.tsx` - Provides `dragData`, `setDragData`, `clearDrag` across components
  - Solves: Browser drag events don't propagate reliably between sibling components in WebKit
  - Adds `is-dragging` class to body during drag (enables CSS to prevent text selection)
  - Delayed cleanup via `dragend` listener (100ms delay lets drop handlers process first)
- **Drag Handlers**: Added `draggable` + `onDragStart` + `onDragEnd` to all Workstation image components
  - `ImageDisplay.tsx` - Main viewer with cursor-grab feedback + 80px drag image thumbnail
  - `ImageGrid.tsx` - Grid thumbnails with drag support + drag image thumbnail
  - `ThumbnailStrip.tsx` - Horizontal strip thumbnails + drag image thumbnail
  - All components: `onDragStart` sets context + dataTransfer, `onDragEnd` clears context
- **Drop Handling**: ChatPanel uses DragContext for reliable drop detection
  - `handleNativeDragOver` - Calls `preventDefault()` when `dragData` exists (enables drop)
  - `handleNativeDrop` - Checks `dragData` first (reliable), falls back to dataTransfer (for external files)
  - Shows overlay when `dragData !== null` (not relying on flaky browser drag events)
- **CSS**: Added `.is-dragging` styles to `index.css`
  - `user-select: none` prevents text selection during drag
  - `pointer-events: none` on images prevents interference
- **Bug Fix**: Fixed `originalPath` not being passed in batch creation
  - `Workstation/index.tsx` line 48 - Added `originalPath: img.originalPath`
  - `ChatPanel/index.tsx` line 54-61 - Added `originalPath: img.originalPath`
  - Root cause: Drag handler checks `if(path.startsWith('data:')) return` - without `originalPath`, it fell back to data URL and blocked drag
- **Preservation Principle**: Added explicit note to `advisor.md` Edit Mode Detection:
  > "PRESERVE EVERYTHING not explicitly mentioned. If user says 'change the background', keep subject, lighting, angle, pose, colors, and all other elements identical."

#### Gemini 3.0 Pro Prompting Enhancement
- **Task 10**: Added test cases document (docs/TEST-gemini-prompting-v2.md)
  - 10 test categories covering all new capabilities
  - Regression, texture, text rendering, iterative refinement, editing tests
  - Sketch/layout, dimensional translation, trigger keyword tests
  - End-to-end workflow integration tests
  - Validation checklist for PR merge
- **Task 1**: Added Texture & Material Details section to SKILL.md
  - New "Advanced Prompting Techniques" section with surface finish, material properties, imperfections guidance
  - 3 example prompts demonstrating texture-rich descriptions
  - Updated "Critical Do's" to include material textures emphasis
- **Task 2**: Added Text Rendering section to SKILL.md
  - 3-step approach: quote exact text, specify typography, describe placement
  - 3 example prompts demonstrating proper text quoting technique
  - Updated "Critical Do's" to emphasize quoted text with typography details
- **Task 3**: Added Iterative Refinement Workflow to SKILL.md and advisor.md
  - "Edit, Don't Re-roll" section with decision tree for refinement vs. fresh generation
  - Path conversion guidance (absolute -> brand-relative)
  - Scope limitation documented: single-reference flows only (Phase 1)
  - Added refinement detection rules to advisor.md with trigger phrases
  - Addresses Concern 1 (output as reference) and Concern 3 (path ergonomics)
- **Task 4**: Added Image Editing via Language to SKILL.md and advisor.md
  - validate_identity decision table for different edit types (remove bg, relight, colorize, style transfer)
  - 4 example prompts with correct flag usage
  - Edit Mode Detection section in advisor.md with specific trigger phrases
  - Addresses Concern 2 (validate_identity nuance) and Concern 3 (path ergonomics)
- **Task 5**: Added Sketch/Layout Control to SKILL.md and advisor.md
  - "Layout Control via Sketch/Wireframe" section with prompt pattern and examples
  - Deterministic detection rules in advisor.md (NO subjective "looks like sketch")
  - Decision tree: product_slug → Identity Flow; explicit layout keywords → Layout Flow; ambiguous → Ask
  - 3 examples: ad layout, UI mockup, floor plan to 3D interior
  - Addresses Concern 5 (deterministic detection, not subjective)
- **Task 6**: Added Dimensional Translation (2D↔3D) to SKILL.md
  - "Dimensional Translation (2D ↔ 3D)" section with patterns for both directions
  - 2D→3D: label designs to bottle mockups, blueprints to 3D renders
  - 3D→2D: renders to flat vector illustrations
  - Guidance on merging product attributes (colors, typography, textures from brand)
  - 2 example prompts demonstrating dimensional conversion
- **Task 7**: Expanded Trigger Keywords in SKILL.md frontmatter
  - Added infographic triggers: infographic, diagram, chart
  - Added layout triggers: sketch layout, wireframe, layout mockup, blueprint, schematic
  - Added editing triggers using SPECIFIC phrases: remove background, colorize image/photo, enhance image, edit image/photo, restore photo/image, cleanup image, relight photo/image
  - Added dimensional triggers: 3D render, 3D mockup, 2D to 3D, 3D to 2D
  - Organized triggers with category comments for maintainability
  - Addresses Concern 4 (specific phrases to avoid false positives on non-image tasks)
- **Task 8**: Updated Critical Do's/Don'ts section in SKILL.md
  - Added DO: use reference_image for edits (previous output as reference + modified prompt)
  - Added DO: prefer iterative refinement when image is 80% correct
  - Added DO: "Following this sketch exactly" for layout references
  - Added DON'T: re-roll when refinement works
  - Added DON'T: forget path conversion (absolute → brand-relative)
  - Reinforces new advanced techniques in quick-reference checklist
- **Task 9**: Added Prompt Templates section to SKILL.md
  - Product Hero Shot template with texture/material emphasis and filled example
  - Infographic Layout template with text quoting pattern and filled example
  - Image Edit template for modification workflows and filled example
  - Sketch to Final template for layout-to-polished conversion and filled example
  - 2D to 3D Conversion template for dimensional translation and filled example
  - All templates include structure with bracketed placeholders plus filled examples

### In Progress / Next Steps
- **Phase 1 Complete** - All 10 tasks finished
- **Phase 2 (Future)**: Code enhancements (Tasks 11-12) - combined output+product refs, attachment-based skill gating

### Known Issues / Unresolved
- ~~Tasks 5, 7 have critical concerns documented in implementation plan that MUST be addressed~~ (RESOLVED)
- ~~Path conversion (absolute to brand-relative) needed for iterative refinement~~ (RESOLVED in Task 3)
- ~~validate_identity nuance for edit operations~~ (RESOLVED in Task 4)
- ~~Deterministic sketch detection (no subjective guessing)~~ (RESOLVED in Task 5)
- ~~Trigger keywords must use specific phrases to avoid firing on non-image tasks~~ (RESOLVED in Task 7)
- No blocking issues - Phase 1 ready for testing

## Testing Status

**What's been tested:**
- Task 1-10 changes verified in SKILL.md and advisor.md structure
- Drag-and-drop code implementation verified (DragContext, handlers, thumbnails)
- Build passes (`npm run build` succeeds)

**What still needs testing:**
- Drag-and-drop end-to-end: Drag image from Workstation → Chat should attach as reference
- Verify drag thumbnail appears attached to cursor during drag
- Verify drop overlay appears/disappears correctly
- Drag-and-drop: Type "change the background to marble" → Agent should preserve subject
- Full end-to-end image generation with new prompting techniques (manual)
- Execute test cases from docs/TEST-gemini-prompting-v2.md

## Notes for Next Developer

**Phase 1 complete + Drag-and-drop implemented with DragContext.**

**Architecture note on drag-and-drop:**
PyWebView/WebKit has limitations with browser drag events between sibling components. We bypass this using a shared React context (`DragContext`):
1. Drag source sets `dragData` in context on `dragStart`
2. ChatPanel reads `dragData` to show overlay and handle drop
3. Context clears automatically via delayed `dragend` listener (100ms delay lets drop handler process first)

**Quick test for drag-and-drop:**
1. Open Workstation with generated images
2. Drag any image (main viewer, grid, or thumbnails) to chat panel
3. Should see: 80px thumbnail attached to cursor, drop overlay in chat
4. Drop should attach image as reference with file path
5. Type "change the background to marble" → Agent should preserve subject exactly

**If drag-and-drop breaks:**
- Check `DragContext.tsx` - the delayed cleanup (100ms) is critical
- Check `handleNativeDragOver` in ChatPanel - must call `preventDefault()` when `dragData` exists
- Check `handleNativeDrop` - must check `dragData` before it's cleared

**Reference documents:**
- `docs/IMPLEMENTATION_PLAN-gemini-prompting-v2.md` - Gemini prompting task list
- `docs/TEST-gemini-prompting-v2.md` - Test cases for validation

**Next steps:**
1. Test drag-and-drop works end-to-end (thumbnail + overlay + attachment)
2. Execute test cases from TEST-gemini-prompting-v2.md
3. Consider Phase 2 code enhancements (Tasks 11-12) if needed

## Handoff History
- 2025-12-26 - Initial handoff created after Task 1 completion
- 2025-12-26 - Updated after Tasks 2-10 completion (Gemini prompting - Phase 1 complete)
- 2025-12-26 - Added Workstation drag-and-drop feature (ImageDisplay, ImageGrid, ThumbnailStrip + originalPath bug fix)
- 2025-12-26 - Refactored drag-and-drop to use DragContext (bypasses PyWebView/WebKit limitations, adds drag thumbnails, prevents selection)

---
*This is a local handoff document. Not tracked in git.*
