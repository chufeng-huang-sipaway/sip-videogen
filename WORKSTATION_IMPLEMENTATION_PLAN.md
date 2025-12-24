# Workstation Feature Implementation Plan

## Why This Change

### Current Pain Points
1. **Image flood problem** - After generating 50-100 images, users lose track of which ones they want to keep
2. **Poor review experience** - Must use macOS Finder/Preview to compare images one by one
3. **No curation workflow** - No way to mark keepers vs drafts inside the app
4. **Chat clutter** - Large image previews in chat waste space and mix commands with results
5. **Export friction** - Copying images requires navigating to Finder

### Business Value
- 99% of post-brand-creation work is image generation and curation
- Users generate dozens of variations to find 3-5 keepers
- Current workflow forces context-switching between app and Finder
- Keeping everything in-app enables future features (feedback loops, AI learning from kept images)

---

## What We're Building

### Three-Column Layout
```
┌─────────────┬────────────────────────────┬──────────────┐
│   Sidebar   │        Workstation         │     Chat     │
│    ~20%     │          ~55%              │    ~25%      │
│  (280px)    │       (flexible)           │   (320px)    │
└─────────────┴────────────────────────────┴──────────────┘
```

### Workstation Features
1. **Large image display** - Primary focus area for reviewing generated images
2. **Thumbnail strip** - Quick navigation between images in current batch
3. **Swipe gestures** - Tinder-style right=keep, left=trash for rapid curation
4. **Comparison mode** - 50/50 split toggle to compare result vs source template/product
5. **Context panel** - Compact display of prompt, source, timestamp (collapsible/hover)
6. **Empty state** - Clean placeholder when nothing to review

### Image Lifecycle
```
Generated → Unsorted (workstation inbox)
                ├─ swipe right → Kept (sidebar, organized by project/product)
                └─ swipe left  → Trash (30-day recycle bin)
```

### Chat Changes
1. **Smaller footprint** - Fixed width (~320px), command-focused
2. **Tiny thumbnails** - Click to open in workstation (no large inline previews)
3. **Input lock during generation** - Prevents multi-tasking, keeps flow linear
4. **Compact confirmation** - "Generated 3 images ✓" instead of large gallery

### Export Options
- Copy to clipboard button
- Drag image out to other apps
- System share sheet integration
- Right-click context menu

---

## What We're NOT Building (This Phase)

1. **Video support** - Focus on images first, video curation later
2. **Multi-session parallelism** - One job at a time, input locked during generation
3. **AI feedback loop** - Kept images as training signal is future work
4. **Keyboard shortcuts** - Power user features for later iteration
5. **Batch operations** - Single image swipe only, no multi-select yet

---

## Architecture

### New Components
```
src/sip_videogen/studio/frontend/src/components/
├── Workstation/
│   ├── index.tsx              # Main container, orchestrates sub-components
│   ├── ImageDisplay.tsx       # Large primary image view
│   ├── ThumbnailStrip.tsx     # Horizontal thumbnail navigation
│   ├── SwipeContainer.tsx     # Gesture handling (swipe left/right)
│   ├── ComparisonView.tsx     # 50/50 split comparison mode
│   ├── ContextPanel.tsx       # Prompt, source, timestamp display
│   ├── EmptyState.tsx         # Placeholder when no images
│   └── ExportActions.tsx      # Copy, share, drag-out handlers
```

### New Context
```
src/sip_videogen/studio/frontend/src/context/
├── WorkstationContext.tsx     # Current batch, selected image, view mode
```

### State Shape
```typescript
interface WorkstationState {
  currentBatch: GeneratedImage[];     // Images from latest generation
  selectedIndex: number;              // Currently viewed image
  viewMode: 'single' | 'comparison';  // Display mode
  comparisonSource: string | null;    // Template/product image for comparison
  unsortedImages: GeneratedImage[];   // All images pending curation
}
```

### Image Status Model
```typescript
interface ImageStatus {
  id: string;
  status: 'unsorted' | 'kept' | 'trashed';
  originalPath: string;             // Stable reference; never changes
  currentPath: string;              // Current filesystem location
  trashedAt?: Date;                   // For 30-day cleanup
  keptAt?: Date;
  projectSlug?: string;               // Where kept image is organized
  productSlug?: string;
}
```

### Backend Changes
```
src/sip_videogen/studio/
├── bridge.py                  # Add: mark_image_kept(), mark_image_trashed(),
│                              #      get_unsorted_images(), empty_trash()
├── services/
│   └── image_status.py        # New: Track image lifecycle states
```

### Storage Structure
```
~/.sip-videogen/brands/{slug}/
├── assets/
│   ├── generated/             # All generated images
│   ├── kept/                  # Curated images (or symlinks)
│   └── trash/                 # 30-day holding area
├── image_status.json          # Status tracking per image
```

### Status Source of Truth
- `image_status.json` is the canonical source for status and current path
- Folder scans are used only for recovery/backfill on first launch or if JSON is missing
- UI always resolves by image `id` to avoid path-based breakage
- Store `keptAt`/`trashedAt` as ISO 8601 strings in JSON

### image_status.json Example
```json
{
  "version": 1,
  "images": {
    "img_01J9K3Q3Q5W2ZB6D2V2H8M0B5E": {
      "id": "img_01J9K3Q3Q5W2ZB6D2V2H8M0B5E",
      "status": "unsorted",
      "originalPath": "/Users/name/.sip-videogen/brands/acme/assets/generated/hero-01.png",
      "currentPath": "/Users/name/.sip-videogen/brands/acme/assets/generated/hero-01.png",
      "keptAt": null,
      "trashedAt": null,
      "projectSlug": "acme",
      "productSlug": "bottle"
    }
  }
}
```

### Schema Versioning & Migration
- Increment `version` on schema changes and provide a lightweight migrator
- If version is missing or unsupported, fall back to folder scan + rebuild
- Keep migrations idempotent; never delete images during migration

---

## Data Flow

### Generation Flow
```
1. User sends prompt in Chat
2. Chat input locks (disabled state)
3. Agent generates images
4. Bridge receives results, saves to generated/
5. Bridge creates/updates ImageStatus with stable id + originalPath/currentPath
6. Results pushed to WorkstationContext.currentBatch
7. Workstation auto-displays first image
8. Chat shows compact confirmation
9. Chat input unlocks
```

### Curation Flow
```
1. User views image in Workstation
2. Swipe right → mark_image_kept() → moves to kept/, updates status + sidebar
3. Swipe left → mark_image_trashed() → moves to trash/, starts 30-day timer
4. Show short undo window (toast) to reverse last action
5. Next image auto-advances in thumbnail strip
6. When batch empty, show empty state
```

### Comparison Flow
```
1. User clicks "Compare" toggle
2. Workstation splits 50/50
3. Left: current generated image
4. Right: source template/product image (from generation metadata)
5. Toggle off to return to single view
```

### Error/Lock Handling
```
1. Generation failure or timeout unlocks chat input
2. Provide "Cancel generation" action while locked
3. If app crashes mid-generation, input unlocks on relaunch
```

---

## Key Files to Modify

### Frontend
| File | Change |
|------|--------|
| `App.tsx` | Three-column layout, add Workstation |
| `ChatPanel/index.tsx` | Reduce width, compact image display |
| `ChatPanel/ChatImageGallery.tsx` | Tiny thumbnails, click-to-workstation |
| `Sidebar/index.tsx` | Add "Kept" section, trash icon |
| `context/WorkstationContext.tsx` | New context for workstation state |

### Backend
| File | Change |
|------|--------|
| `bridge.py` | New methods: mark_kept, mark_trashed, get_unsorted |
| `services/image_status.py` | New service for image lifecycle |
| `services/asset_service.py` | Support trash folder operations |

---

## UX Details

### Swipe Gesture
- Trackpad swipe or mouse drag horizontally
- Visual feedback: card tilts in swipe direction
- Threshold: 100px to trigger action
- Snap back if below threshold

### Comparison Mode
- Toggle button in workstation header
- 50/50 horizontal split
- Vertical divider, optionally draggable
- Labels: "Generated" | "Original"
- If source missing, show placeholder card with "Source missing"

### Context Panel
- Collapsed by default (icon button to expand)
- Shows: prompt used, product/template name, timestamp
- Copy prompt button for reuse

### Empty State
- Centered message: "No images to review"
- Subtle prompt: "Generate images using the chat, or select from sidebar"

### Trash Behavior
- Hidden from main view (small trash icon in sidebar footer)
- Click to view trashed images
- "Empty Trash" button
- Auto-cleanup job for 30+ day items
- Restore action to return items to unsorted

### Keep Behavior
- "Kept" is reversible; allow "Unkeep" to return items to unsorted

### Persistence Reliability
- Atomic writes for `image_status.json` (write temp + rename)
- Coalesce rapid updates to avoid corruption on fast swipes

### macOS Export Notes
- Share sheet via native bridge
- Drag-out via file URL/NSItemProvider
- Clipboard copy via NSImage + file URL fallback

---

## Migration Notes

### No Breaking Changes
- Existing generated images remain in `generated/` folder
- New status tracking is additive (defaults to 'unsorted')
- Chat still functional, just smaller

### First Launch
- Scan `generated/` to backfill `image_status.json` if missing
- All existing generated images appear as "unsorted" in workstation
- User can curate backlog at their pace

---

## Test Checklist
- Migration: existing `generated/` images backfill into `image_status.json`
- Path remap: moving to kept/trash preserves ID-based references in UI
- Undo/restore: swipe then undo restores status and path; unkeep returns to unsorted
- Crash/relaunch: input unlocks and status file remains valid
- Missing source: comparison shows placeholder and falls back gracefully
- Rapid swipes: atomic writes prevent JSON corruption

---

## Implementation Phases

### Phase 1: Layout Foundation
- Three-column layout in App.tsx
- Empty Workstation component
- Resize ChatPanel to fixed width
- Verify sidebar still works

### Phase 2: Workstation Core
- ImageDisplay + ThumbnailStrip
- WorkstationContext
- Wire generation results to workstation
- Basic navigation (click thumbnails)

### Phase 3: Curation
- SwipeContainer with gestures
- Backend image_status service
- Keep/Trash actions
- Sidebar updates for kept images

### Phase 4: Comparison & Export
- ComparisonView toggle
- ContextPanel (prompt, source)
- Export actions (copy, drag, share)
- Trash management UI

### Phase 5: Polish
- Empty state
- Animations and transitions
- Chat compact mode refinements
- Testing and edge cases
