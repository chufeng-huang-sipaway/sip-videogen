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

#### Task 10: EmptyState Component ✅

**Changes:**
- Created `src/sip_videogen/studio/frontend/src/components/Workstation/EmptyState.tsx` - Empty state display
- Updated `src/sip_videogen/studio/frontend/src/components/Workstation/index.tsx` - Integrated EmptyState

**Features:**
- Displays when `currentBatch` is empty
- Centered message: "No images to review"
- Subtitle: "Generate images using the chat, or select from sidebar"
- Clean, minimal design with image icon
- Matches existing app visual style

**Verification:**
- Build frontend: `cd src/sip_videogen/studio/frontend && npm run build` - Compiles without errors
- When no images in batch, empty state displays
- After curating all images, empty state appears
- Text is centered and readable

#### Task 11: ComparisonView Component ✅

**Changes:**
- Created `src/sip_videogen/studio/frontend/src/components/Workstation/ComparisonView.tsx` - Side-by-side comparison view
- Updated `src/sip_videogen/studio/frontend/src/components/Workstation/index.tsx` - Added Compare toggle and integrated ComparisonView

**Features:**
- 50/50 split layout for comparing generated vs source image
- Left side: generated image with "Generated" label
- Right side: source template image with "Original" label
- Placeholder displayed when source image is unavailable
- Compare toggle button in workstation header
- Uses viewMode from WorkstationContext ('single' | 'comparison')
- Toggle off returns to single image view with swipe gestures

**Verification:**
- Build frontend: `cd src/sip_videogen/studio/frontend && npm run build` - Compiles without errors
- Toggle button visible in workstation header when images are loaded
- Click toggle → view splits 50/50
- Both images display correctly with labels
- "Source not available" placeholder shown when sourceTemplatePath is missing
- Toggle off returns to single swipe view

#### Task 12: ContextPanel Component ✅

**Changes:**
- Created `src/sip_videogen/studio/frontend/src/components/Workstation/ContextPanel.tsx` - Image metadata panel
- Updated `src/sip_videogen/studio/frontend/src/components/Workstation/index.tsx` - Integrated ContextPanel

**Features:**
- Collapsed by default with info icon button in top-right corner
- Click to expand panel showing:
  - Prompt used to generate the image
  - Source template filename (if available)
  - Timestamp of generation
- "Copy" button to copy prompt text to clipboard
- Panel styled as overlay with backdrop blur
- Does not obstruct main image view
- Can be collapsed again with X button

**Verification:**
- Build frontend: `cd src/sip_videogen/studio/frontend && npm run build` - Compiles without errors
- Info icon button visible in top-right corner when images loaded
- Click expands panel with metadata
- Prompt, source, timestamp displayed correctly
- Copy button copies prompt to clipboard
- Panel can be collapsed again

#### Task 13: Chat Panel Compact Mode ✅

**Changes:**
- Updated `src/sip_videogen/studio/frontend/src/components/ChatPanel/ChatImageGallery.tsx` - Compact thumbnail display

**Features:**
- Replaced large inline image previews with 48x48 (w-12 h-12) thumbnails
- Show compact "Generated N images" confirmation text with Images icon
- Click on any thumbnail opens image in Workstation via WorkstationContext
- Limit to 4 visible thumbnails with "+N" indicator for overflow
- Clicking "+N" button opens remaining images in workstation
- Integrated with WorkstationContext to display images in main viewer
- Removed PromptDetailsModal - metadata now accessible via ContextPanel in Workstation

**Verification:**
- Build frontend: `cd src/sip_videogen/studio/frontend && npm run build` - Compiles without errors
- Generate images via chat - compact "Generated N images" text displays
- Tiny 48x48 thumbnails appear below the text
- Clicking a thumbnail opens it in the Workstation
- No large image previews cluttering the chat panel
- Chat panel width already set at 320px in App.tsx

#### Task 14: Input Lock During Generation ✅

**Changes:**
- Updated `src/sip_videogen/studio/frontend/src/components/ChatPanel/MessageInput.tsx` - Added isGenerating and onCancel props
- Updated `src/sip_videogen/studio/frontend/src/hooks/useChat.ts` - Added cancelGeneration function
- Updated `src/sip_videogen/studio/frontend/src/components/ChatPanel/index.tsx` - Wired cancel to MessageInput

**Features:**
- Input field disabled during generation (prevents double-submission)
- Send button transforms to Cancel button with spinning loader during generation
- Cancel button has stop icon with animated spinner ring
- Click Cancel stops progress polling, clears loading state
- Pending assistant message updated to "Generation cancelled."
- Calls `bridge.cancelGeneration()` to signal backend (placeholder for future)
- State resets on app restart (React state not persisted)

**Verification:**
- Build frontend: `cd src/sip_videogen/studio/frontend && npm run build` - Compiles without errors
- Start generation → input becomes disabled, send button changes to red cancel button with spinner
- Click Cancel → generation stops, message shows "Generation cancelled."
- Generation completes normally → input unlocks
- Restart app → input is unlocked (fresh React state)

#### Task 15: Export Actions ✅

**Changes:**
- Created `src/sip_videogen/studio/frontend/src/components/Workstation/ExportActions.tsx` - Export actions component
- Updated `src/sip_videogen/studio/bridge.py` - Added copy_image_to_clipboard and share_image methods
- Updated `src/sip_videogen/studio/frontend/src/lib/bridge.ts` - Added TypeScript types and bridge functions
- Updated `src/sip_videogen/studio/frontend/src/components/Workstation/index.tsx` - Integrated ExportActions

**Features:**
- Copy to clipboard button using macOS osascript (supports PNG and JPEG)
- Share button that reveals image in Finder for native sharing
- Drag-out functionality: drag image to Finder or other apps
- Visual feedback: spinner during copy, checkmark on success
- Tooltips on hover for each action
- ExportActions positioned in workstation header on left side

**Bridge Methods Added:**
- `copy_image_to_clipboard(image_path)` - Copy image to system clipboard (macOS)
- `share_image(image_path)` - Reveal image in Finder for sharing

**Verification:**
- Build frontend: `cd src/sip_videogen/studio/frontend && npm run build` - Compiles without errors
- Copy button copies image to clipboard (paste in Preview works)
- Share button opens Finder at image location
- Can drag image out to Finder or other apps
- Copy shows spinner while copying, then checkmark on success

#### Task 16: Trash Management UI ✅

**Changes:**
- Created `src/sip_videogen/studio/frontend/src/components/Workstation/TrashView.tsx` - Trash management view
- Updated `src/sip_videogen/studio/frontend/src/components/Workstation/index.tsx` - Integrated TrashView
- Updated `src/sip_videogen/studio/frontend/src/context/WorkstationContext.tsx` - Added isTrashView state
- Updated `src/sip_videogen/studio/frontend/src/components/Sidebar/index.tsx` - Added trash cleanup and view mode
- Updated `src/sip_videogen/studio/bridge.py` - Added cleanup_old_trash method
- Updated `src/sip_videogen/studio/frontend/src/lib/bridge.ts` - Added cleanupOldTrash bridge function

**Features:**
- Click trash icon in sidebar footer → opens TrashView in workstation
- Display all trashed images with thumbnail navigation
- Show "Days until deletion" badge for each image (30-day retention)
- Badge turns red when ≤7 days remaining
- "Restore" button to return image to unsorted status
- "Empty Trash" button with confirmation dialog to permanently delete all
- Back button to exit trash view and return to empty workstation
- Auto-cleanup of 30+ day old items triggered when opening trash

**Bridge Methods Added:**
- `cleanup_old_trash(brand_slug?, days?)` - Delete trash items older than specified days

**Verification:**
- Build frontend: `cd src/sip_videogen/studio/frontend && npm run build` - Compiles without errors
- Click trash icon in sidebar footer → workstation shows trashed images
- Each trashed image shows days remaining until auto-deletion
- Restore button moves image back to unsorted
- Empty Trash button deletes all trashed images with confirmation
- Images older than 30 days are auto-deleted when opening trash

#### Task 17: Migration and First Launch ✅

**Changes:**
- Updated `src/sip_videogen/studio/bridge.py` - Added backfill_images() bridge method
- Updated `src/sip_videogen/studio/frontend/src/lib/bridge.ts` - Added TypeScript types and backfillImages function
- Updated `src/sip_videogen/studio/frontend/src/context/BrandContext.tsx` - Call backfillImages on brand selection

**Features:**
- Auto-backfill existing images when brand is selected
- Scans generated/, kept/, trash/ folders for images without status entries
- Creates image_status.json with version 1 if missing
- Handles first launch and migration gracefully
- Idempotent operation (safe to run multiple times)

**Bridge Methods Added:**
- `backfill_images(brand_slug?)` - Scan folders and create entries for untracked images

**Verification:**
- Build frontend: `cd src/sip_videogen/studio/frontend && npm run build` - Compiles without errors
- Run `python -m pytest tests/test_image_status.py -v` - All 28 tests pass
- Delete `image_status.json` for a brand and select that brand
- All existing generated images should appear as unsorted in workstation
- `image_status.json` is created with correct entries

### Pending Tasks
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
10. `13c94b9` - feat(workstation): Add EmptyState component for empty workstation
11. `6cc1462` - feat(workstation): Add ComparisonView for side-by-side image comparison
12. `c82df7a` - feat(workstation): Add ContextPanel for image metadata display
13. `5686d10` - feat(workstation): Add compact mode for chat panel image gallery
14. `bcfb7c1` - feat(workstation): Add input lock during generation with cancel button
15. `2a0dd29` - feat(workstation): Add ExportActions for copy, share, and drag-out
16. `0d8ee53` - feat(workstation): Add trash management UI with restore and empty
17. `6ad793c` - feat(workstation): Add migration and first launch backfill

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
12. (For Task 10) When no images are in batch, verify empty state displays with helpful message
13. (For Task 11) With images loaded, click Compare toggle - view should split 50/50 with Generated/Original labels
14. (For Task 12) Click info icon in top-right corner - panel should expand with prompt, source, timestamp; Copy button should copy prompt
15. (For Task 13) Generate images via chat - compact "Generated N images" displays with tiny thumbnails; clicking opens in Workstation
16. (For Task 14) Start generation - input should disable, send button becomes cancel with spinner; clicking Cancel stops and shows "Generation cancelled."
17. (For Task 15) With images loaded, click copy button → image copied to clipboard (paste in Preview works); click share → Finder opens at image; drag image out → export works
18. (For Task 16) Click trash icon in sidebar footer → trash view opens; each image shows days remaining; Restore and Empty Trash buttons work
19. (For Task 17) Delete `~/.sip-videogen/brands/{slug}/image_status.json`, select that brand → existing images should auto-appear in workstation
