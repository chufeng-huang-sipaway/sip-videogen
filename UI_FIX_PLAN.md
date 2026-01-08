# Task Plan: Fix Right Panel Layout Hierarchy and Sidebar Visibility

## Goal
Fix the UX issues where (1) sidebar doesn't show on initial load in Assistant mode, and (2) the right panel header has flat hierarchy mixing mode tabs with mode-specific actions.

## Observed Problems (from screenshots)

### Problem 1: Sidebar Visibility
- In Assistant mode (Screenshot 1): No sidebar visible on left
- In Playground mode (Screenshot 2): Sidebar appears with brand icon (TB)
- **Expected**: Sidebar should be visible in BOTH modes

### Problem 2: Right Panel Header Hierarchy
Current header layout (all at same level):
```
[Assistant] [Playground] [Studio Performance ▼] [+ New Chat]
```

**Issues:**
- Mode switcher (Assistant/Playground) = global navigation
- Project selector (Studio Performance) = Assistant-mode context
- New Chat = Assistant-mode action
- All 4 elements appear visually equal but serve different purposes
- Assistant-specific controls bleed into Playground mode

## UX Critique

### Hierarchy Violation
The header violates the principle of **visual hierarchy matching functional hierarchy**:
- **Level 1** (Global): Mode switcher - affects entire panel behavior
- **Level 2** (Mode-specific): Project selector, New Chat - only relevant in Assistant mode

### Gestalt Grouping Failure
Related items aren't grouped together:
- Mode tabs should be isolated as top-level navigation
- Assistant controls (Project, New Chat) should be grouped within Assistant mode

### Mode Bleeding
Controls that only make sense in one mode are visible in both:
- "New Chat" is meaningless in Playground mode
- "Project selector" is meaningless in Playground mode

## Proposed Fix

### Correct Visual Hierarchy:
```
┌─────────────────────────────────────────────┐
│  [Assistant]  [Playground]                  │  ← Level 1: Mode tabs (always visible)
├─────────────────────────────────────────────┤
│  [Project ▼]              [+ New Chat]      │  ← Level 2: Assistant-specific header
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│  Chat content...                            │
│                                             │
│  [Input area]                               │
└─────────────────────────────────────────────┘

OR in Playground mode:

┌─────────────────────────────────────────────┐
│  [Assistant]  [Playground]                  │  ← Level 1: Mode tabs (always visible)
├─────────────────────────────────────────────┤
│  Preview canvas                             │  ← Level 2: No Assistant controls
│                                             │
│  [Aspect ratio] [Product] [Style]           │
│  [Prompt input]                             │
└─────────────────────────────────────────────┘
```

### Key Changes:
1. **Mode tabs as standalone header row** - Clear visual separation from content
2. **Mode-specific content below tabs** - Assistant controls only in Assistant mode
3. **Fix sidebar visibility** - Should show regardless of which mode is active

## Phases
- [ ] Phase 1: Diagnose sidebar visibility bug
- [ ] Phase 2: Research current ChatPanel structure
- [ ] Phase 3: Redesign header hierarchy
- [ ] Phase 4: Implement fix
- [ ] Phase 5: Test both modes

## Key Questions
1. Why does sidebar only appear in Playground mode?
2. What controls the sidebar visibility in App.tsx?
3. How is PanelModeToggle currently placed relative to other header items?

## Decisions Made
(none yet)

## Errors Encountered
(none yet)

## Analysis Complete

### Sidebar Issue Root Cause
Looking at screenshots:
- Screenshot 1 (Assistant): Only see a chevron `<` on left (this is Workstation carousel nav, NOT sidebar)
- Screenshot 2 (Playground): Sidebar IS visible with TB bubble, settings, collapse icons

The sidebar wrapper (72px) is rendering but appears transparent/invisible in screenshot 1. The sidebar content (BrandSelector compact, icons) isn't showing. This could be:
1. A z-index issue where sidebar is behind workstation
2. Background transparency issue making sidebar invisible
3. Some CSS conflict specific to initial render

### Header Hierarchy Issue Root Cause
Current structure (lines 363-385 in ChatPanel):
```tsx
<div className="flex items-center justify-between">  // justify-between spreads items
  <div className="flex items-center gap-3">
    <PanelModeToggle/>  // Mode tabs
    {panelMode==='assistant' && <ProjectSelector/>}  // Assistant-only (GOOD)
  </div>
  <div className="flex items-center gap-3">
    <Button>New Chat</Button>  // ALWAYS visible (BAD - should be assistant-only)
  </div>
</div>
```

**Problems:**
1. New Chat is visible in Playground mode (should be hidden)
2. Mode tabs and project selector in same visual row = flat hierarchy
3. justify-between creates awkward spacing

## Fix Plan

### Fix 1: Header Hierarchy Redesign
```
BEFORE:
[Assistant] [Playground] [Project ▼]          [+ New Chat]

AFTER:
┌─────────────────────────────────────────────┐
│ [Assistant] [Playground]                    │  ← Standalone mode tabs
├─────────────────────────────────────────────┤
│ [Project ▼]              [+ New Chat]       │  ← Assistant-only subheader
│ Chat content...                             │
└─────────────────────────────────────────────┘

OR for Playground:
┌─────────────────────────────────────────────┐
│ [Assistant] [Playground]                    │  ← Mode tabs (same)
├─────────────────────────────────────────────┤
│ Preview canvas (no project/newchat)         │  ← Playground content
└─────────────────────────────────────────────┘
```

### Fix 2: Sidebar Visibility
Check sidebar CSS - likely needs explicit background color in collapsed state, and verify z-index stacking.

## Status
**Phase 4 Complete** - Fixes implemented

## Changes Made

### Fix 1: Sidebar Visibility (Sidebar/index.tsx)
- Changed `bg-sidebar/50` to `bg-background/80` (sidebar was undefined color)
- Changed `bg-sidebar/95` to `bg-background/95`
- Sidebar now uses actual defined background color with proper opacity

### Fix 2: Header Hierarchy (ChatPanel/index.tsx)
**Before:**
```
[Assistant] [Playground] [Project ▼]          [+ New Chat]
```
All items in same row = flat hierarchy

**After:**
```
┌─────────────────────────────────────────────┐
│        [Assistant] [Playground]             │  ← Centered mode tabs
├─────────────────────────────────────────────┤
│ [Project ▼]              [+ New Chat]       │  ← Assistant-only subheader
│ Chat content...                             │
└─────────────────────────────────────────────┘
```
- Mode tabs isolated in their own centered row (top-level navigation)
- Project selector + New Chat moved INSIDE assistant mode div
- These controls are now only visible in Assistant mode (not Playground)
