# Task Plan: Playground Shimmer Effect + Stop Button

## Goal
Replace the plain loading spinner in PreviewCanvas with the identical shimmer effect and breathing stop button from ImageDisplay (quick edit feature).

## Current State
- **PreviewCanvas** (line 24-27): Simple spinner during loading
- **PlaygroundMode** (line 76): Stop button in input area next to generate button
- **ImageDisplay** (line 200): Has shimmer overlay + sparkles + magic-stop-btn

## Target State
- PreviewCanvas shows shimmer overlay + sparkles + centered stop button during generation
- Input textarea and selectors are disabled (already partly done)
- No stop button in input area - stop button is ONLY in the canvas center
- Generate button stays as generate button (doesn't transform to stop)

## Phases
- [x] Phase 1: Update PreviewCanvas to include shimmer + stop button
- [x] Phase 2: Update PlaygroundMode to remove stop button from input area
- [x] Phase 3: Pass onStop callback from PlaygroundMode to PreviewCanvas

## Implementation Details

### Phase 1: PreviewCanvas Changes
**File:** `src/sip_studio/studio/frontend/src/components/ChatPanel/PlaygroundMode/PreviewCanvas.tsx`

Current loading state (spinner):
```tsx
{isLoading&&(
<div className="absolute inset-0 bg-white/90 dark:bg-black/90 backdrop-blur-sm flex items-center justify-center rounded-2xl">
<div className="w-8 h-8 rounded-full border-2 border-neutral-200 dark:border-neutral-700 border-t-brand-500 animate-spin"/>
</div>
)}
```

Replace with shimmer effect (copy from ImageDisplay):
```tsx
{isLoading&&(<>
<div className="shimmer-overlay rounded-2xl"/>
<div className="shimmer-sparkles rounded-2xl">{Array.from({length:38},(_,i)=><span key={i} className={`sparkle${i%3===1?' brand':''}`}/>)}</div>
<button onClick={onStop} className="magic-stop-btn" style={{pointerEvents:'auto'}}><span className="magic-stop-icon"/></button>
</>)}
```

**Props change needed:**
- Add `onStop?: () => void` to Props interface

### Phase 2: PlaygroundMode Changes
**File:** `src/sip_studio/studio/frontend/src/components/ChatPanel/PlaygroundMode/index.tsx`

1. Remove stop button from input area (line 76)
2. Keep generate button as-is (Zap icon)
3. Pass `onStop={handleStop}` to PreviewCanvas
4. Keep `disabled={isGenerating}` on all inputs/selectors

Current (line 76):
```tsx
{isGenerating?(<Button onClick={handleStop} variant="outline" ...><Square .../></Button>):(<Button ...><Zap .../></Button>)}
```

Change to (always show generate button):
```tsx
<Button onClick={handleGenerate} disabled={!prompt.trim()||isGenerating} ...><Zap .../></Button>
```

### Phase 3: Wire up callback
Pass handleStop to PreviewCanvas:
```tsx
<PreviewCanvas aspectRatio={aspectRatio} isLoading={isGenerating} result={result} onStop={handleStop}/>
```

## CSS Already Available
The shimmer CSS classes are already defined in `index.css`:
- `.shimmer-overlay` (lines 291-333) - Four corner atmospheric glow
- `.shimmer-sparkles` + `.sparkle` (lines 334-417) - 4-point star sparkles
- `.magic-stop-btn` + `.magic-stop-icon` (lines 419-456) - Breathing stop button

No CSS changes needed - just use the existing classes.

## Status
**COMPLETE** - All phases implemented
