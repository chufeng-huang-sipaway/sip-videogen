# Workstation Feature - Implementation Tasks

## Background for Developers

### Why We're Building This

Brand Studio users spend 99% of their time after brand creation generating and curating images. They generate 50-100 images to find 3-5 keepers. Currently, users:
- Lose track of which images they want to keep
- Must use macOS Finder/Preview to compare images one by one
- Have no way to mark keepers vs drafts inside the app
- See large image previews cluttering the chat panel

We're building a **Workstation** - a dedicated middle panel for image review and curation, inspired by Cursor IDE's three-column layout.

### Architecture Overview

**Current Layout:**
```
┌─────────────┬────────────────────────────┐
│   Sidebar   │         ChatPanel          │
│   (280px)   │        (flexible)          │
└─────────────┴────────────────────────────┘
```

**New Layout:**
```
┌─────────────┬────────────────────────────┬──────────────┐
│   Sidebar   │        Workstation         │     Chat     │
│   (280px)   │       (flexible)           │   (320px)    │
└─────────────┴────────────────────────────┴──────────────┘
```

### Image Lifecycle

Every generated image follows this lifecycle:
```
Generated → Unsorted (appears in workstation)
              ├─ swipe right → Kept (organized in sidebar)
              └─ swipe left  → Trash (30-day recycle bin)
```

### Key Files You'll Work With

**Frontend (React + TypeScript):**
- `src/sip_videogen/studio/frontend/src/App.tsx` - Main layout
- `src/sip_videogen/studio/frontend/src/components/` - UI components
- `src/sip_videogen/studio/frontend/src/context/` - React contexts
- `src/sip_videogen/studio/frontend/src/lib/bridge.ts` - Python bridge API

**Backend (Python):**
- `src/sip_videogen/studio/bridge.py` - PyWebView bridge methods
- `src/sip_videogen/studio/services/` - Business logic services
- `~/.sip-videogen/brands/{slug}/` - Brand data storage

### How Frontend Talks to Backend

The frontend uses PyWebView's bridge pattern:
```typescript
// Frontend calls Python
const result = await window.pywebview.api.get_brands();
```
```python
# Python bridge method
class StudioBridge:
    def get_brands(self) -> list[dict]:
        return storage.list_brands()
```

### Status Tracking Design

We track image status in `~/.sip-videogen/brands/{slug}/image_status.json`:
```json
{
  "version": 1,
  "images": {
    "img_abc123": {
      "id": "img_abc123",
      "status": "unsorted",
      "originalPath": "/path/to/generated/hero.png",
      "currentPath": "/path/to/generated/hero.png",
      "keptAt": null,
      "trashedAt": null
    }
  }
}
```

- `originalPath` never changes (stable reference)
- `currentPath` updates when image moves between folders
- `keptAt` / `trashedAt` are stored as ISO 8601 strings in JSON
- UI always looks up images by `id`, not by path
- `image_status.json` is the canonical source of truth; folder scans are recovery/backfill only

---

## Task 1: Three-Column Layout Foundation

**Goal:** Restructure App.tsx from two columns to three columns.

**What to do:**
- Open `src/sip_videogen/studio/frontend/src/App.tsx`
- Change the flex layout from `[Sidebar | ChatPanel]` to `[Sidebar | Workstation | ChatPanel]`
- Sidebar stays at 280px fixed width
- ChatPanel becomes 320px fixed width
- Workstation takes remaining flexible space (flex-1)
- Create empty `Workstation/index.tsx` component with placeholder text "Workstation"

**Files to modify:**
- `src/sip_videogen/studio/frontend/src/App.tsx`
- Create `src/sip_videogen/studio/frontend/src/components/Workstation/index.tsx`

**How to verify:**
- Run the app with `./scripts/studio-demo.sh`
- You should see three columns: Sidebar on left, "Workstation" placeholder in middle, Chat on right
- Resize the window - Workstation should grow/shrink while Sidebar and Chat stay fixed width
- Existing sidebar functionality (brand selection, projects, etc.) still works

---

## Task 2: WorkstationContext Setup

**Goal:** Create React context to manage workstation state.

**What to do:**
- Create `src/sip_videogen/studio/frontend/src/context/WorkstationContext.tsx`
- Define the state interface:
  ```typescript
  interface GeneratedImage {
    id: string;
    path: string;
    prompt?: string;
    sourceTemplatePath?: string;
    timestamp: string;
  }

  interface WorkstationState {
    currentBatch: GeneratedImage[];
    selectedIndex: number;
    viewMode: 'single' | 'comparison';
    comparisonSource: string | null;
    unsortedImages: GeneratedImage[];
  }
  ```
- Provide actions: `setCurrentBatch`, `setSelectedIndex`, `setViewMode`, `addToUnsorted`, `removeFromUnsorted`
- Wrap the app with this provider in App.tsx

**Files to modify:**
- Create `src/sip_videogen/studio/frontend/src/context/WorkstationContext.tsx`
- Modify `src/sip_videogen/studio/frontend/src/App.tsx` to wrap with provider

**How to verify:**
- App still loads without errors
- Open React DevTools (if available) and verify WorkstationContext exists
- No console errors related to context

---

## Task 3: ImageDisplay Component

**Goal:** Create the main image viewer for the workstation.

**What to do:**
- Create `src/sip_videogen/studio/frontend/src/components/Workstation/ImageDisplay.tsx`
- Display the currently selected image from WorkstationContext
- Image should fill the available space while maintaining aspect ratio (object-contain)
- Center the image both horizontally and vertically
- Add subtle background color to distinguish from empty areas

**Files to create:**
- `src/sip_videogen/studio/frontend/src/components/Workstation/ImageDisplay.tsx`

**Modify:**
- `src/sip_videogen/studio/frontend/src/components/Workstation/index.tsx` to include ImageDisplay

**How to verify:**
- Hardcode a test image path in the context
- The image displays centered in the workstation area
- Image maintains aspect ratio (not stretched or distorted)

---

## Task 4: ThumbnailStrip Component

**Goal:** Create horizontal thumbnail navigation below the main image.

**What to do:**
- Create `src/sip_videogen/studio/frontend/src/components/Workstation/ThumbnailStrip.tsx`
- Display thumbnails for all images in `currentBatch`
- Highlight the currently selected thumbnail
- Click on thumbnail → updates `selectedIndex` in context
- Thumbnails should be small (e.g., 64x64px) with slight padding
- Horizontal scrolling if thumbnails overflow

**Files to create:**
- `src/sip_videogen/studio/frontend/src/components/Workstation/ThumbnailStrip.tsx`

**Modify:**
- `src/sip_videogen/studio/frontend/src/components/Workstation/index.tsx` to include ThumbnailStrip

**How to verify:**
- Add 5-10 test images to the context
- Thumbnails appear in a horizontal row below the main image
- Clicking a thumbnail changes the main image
- Selected thumbnail has visible highlight (border or background)
- Horizontal scroll works when thumbnails overflow

---

## Task 5: Backend Image Status Service

**Goal:** Create Python service to track image lifecycle status.

**What to do:**
- Create `src/sip_videogen/studio/services/image_status.py`
- Implement `ImageStatusService` class with methods:
  - `get_status(brand_slug: str, image_id: str) -> dict`
  - `set_status(brand_slug: str, image_id: str, status: str) -> None`
  - `list_by_status(brand_slug: str, status: str) -> list[dict]`
  - `register_image(brand_slug: str, image_path: str) -> str` (generates ID, creates entry)
  - `update_path(brand_slug: str, image_id: str, new_path: str) -> None`
- Read/write to `~/.sip-videogen/brands/{slug}/image_status.json`
- Use atomic writes (write to temp file, then rename) to prevent corruption
- Include `version: 1` in JSON schema for future migrations
- Store `originalPath` + `currentPath` on register
- When status changes, set `keptAt` / `trashedAt` as ISO 8601 strings and clear the other
- Treat `image_status.json` as the source of truth; folder scans only for recovery/backfill

**Files to create:**
- `src/sip_videogen/studio/services/image_status.py`

**How to verify:**
- Write unit tests in `tests/test_image_status.py`
- Test: register new image creates entry with status "unsorted"
- Test: set_status changes status correctly
- Test: list_by_status filters correctly
- Test: atomic write doesn't corrupt file on failure
- Test: kept/trashed timestamps are ISO strings and `currentPath` updates on move

---

## Task 6: Bridge Methods for Image Status

**Goal:** Expose image status operations to the frontend.

**What to do:**
- Add new methods to `src/sip_videogen/studio/bridge.py`:
  - `get_unsorted_images(brand_slug: str) -> list[dict]`
  - `get_images_by_status(brand_slug: str, status: str) -> list[dict]`
  - `mark_image_kept(brand_slug: str, image_id: str) -> dict`
  - `mark_image_trashed(brand_slug: str, image_id: str) -> dict`
  - `unkeep_image(brand_slug: str, image_id: str) -> dict`
  - `restore_image(brand_slug: str, image_id: str) -> dict`
  - `empty_trash(brand_slug: str) -> dict`
  - `register_image(brand_slug: str, image_path: str) -> dict`
  - `register_generated_images(brand_slug: str, images: list[dict]) -> list[dict]`
  - `cancel_generation(brand_slug: str) -> dict`
- Each method should:
  - Call ImageStatusService
  - Move files to appropriate folder (kept/, trash/)
  - Return updated status
  - Update `currentPath` and set/clear `keptAt` / `trashedAt`
- Add corresponding TypeScript types in `bridge.ts`

**Files to modify:**
- `src/sip_videogen/studio/bridge.py`
- `src/sip_videogen/studio/frontend/src/lib/bridge.ts`

**How to verify:**
- Call `window.pywebview.api.get_unsorted_images("test-brand")` from browser console
- Returns list of unsorted images (or empty list)
- Call `mark_image_kept` and verify file moves to `kept/` folder
- Verify `image_status.json` updates correctly

---

## Task 7: Wire Generation Results to Workstation

**Goal:** When images are generated, display them in the workstation.

**What to do:**
- Find where image generation results are currently handled (likely in ChatPanel or a hook)
- After generation completes:
  1. Register each image via bridge (`register_image` or `register_generated_images`) to get IDs
  2. Push images to `WorkstationContext.currentBatch`
  3. Set `selectedIndex` to 0 (show first image)
- Images should auto-appear in workstation immediately after generation
- IDs should be generated in the backend, not in the frontend

**Files to modify:**
- Investigate current generation flow (start from ChatPanel message handling)
- Modify generation result handler to update WorkstationContext
- Update backend generation flow or bridge to return IDs + paths in one call

**How to verify:**
- Generate images using the chat
- Images immediately appear in the workstation
- Thumbnails show all generated images
- First image is selected by default

---

## Task 8: SwipeContainer Component

**Goal:** Add swipe gesture support for keep/trash curation.

**What to do:**
- Create `src/sip_videogen/studio/frontend/src/components/Workstation/SwipeContainer.tsx`
- Wrap ImageDisplay with SwipeContainer
- Detect horizontal swipe gestures (mouse drag or trackpad)
- Visual feedback: image tilts slightly in swipe direction
- Threshold: 100px horizontal movement triggers action
- If below threshold, snap back to center
- Swipe right → call `mark_image_kept()` via bridge
- Swipe left → call `mark_image_trashed()` via bridge
- After action, remove image from batch and auto-advance to next

**Libraries to consider:**
- Could use vanilla JS with touch/mouse events
- Or a gesture library like `@use-gesture/react` if already in project

**Files to create:**
- `src/sip_videogen/studio/frontend/src/components/Workstation/SwipeContainer.tsx`

**How to verify:**
- Drag image right past threshold → image disappears, file moves to kept/
- Drag image left past threshold → image disappears, file moves to trash/
- Drag but release before threshold → image snaps back
- Visual tilt effect visible during drag
- Next image auto-displays after swipe

---

## Task 9: Sidebar Kept Section

**Goal:** Show kept images in the sidebar.

**What to do:**
- Add "Kept" section to Sidebar (below existing sections)
- Fetch kept images using `get_images_by_status(brand_slug, "kept")`
- Display as thumbnails or list items
- Click on kept image → opens in workstation
- Provide "Unkeep" action (context menu or button) → calls `unkeep_image` and returns to unsorted
- Add small trash icon in sidebar footer for trash access

**Files to modify:**
- `src/sip_videogen/studio/frontend/src/components/Sidebar/index.tsx`
- May need new sub-component for kept images section

**How to verify:**
- After swiping right on images, they appear in Sidebar "Kept" section
- Clicking a kept image opens it in workstation
- Trash icon visible in sidebar footer

---

## Task 10: Empty State Component

**Goal:** Show helpful message when workstation has no images.

**What to do:**
- Create `src/sip_videogen/studio/frontend/src/components/Workstation/EmptyState.tsx`
- Display when `currentBatch` is empty
- Centered message: "No images to review"
- Subtitle: "Generate images using the chat, or select from sidebar"
- Clean, minimal design matching app style

**Files to create:**
- `src/sip_videogen/studio/frontend/src/components/Workstation/EmptyState.tsx`

**Modify:**
- `src/sip_videogen/studio/frontend/src/components/Workstation/index.tsx` to show EmptyState when appropriate

**How to verify:**
- When no images in batch, empty state displays
- After curating all images, empty state appears
- Text is centered and readable

---

## Task 11: ComparisonView Component

**Goal:** Enable side-by-side comparison of generated vs source image.

**What to do:**
- Create `src/sip_videogen/studio/frontend/src/components/Workstation/ComparisonView.tsx`
- Add "Compare" toggle button in workstation header
- When enabled, split view 50/50 horizontally
- Left side: current generated image
- Right side: source template/product image (from generation metadata)
- Labels above each: "Generated" | "Original"
- If source missing, show placeholder with "Source not available"
- Toggle off returns to single image view

**Files to create:**
- `src/sip_videogen/studio/frontend/src/components/Workstation/ComparisonView.tsx`

**Modify:**
- `src/sip_videogen/studio/frontend/src/components/Workstation/index.tsx` to include toggle and ComparisonView

**How to verify:**
- Toggle button visible in workstation header
- Click toggle → view splits 50/50
- Both images display correctly
- Labels visible above each image
- Toggle off returns to single view

---

## Task 12: ContextPanel Component

**Goal:** Show image metadata (prompt, source, timestamp).

**What to do:**
- Create `src/sip_videogen/studio/frontend/src/components/Workstation/ContextPanel.tsx`
- Collapsed by default (just an icon button)
- Click to expand panel showing:
  - Prompt used to generate
  - Product/template name if available
  - Timestamp of generation
- "Copy prompt" button to copy prompt text
- Panel should not obstruct main image view (overlay or sidebar)

**Files to create:**
- `src/sip_videogen/studio/frontend/src/components/Workstation/ContextPanel.tsx`

**Modify:**
- `src/sip_videogen/studio/frontend/src/components/Workstation/index.tsx` to include ContextPanel

**How to verify:**
- Icon button visible (e.g., info icon)
- Click expands panel with metadata
- Prompt, source, timestamp displayed correctly
- Copy button copies prompt to clipboard
- Panel can be collapsed again

---

## Task 13: Chat Panel Compact Mode

**Goal:** Make chat panel narrower with smaller image thumbnails.

**What to do:**
- Modify `src/sip_videogen/studio/frontend/src/components/ChatPanel/index.tsx`:
  - Set fixed width (320px)
  - Remove large inline image previews
- Modify `ChatImageGallery.tsx` (or equivalent):
  - Show tiny thumbnails (e.g., 48x48px)
  - Click on thumbnail → opens image in workstation
  - Display compact confirmation: "Generated 3 images" instead of full gallery

**Files to modify:**
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/index.tsx`
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/ChatImageGallery.tsx`

**How to verify:**
- Chat panel is narrower (320px)
- Generated images show as tiny thumbnails
- Clicking thumbnail opens image in workstation (WorkstationContext updates)
- No large image previews in chat

---

## Task 14: Input Lock During Generation

**Goal:** Disable chat input while generation is in progress.

**What to do:**
- Add `isGenerating` state to track generation status
- When generation starts → disable input field and submit button
- Show visual indicator (e.g., spinner, "Generating..." text)
- Add "Cancel" button to abort generation
- "Cancel" calls `cancel_generation` via bridge and then unlocks input
- When generation completes (success or failure) → unlock input
- Handle app crash/restart: ensure input is unlocked on relaunch

**Files to modify:**
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/MessageInput.tsx` (or equivalent)
- May need to modify context or hooks tracking generation state

**How to verify:**
- Start generation → input becomes disabled
- "Cancel" button appears during generation
- Generation completes → input unlocks
- Generation fails → input unlocks
- Restart app during generation → input is unlocked on relaunch

---

## Task 15: Export Actions

**Goal:** Enable users to copy, drag, or share images.

**What to do:**
- Create `src/sip_videogen/studio/frontend/src/components/Workstation/ExportActions.tsx`
- Add action buttons (visible on hover or always visible):
  - Copy to clipboard
  - Share (macOS share sheet)
- Enable drag-out: user can drag image to Finder or other apps
- Right-click context menu with same options

**macOS-specific:**
- Clipboard: use bridge to copy file to system clipboard
- Share: use bridge to invoke NSShareService
- Drag: implement drag with file URL

**Files to create:**
- `src/sip_videogen/studio/frontend/src/components/Workstation/ExportActions.tsx`

**Files to modify:**
- `src/sip_videogen/studio/bridge.py` - add `copy_to_clipboard()`, `share_image()` methods
- `src/sip_videogen/studio/frontend/src/lib/bridge.ts` - add TypeScript types

**How to verify:**
- Copy button copies image to clipboard (paste in Preview works)
- Share button opens macOS share sheet
- Can drag image out to Finder or other apps
- Right-click shows context menu

---

## Task 16: Trash Management UI

**Goal:** Allow users to view and manage trashed images.

**What to do:**
- Add trash icon in sidebar footer (as designed in Task 9)
- Clicking trash icon opens trash view in workstation
- Display all trashed images in thumbnail strip
- Show "Days until deletion" for each (30 - days since trashed)
- "Restore" button to return image to unsorted
- "Empty Trash" button to permanently delete all trashed images
- Add backend cleanup job for 30+ day items (trigger on app launch and brand selection)

**Files to modify:**
- `src/sip_videogen/studio/frontend/src/components/Sidebar/index.tsx` - trash icon
- `src/sip_videogen/studio/frontend/src/components/Workstation/index.tsx` - trash view mode
- `src/sip_videogen/studio/bridge.py` - `cleanup_old_trash()` method

**How to verify:**
- Click trash icon → workstation shows trashed images
- Each image shows days remaining
- Restore button moves image back to unsorted
- Empty Trash button deletes all trashed images
- Images older than 30 days are auto-deleted on app launch

---

## Task 17: Migration and First Launch

**Goal:** Handle existing images and missing status file.

**What to do:**
- On app launch (or brand selection), check if `image_status.json` exists
- If missing:
  - Scan `generated/`, `kept/`, and `trash/` for existing images
  - Create entries for each with inferred status
  - Generate unique IDs for each
  - Write `image_status.json` with version 1
- If version is old or unsupported, run migrations or rebuild from folders
- Keep migrations idempotent (safe to run multiple times)

**Files to modify:**
- `src/sip_videogen/studio/services/image_status.py` - add `backfill_from_folder()` method
- `src/sip_videogen/studio/bridge.py` - call backfill on brand load

**How to verify:**
- Delete `image_status.json` for a brand
- Launch app and select that brand
- All existing generated images appear as unsorted in workstation
- `image_status.json` is created with correct entries

---

## Task 18: Undo Toast

**Goal:** Allow users to undo keep/trash actions briefly.

**What to do:**
- After keep or trash action, show toast notification
- Toast displays: "Image moved to [Kept/Trash]" with "Undo" button
- Toast visible for 5 seconds, then auto-dismisses
- Clicking "Undo" reverses the action (restore image to previous state)
- Undo uses `unkeep_image` or `restore_image` based on last action
- Only one toast at a time (new action replaces old toast)

**Files to create:**
- May use existing toast/notification component if available
- Or create simple toast component

**Modify:**
- `src/sip_videogen/studio/frontend/src/components/Workstation/SwipeContainer.tsx` - trigger toast after action

**How to verify:**
- Swipe to keep → toast appears with "Undo"
- Click Undo → image returns to current batch
- Wait 5 seconds → toast disappears
- New action replaces existing toast

---

## Task 19: Animations and Polish

**Goal:** Add smooth transitions and visual polish.

**What to do:**
- Add transition animation when switching between images
- Add slide-out animation when image is swiped away
- Add fade-in for new images appearing
- Ensure all animations are smooth (60fps)
- Add loading spinner while images are fetching
- Match existing app visual style (colors, shadows, borders)

**Files to modify:**
- Various Workstation components
- May need CSS animations or a library like Framer Motion

**How to verify:**
- Image transitions feel smooth
- Swipe animation looks natural (card flies off screen)
- No jank or stuttering
- Loading states are clear

---

## Task 20: Testing and Edge Cases

**Goal:** Ensure robustness across all scenarios.

**Test scenarios to verify:**
- Migration: existing images in `generated/` are backfilled correctly
- Path updates: moving to kept/trash updates `currentPath` in status file
- Undo works: restore after keep/trash works correctly
- Unkeep works: kept images return to unsorted
- Crash recovery: app crash during generation leaves system in valid state
- Cancel generation: cancel stops job (or no-ops cleanly) and unlocks input
- Missing source: comparison mode handles missing source image gracefully
- Rapid swipes: fast swiping doesn't corrupt `image_status.json`
- Empty states: all empty states display correctly
- Large batches: 50+ images in batch don't break thumbnails (scrolling works)

**Files to create:**
- Additional unit tests in `tests/`
- Integration tests if framework supports

**How to verify:**
- All tests pass
- Manual testing of each scenario
- No console errors during normal usage
- App recovers gracefully from unexpected states

---

## Summary

This implementation consists of 20 tasks across 5 phases:

| Phase | Tasks | Focus |
|-------|-------|-------|
| 1 | Tasks 1-2 | Layout foundation |
| 2 | Tasks 3-4, 7 | Workstation core display |
| 3 | Tasks 5-6, 8-9 | Curation (keep/trash) |
| 4 | Tasks 10-16 | Features (compare, export, trash) |
| 5 | Tasks 17-20 | Migration, polish, testing |

Work through tasks in order. Each task builds on previous ones. Complete Task 1 before Task 2, etc.

Reference the main plan document (`WORKSTATION_IMPLEMENTATION_PLAN.md`) for architectural details and UX specifications.
