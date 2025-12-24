# PR Guide: Workstation Feature Implementation

## Overview

This PR implements the **Workstation** feature - a dedicated middle panel for image review and curation in Brand Studio. The implementation follows the plan in `WORKSTATION_IMPLEMENTATION_PLAN.md` and tasks in `WORKSTATION_TASKS.md`.

## Branch

`ui-refactor`

## Current Status

### Completed Tasks

#### Task 1: Three-Column Layout Foundation ✅

**Changes:**
- Created `src/sip_videogen/studio/frontend/src/components/Workstation/index.tsx` - Placeholder component
- Updated `src/sip_videogen/studio/frontend/src/App.tsx` - Three-column layout

**Layout Structure:**
```
┌─────────────┬────────────────────────────┬──────────────┐
│   Sidebar   │        Workstation         │     Chat     │
│   (280px)   │       (flexible)           │   (320px)    │
└─────────────┴────────────────────────────┴──────────────┘
```

**Verification:**
- Run `./scripts/studio-demo.sh`
- Verify three columns: Sidebar (left), Workstation placeholder (middle), Chat (right)
- Resize window - Workstation should grow/shrink while Sidebar and Chat stay fixed

#### Task 2: WorkstationContext Setup ✅

**Changes:**
- Created `src/sip_videogen/studio/frontend/src/context/WorkstationContext.tsx` - State management
- Updated `src/sip_videogen/studio/frontend/src/main.tsx` - Wrapped app with WorkstationProvider

**State Interface:**
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

**Actions Provided:**
- `setCurrentBatch`, `setSelectedIndex`, `setViewMode`
- `setComparisonSource`, `addToUnsorted`, `removeFromUnsorted`, `clearCurrentBatch`

**Verification:**
- App loads without errors
- No console errors related to context

#### Task 3: ImageDisplay Component ✅

**Changes:**
- Created `src/sip_videogen/studio/frontend/src/components/Workstation/ImageDisplay.tsx` - Main image viewer
- Updated `src/sip_videogen/studio/frontend/src/components/Workstation/index.tsx` - Integrated ImageDisplay

**Features:**
- Displays currently selected image from WorkstationContext
- Image fills available space with object-contain (maintains aspect ratio)
- Centered horizontally and vertically
- Subtle background to distinguish from empty areas
- Handles file:// protocol for local images

**Verification:**
- Hardcode a test image path in context to verify display
- Image should be centered and maintain aspect ratio
- No stretching or distortion

#### Task 4: ThumbnailStrip Component ✅

**Changes:**
- Created `src/sip_videogen/studio/frontend/src/components/Workstation/ThumbnailStrip.tsx` - Horizontal thumbnail navigation
- Updated `src/sip_videogen/studio/frontend/src/components/Workstation/index.tsx` - Integrated ThumbnailStrip

**Features:**
- Displays 64x64 thumbnails for all images in currentBatch
- Highlights currently selected thumbnail with border and shadow
- Click on thumbnail updates selectedIndex in context
- Horizontal scrolling when thumbnails overflow
- Only shown when batch has more than one image

**Verification:**
- Add 5-10 test images to the context
- Thumbnails appear in horizontal row below main image
- Clicking a thumbnail changes the main image
- Selected thumbnail has visible highlight
- Horizontal scroll works when thumbnails overflow

#### Task 5: Backend Image Status Service ✅

**Changes:**
- Created `src/sip_videogen/studio/services/image_status.py` - ImageStatusService class
- Updated `src/sip_videogen/studio/services/__init__.py` - Export ImageStatusService
- Created `tests/test_image_status.py` - 28 comprehensive unit tests

**Features:**
- Track image lifecycle status: unsorted → kept / trashed
- Store status in `~/.sip-videogen/brands/{slug}/image_status.json`
- Atomic writes (temp file + rename) to prevent corruption
- Methods: `register_image`, `get_status`, `set_status`, `list_by_status`, `update_path`, `delete_image`
- `backfill_from_folders` for migration of existing images
- `cleanup_old_trash` for auto-deleting 30+ day old trashed images
- ISO 8601 timestamps for `keptAt` / `trashedAt`

**JSON Schema:**
```json
{
  "version": 1,
  "images": {
    "img_abc123": {
      "id": "img_abc123",
      "status": "unsorted",
      "originalPath": "/path/to/generated/hero.png",
      "currentPath": "/path/to/generated/hero.png",
      "prompt": "A hero image",
      "sourceTemplatePath": null,
      "timestamp": "2024-01-15T10:30:00+00:00",
      "keptAt": null,
      "trashedAt": null
    }
  }
}
```

**Verification:**
- Run `python -m pytest tests/test_image_status.py -v` - All 28 tests pass
- Test: `register_image` creates entry with "unsorted" status
- Test: `set_status` changes status and sets timestamps correctly
- Test: `list_by_status` filters by status
- Test: Atomic writes don't corrupt file
- Test: `backfill_from_folders` scans existing images
- Test: `cleanup_old_trash` deletes old trashed images

#### Task 6: Bridge Methods for Image Status ✅

**Changes:**
- Updated `src/sip_videogen/studio/bridge.py` - Added ImageStatusService and bridge methods
- Updated `src/sip_videogen/studio/frontend/src/lib/bridge.ts` - Added TypeScript types and bridge functions

**Bridge Methods Added:**
- `get_unsorted_images(brand_slug?)` - List unsorted images for a brand
- `get_images_by_status(brand_slug?, status?)` - Filter images by status
- `mark_image_kept(image_id, brand_slug?)` - Move image to kept/ folder
- `mark_image_trashed(image_id, brand_slug?)` - Move image to trash/ folder
- `unkeep_image(image_id, brand_slug?)` - Return kept image to unsorted
- `restore_image(image_id, brand_slug?)` - Restore trashed image to unsorted
- `empty_trash(brand_slug?)` - Permanently delete all trashed images
- `register_image(image_path, brand_slug?, prompt?, source_template_path?)` - Register new image
- `register_generated_images(images, brand_slug?)` - Batch register generated images
- `cancel_generation(brand_slug?)` - Placeholder for future implementation

**TypeScript Types Added:**
- `ImageStatusType` - 'unsorted' | 'kept' | 'trashed'
- `ImageStatusEntry` - Complete image status entry with all fields
- `RegisterImageInput` - Input type for registering images

**File Movement Logic:**
- When status changes, files are moved to appropriate folders:
  - unsorted → `assets/generated/`
  - kept → `assets/kept/`
  - trashed → `assets/trash/`
- Handles filename conflicts by appending counter (_1, _2, etc.)
- Updates `currentPath` in status file after move

**Verification:**
- Build frontend: `cd src/sip_videogen/studio/frontend && npm run build` - Compiles without errors
- Verify Python: `python3 -m py_compile src/sip_videogen/studio/bridge.py` - No syntax errors
- All existing tests still pass: `python -m pytest tests/test_image_status.py -v`
- From browser console: `window.pywebview.api.get_unsorted_images()` returns list or empty array

#### Task 7: Wire Generation Results to Workstation ✅

**Changes:**
- Updated `src/sip_videogen/studio/frontend/src/hooks/useChat.ts` - Added onImagesGenerated callback
- Updated `src/sip_videogen/studio/frontend/src/components/ChatPanel/index.tsx` - Integrated WorkstationContext

**Features:**
- After image generation completes, images are registered via `bridge.registerGeneratedImages()`
- Registered images (with IDs from backend) are pushed to WorkstationContext.currentBatch
- Images also added to unsortedImages for tracking
- First image is auto-selected (selectedIndex = 0)
- IDs are generated in backend, not frontend

**Flow:**
```
bridge.chat() returns images → registerGeneratedImages() → onImagesGenerated callback
                                                                     ↓
                                                          setCurrentBatch(images)
                                                          addToUnsorted(images)
```

**Verification:**
- Build frontend: `cd src/sip_videogen/studio/frontend && npm run build` - Compiles without errors
- Generate images using the chat
- Images should immediately appear in the workstation
- Thumbnails show all generated images
- First image is selected by default

#### Task 8: SwipeContainer Component ✅

**Changes:**
- Created `src/sip_videogen/studio/frontend/src/components/Workstation/SwipeContainer.tsx` - Swipe gesture detection
- Updated `src/sip_videogen/studio/frontend/src/components/Workstation/index.tsx` - Integrated SwipeContainer with keep/trash actions

**Features:**
- Mouse and touch gesture support for horizontal swiping
- Visual feedback: image tilts in swipe direction, color overlay (green for keep, red for trash)
- "Keep" / "Trash" label appears during swipe with opacity based on progress
- Threshold-based triggering (100px horizontal movement)
- Snap back animation if below threshold
- Calls `bridge.markImageKept()` on right swipe, `bridge.markImageTrashed()` on left swipe
- Auto-advances to next image after curation action
- Removes curated image from current batch and unsorted list

**Verification:**
- Build frontend: `cd src/sip_videogen/studio/frontend && npm run build` - Compiles without errors
- Drag image right past threshold → image disappears, file moves to kept/ folder
- Drag image left past threshold → image disappears, file moves to trash/ folder
- Drag but release before threshold → image snaps back
- Visual tilt effect visible during drag
- Next image auto-displays after swipe

#### Task 9: Sidebar Kept Section ✅

**Changes:**
- Created `src/sip_videogen/studio/frontend/src/components/Sidebar/sections/KeptSection.tsx` - Kept images section
- Updated `src/sip_videogen/studio/frontend/src/components/Sidebar/index.tsx` - Added KeptSection and trash icon

**Features:**
- New "Kept" nav section with Heart icon in sidebar
- Displays thumbnails of all kept images for the active brand
- Click on thumbnail opens image in workstation for viewing
- Context menu with "View in Workstation" and "Return to Unsorted" actions
- Trash icon in sidebar footer opens trashed images in workstation
- Kept count shown when brand is active

**Verification:**
- Build frontend: `cd src/sip_videogen/studio/frontend && npm run build` - Compiles without errors
- After swiping right on images, they appear in Sidebar "Kept" section
- Clicking a kept image opens it in workstation
- Right-click on kept image shows context menu with unkeep option
- Trash icon visible in sidebar footer

### Pending Tasks
- Task 10: EmptyState Component
- Task 11: ComparisonView Component
- Task 12: ContextPanel Component
- Task 13: Chat Panel Compact Mode
- Task 14: Input Lock During Generation
- Task 15: Export Actions
- Task 16: Trash Management UI
- Task 17: Migration and First Launch
- Task 18: Undo Toast
- Task 19: Animations and Polish
- Task 20: Testing and Edge Cases

## Commits

1. `30cb294` - feat(workstation): Add three-column layout foundation
2. `b13ab2b` - feat(workstation): Add WorkstationContext for state management
3. `e3cdcf6` - feat(workstation): Add ImageDisplay component
4. `77ccd0a` - feat(workstation): Add ThumbnailStrip component for batch navigation
5. `ab8dc3f` - feat(workstation): Add ImageStatusService for image lifecycle tracking
6. `a757bf8` - feat(workstation): Add bridge methods for image status operations
7. `fe89309` - feat(workstation): Wire generation results to workstation display
8. `c0d4f4c` - feat(workstation): Add SwipeContainer for keep/trash gestures
9. `e2199ec` - feat(workstation): Add Kept section and trash icon to sidebar

## Related Files

- `WORKSTATION_IMPLEMENTATION_PLAN.md` - Detailed architecture and UX specs
- `WORKSTATION_TASKS.md` - Step-by-step implementation tasks

## Testing Instructions

1. Run `./scripts/studio-demo.sh` to launch Brand Studio
2. Verify three-column layout displays correctly
3. Verify existing sidebar functionality still works
4. Verify chat functionality still works
5. (For Task 3) Add test images to context and verify ImageDisplay works
6. (For Task 4) Add multiple test images to context and verify ThumbnailStrip appears and works
7. (For Task 5) Run `python -m pytest tests/test_image_status.py -v` - All tests should pass
8. (For Task 6) Build frontend: `cd src/sip_videogen/studio/frontend && npm run build` - Should compile without errors
9. (For Task 7) Generate images via chat - images should appear in workstation automatically
10. (For Task 8) Drag images left/right to test swipe gestures for keep/trash curation
11. (For Task 9) After keeping images via swipe, check Sidebar "Kept" section - images should appear there
