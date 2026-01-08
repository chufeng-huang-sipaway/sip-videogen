# Task Plan: Sip Studio UI Redesign

## Goal
Redesign Sip Studio's layout to promote the Assistant as the primary creative interface, with a floating sidebar, expanded chat panel, and Playground mode replacing the Quick Generator modal.

## Design Vision Summary

### Current Problems
- Chat panel cramped at 320px fixed width
- Sidebar takes space but is low-frequency
- Quick Generator as popup modal feels disconnected
- Autonomy toggle in wrong location (header vs near input)

### Target State
1. **Floating Sidebar**: Collapsed by default, expands on hover, auto-collapses on blur
2. **Expanded Chat Panel**: Gains horizontal space from collapsed sidebar
3. **Two Modes in Right Panel**: Assistant (default) and Playground (replaces Quick Generator modal)
4. **Autonomy Toggle**: Moved near input area in Assistant mode

## Phases
- [x] Phase 1: Research current implementation
- [x] Phase 2: Floating sidebar implementation
- [x] Phase 3: Right panel mode system (Assistant/Playground toggle)
- [x] Phase 4: Playground mode UI (preview canvas, inline controls)
- [x] Phase 5: Assistant mode refinements (autonomy toggle relocation)
- [x] Phase 6: Remove old Quick Generator modal and FAB
- [ ] Phase 7: Polish and integration testing

## Key Questions
1. What's the current sidebar collapse/expand implementation? ✅ ANSWERED
2. How does the current aspect ratio selector work (to reuse in Playground)? ✅ ANSWERED
3. What bridge methods exist for Quick Generator (to reuse in Playground)? ✅ ANSWERED
4. Where is autonomy toggle currently rendered? ✅ ANSWERED

## Decisions Made
- [Sidebar behavior]: Collapsed by default, **overlay** on hover (not layout push), auto-collapse on mouse leave. Uses `position: absolute` when expanded to overlay content.
- [Mode default]: Always start in Assistant mode
- [Playground loading]: Spinner overlay on aspect-ratio placeholder canvas
- [Generated images]: Images save to gallery immediately (matches current Quick Generator). "New Generation" clears preview for next generation. No explicit Save/Discard needed.
- [Aspect ratio selector]: Reuse existing component with same styling
- [Video support]: Playground is **image-only** for now (matches existing quick_generate bridge API). Video generation mode toggle hidden in Playground.
- [State preservation]: Keep Assistant content mounted but hidden (CSS display:none) when in Playground mode, preventing state loss and stream interruption.
- [LocalStorage validation]: All localStorage reads have safe fallbacks with type guards.
- [Hover collapse edge case]: Use `onMouseLeave` on a wrapper div that includes any popover/menu portals, OR add delay before collapse to allow menu interaction.

## API Clarifications (from research)
- `bridge.quickGenerate(prompt, productSlug?, styleRefSlug?, aspectRatio, count)` - Image generation only, no brandSlug param (uses internal state), no video support
- `bridge.registerGeneratedImages(images)` - Used by Quick Generator to register images to gallery
- Current Quick Generator behavior: Images are saved to gallery immediately on generation

## Errors Encountered
(None yet)

## Status
**Phase 1 Complete** - Research done, see UI_REDESIGN_NOTES.md for findings

**[Codex Review 3/3 - FINAL]** - All issues resolved:

**ACCEPTED** (changes made):
- Sidebar wrapper approach: Keep 72px spacer in-flow, overlay panel is absolute child
- Focus-within handling for keyboard accessibility
- onBlur relatedTarget null check added
- localStorage try/catch wrappers
- Use data URL from bridge (not file:// paths)
- Explicit test commands in Phase 7
- Brand-aware hooks with reset on brand change
- PreviewCanvas needs explicit width constraints

**DISCARDED** (with reasoning):
- Gallery registration: Verified Quick Generator does NOT call `registerGeneratedImages`. Playground matches this behavior. Images are saved to disk but not tracked in status system. (If tracking is desired later, it's a separate feature.)
- Portal menu handling: 200ms delay + focus-within is acceptable initial behavior. Portal issues are edge cases that can be refined post-launch if needed.
- "New Generation" clears prompt: This matches current Quick Generator behavior and is intentional UX.
- Mode switching while generating: Out of scope for initial implementation. User should finish generation before switching.

**Ready for implementation** - All questions resolved, plan is final

---

## Phase Details

### Phase 1: Research Current Implementation ✅
**Goal**: Understand existing code structure for sidebar, chat panel, quick generator

**Findings saved to**: UI_REDESIGN_NOTES.md

**Key discoveries**:
- Sidebar uses `collapsed` prop, widths: 280px (expanded) / 72px (collapsed)
- AspectRatioSelector is excellent - mode-aware, has RatioIcon, platform hints
- ModeToggle is excellent - pill-shaped Image/Video toggle
- ChatPanel is fixed 320px in App.tsx
- AutonomyToggle is in ChatPanel header (line 371)
- QuickGenerator is FAB + modal pattern

---

### Phase 2: Floating Sidebar Implementation
**Goal**: Make sidebar collapsed by default, expand on hover as **overlay** (not push), auto-collapse on mouse leave

**Files to modify**:
- `src/sip_studio/studio/frontend/src/components/Sidebar/index.tsx`
- `src/sip_studio/studio/frontend/src/App.tsx`

**Implementation**:

**Key Architecture**: Use a WRAPPER approach to prevent layout shift:
- Outer wrapper (`<div>`) stays fixed at 72px width, always in flex layout flow
- Inner sidebar panel (`<aside>`) becomes absolute and expands to 280px when hovered
- This ensures NO layout shift because the wrapper never changes size

```tsx
// Sidebar/index.tsx changes:
// 1. Add hover + focus state management
const [isHovering, setIsHovering] = useState(false)
const [isFocusWithin, setIsFocusWithin] = useState(false)
const collapseTimeoutRef = useRef<ReturnType<typeof setTimeout>>()

// 2. Expanded = hovering OR focus-within (for keyboard accessibility)
const isExpanded = !collapsed || isHovering || isFocusWithin

// 3. Mouse + focus handlers with debounced collapse
const handleMouseEnter = () => {
  if (collapseTimeoutRef.current) clearTimeout(collapseTimeoutRef.current)
  setIsHovering(true)
}
const handleMouseLeave = () => {
  collapseTimeoutRef.current = setTimeout(() => setIsHovering(false), 200)
}
const handleFocusIn = () => setIsFocusWithin(true)
const handleFocusOut = (e: React.FocusEvent) => {
  // Only collapse if focus moves outside sidebar entirely (null check for window blur)
  if (!e.relatedTarget || !e.currentTarget.contains(e.relatedTarget as Node)) setIsFocusWithin(false)
}
useEffect(() => () => { if(collapseTimeoutRef.current) clearTimeout(collapseTimeoutRef.current) }, [])

// 4. WRAPPER approach: outer div is fixed width, inner aside is absolute when expanded
return (
  <div
    className="relative flex-shrink-0 w-[72px] h-full"
    onMouseEnter={handleMouseEnter}
    onMouseLeave={handleMouseLeave}
  >
    <aside
      onFocus={handleFocusIn}
      onBlur={handleFocusOut}
      className={cn(
        "absolute left-0 top-0 h-full flex flex-col border-r transition-all duration-200 bg-background",
        isExpanded ? "w-[280px] z-50 shadow-xl" : "w-[72px]"
      )}
    >
      {/* Sidebar content - render expanded or collapsed based on isExpanded */}
    </aside>
  </div>
)
```

```tsx
// App.tsx changes:
// 1. Default to collapsed, with localStorage fallback
const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
  try {
    const saved = localStorage.getItem(SIDEBAR_COLLAPSED_KEY)
    return saved === null ? true : saved === 'true'
  } catch { return true }
})

// 2. Layout: Wrapper div ensures 72px space always reserved
<div className="relative flex h-screen overflow-hidden">
  <Sidebar collapsed={sidebarCollapsed} onToggle={handleSidebarToggle} />
  <Workstation ... />
  <div className="flex-1 max-w-[480px] min-w-[320px] flex-shrink-0">
    <ChatPanel brandSlug={activeBrand} />
  </div>
</div>
```

**Note on layout**: The WRAPPER approach guarantees no layout shift:
- Outer wrapper `<div>` is always `w-[72px]` in flex flow (never changes)
- Inner `<aside>` is absolute positioned, can expand to 280px without affecting layout
- Shadow and z-50 make the expanded state visually distinct as an overlay

**Tasks**:
- [ ] Add hover + focus-within state to Sidebar component
- [ ] Use `ReturnType<typeof setTimeout>` for timer ref type
- [ ] Add onMouseEnter/onMouseLeave/onFocus/onBlur handlers
- [ ] Make expanded sidebar position absolute (overlay) when collapsed
- [ ] Add bg-background to prevent transparency issues
- [ ] Add z-50 and shadow-xl for overlay appearance
- [ ] Update App.tsx default to collapsed=true with try/catch
- [ ] Make ChatPanel width flexible (flex-1 with max/min)
- [ ] Test keyboard navigation (Tab into sidebar keeps it expanded)
- [ ] Verify menus/popovers work with focus-within + 200ms delay

**Success criteria**:
- Sidebar starts collapsed (72px)
- Hovering expands it as overlay (no content shift)
- Focus-within keeps it expanded (keyboard accessible)
- Moving mouse away collapses after 200ms delay
- Tab navigation works correctly

---

### Phase 3: Right Panel Mode System
**Goal**: Add Assistant/Playground toggle to ChatPanel

**Files to create**:
- `src/sip_studio/studio/frontend/src/components/ChatPanel/PanelModeToggle.tsx`

**Files to modify**:
- `src/sip_studio/studio/frontend/src/components/ChatPanel/index.tsx`

**Implementation**:

```tsx
// PanelModeToggle.tsx - similar to ModeToggle but for panel modes
import { MessageSquare, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'

type PanelMode = 'assistant' | 'playground'

interface Props {
  value: PanelMode
  onChange: (m: PanelMode) => void
  disabled?: boolean
}

export function PanelModeToggle({ value, onChange, disabled }: Props) {
  const isPlayground = value === 'playground'
  return (
    <div className={cn(
      "inline-flex items-center gap-0.5 p-0.5 rounded-full",
      "bg-white/50 dark:bg-white/10 border border-border/40",
      disabled && "opacity-50 pointer-events-none"
    )}>
      <button
        onClick={() => onChange('assistant')}
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all",
          !isPlayground
            ? "bg-white dark:bg-white/20 shadow-sm text-foreground"
            : "text-muted-foreground hover:text-foreground"
        )}
        disabled={disabled}
      >
        <MessageSquare className="w-4 h-4" />
        <span>Assistant</span>
      </button>
      <button
        onClick={() => onChange('playground')}
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all",
          isPlayground
            ? "bg-white dark:bg-white/20 shadow-sm text-foreground"
            : "text-muted-foreground hover:text-foreground"
        )}
        disabled={disabled}
      >
        <Sparkles className="w-4 h-4" />
        <span>Playground</span>
      </button>
    </div>
  )
}
```

```tsx
// ChatPanel/index.tsx changes:
// 1. Add state for panel mode
const [panelMode, setPanelMode] = useState<'assistant' | 'playground'>('assistant')

// 2. Add toggle in header area (replacing/alongside project selector)
<PanelModeToggle value={panelMode} onChange={setPanelMode} disabled={!brandSlug} />

// 3. Render BOTH modes but hide inactive one (preserves state, prevents stream interruption)
<div className={panelMode === 'assistant' ? 'flex flex-col flex-1' : 'hidden'}>
  {/* Existing chat content (ScrollArea, MessageList, etc.) */}
</div>
<div className={panelMode === 'playground' ? 'flex flex-col flex-1' : 'hidden'}>
  <PlaygroundMode brandSlug={brandSlug} />
</div>
```

**Important**: Both modes stay mounted, just hidden via CSS. This prevents:
- Losing draft messages when switching modes
- Interrupting in-flight streaming responses
- Losing scroll position in chat

**Tasks**:
- [ ] Create PanelModeToggle component
- [ ] Add panelMode state to ChatPanel
- [ ] Add toggle to header area
- [ ] Wrap existing chat content in a div with conditional display
- [ ] Add PlaygroundMode component (hidden initially)
- [ ] Verify chat state preserved when switching modes

**Success criteria**: Can toggle between Assistant and Playground modes without losing state

---

### Phase 4: Playground Mode UI
**Goal**: Build the Playground interface (preview canvas, inline controls). Image generation only (no video).

**Files to create**:
- `src/sip_studio/studio/frontend/src/components/ChatPanel/PlaygroundMode/index.tsx`
- `src/sip_studio/studio/frontend/src/components/ChatPanel/PlaygroundMode/PreviewCanvas.tsx`

**Files to modify**: None (uses existing bridge.quickGenerate)

**Key Design Decisions**:
- **Image-only**: No video support (matches existing quick_generate API)
- **Auto-save**: Images save to gallery automatically (matches current Quick Generator behavior)
- **New Generation button**: Clears preview to start fresh (no explicit Save/Discard)
- **LocalStorage validation**: Type guard ensures valid aspect ratio values

**LocalStorage Helpers with Safety**:
```tsx
const VALID_ASPECT_RATIOS = ['1:1','16:9','9:16','4:3','3:4','2:3','3:2','4:5','5:4'] as const
type AspectRatio = typeof VALID_ASPECT_RATIOS[number]

function isValidAspectRatio(v: string): v is AspectRatio {
  return VALID_ASPECT_RATIOS.includes(v as AspectRatio)
}

function getStoredAspectRatio(): AspectRatio {
  try {
    const stored = localStorage.getItem('playground-aspect-ratio')
    return stored && isValidAspectRatio(stored) ? stored : '1:1'
  } catch { return '1:1' }
}

function setStoredAspectRatio(v: AspectRatio): void {
  try { localStorage.setItem('playground-aspect-ratio', v) } catch { /* ignore */ }
}
```

**PreviewCanvas Component**:
```tsx
// Shows aspect-ratio placeholder or generated image (IMAGE ONLY)
// Uses data URL from bridge response (NOT file:// paths)
interface Props {
  aspectRatio: AspectRatio
  isLoading: boolean
  result: { data?: string; path?: string } | null
}

export function PreviewCanvas({ aspectRatio, isLoading, result }: Props) {
  const dims = ASPECT_RATIO_DIMS[aspectRatio] || { w: 1, h: 1 }
  // Use data URL directly (bridge.quickGenerate returns base64 data URL in .data field)
  const imgSrc = result?.data || null

  return (
    <div className="relative w-full max-w-md flex items-center justify-center p-4">
      <div
        className="relative w-full bg-blue-50 dark:bg-blue-900/20 rounded-xl overflow-hidden border-2 border-dashed border-blue-200 dark:border-blue-800"
        style={{ aspectRatio: `${dims.w}/${dims.h}`, maxHeight: '400px' }}
      >
        {imgSrc ? (
          <img src={imgSrc} className="w-full h-full object-cover" alt="Generated" />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <Mountain className="w-16 h-16 text-blue-300 dark:text-blue-700" />
          </div>
        )}
        {isLoading && (
          <div className="absolute inset-0 bg-white/50 dark:bg-black/50 flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          </div>
        )}
        <div className="absolute top-2 right-2 text-xs text-muted-foreground bg-background/80 px-2 py-0.5 rounded">
          Image · {aspectRatio}
        </div>
      </div>
    </div>
  )
}
```

**PlaygroundMode Component**:
```tsx
export function PlaygroundMode({ brandSlug }: { brandSlug: string }) {
  const [prompt, setPrompt] = useState('')
  const [selectedProduct, setSelectedProduct] = useState('')
  const [selectedStyleRef, setSelectedStyleRef] = useState('')
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>(getStoredAspectRatio)
  const [isGenerating, setIsGenerating] = useState(false)
  const [result, setResult] = useState<{path:string;data?:string}|null>(null)
  const [error, setError] = useState<string | null>(null)

  // Brand-aware hooks for products/styles
  const { products } = useProducts(brandSlug)
  const { styleReferences } = useStyleReferences(brandSlug)

  // Reset selections when brandSlug changes
  useEffect(() => { setSelectedProduct(''); setSelectedStyleRef('') }, [brandSlug])

  // Persist aspect ratio using safe setter
  useEffect(() => { setStoredAspectRatio(aspectRatio) }, [aspectRatio])

  const handleGenerate = async () => {
    if (!prompt.trim()) return
    setIsGenerating(true); setError(null); setResult(null)
    try {
      const res = await bridge.quickGenerate(prompt, selectedProduct||undefined, selectedStyleRef||undefined, aspectRatio, 1)
      if (!res.success) { setError(res.error || 'Generation failed'); return }
      if (res.images?.[0]) {
        setResult(res.images[0])
        // Image is already saved to gallery by quickGenerate API
      }
    } catch (e) { setError(String(e)) }
    finally { setIsGenerating(false) }
  }

  const handleNewGeneration = () => { setResult(null); setPrompt('') }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 flex items-center justify-center overflow-hidden">
        <PreviewCanvas aspectRatio={aspectRatio} isLoading={isGenerating} result={result} />
      </div>

      {/* New Generation button (when result exists) */}
      {result && !isGenerating && (
        <div className="flex justify-center py-3">
          <Button variant="outline" onClick={handleNewGeneration}>
            <Plus className="w-4 h-4 mr-2" /> New Generation
          </Button>
        </div>
      )}

      {error && <div className="px-4 pb-2"><Alert variant="destructive">{error}</Alert></div>}

      {/* Controls */}
      <div className="p-4 space-y-3 border-t border-border/20">
        {/* Aspect Ratio only (no video toggle) */}
        <AspectRatioSelector value={aspectRatio} onChange={setAspectRatio} generationMode="image" />

        {/* Product + Style selectors */}
        <div className="flex items-center gap-2">
          <select value={selectedProduct} onChange={e=>setSelectedProduct(e.target.value)}
            className="flex-1 px-3 py-1.5 rounded-lg border border-border/40 text-sm bg-background">
            <option value="">No product</option>
            {products.map(p=><option key={p.slug} value={p.slug}>{p.name}</option>)}
          </select>
          <select value={selectedStyleRef} onChange={e=>setSelectedStyleRef(e.target.value)}
            className="flex-1 px-3 py-1.5 rounded-lg border border-border/40 text-sm bg-background">
            <option value="">No style</option>
            {styleReferences.map(s=><option key={s.slug} value={s.slug}>{s.name}</option>)}
          </select>
        </div>

        {/* Prompt input + generate */}
        <div className="flex items-end gap-2">
          <textarea value={prompt} onChange={e=>setPrompt(e.target.value)}
            placeholder="Describe your image..." rows={2} disabled={isGenerating}
            className="flex-1 px-4 py-3 rounded-xl border border-border/40 resize-none text-sm bg-background" />
          <Button onClick={handleGenerate} disabled={isGenerating||!prompt.trim()} className="px-6">
            {isGenerating ? <Loader2 className="w-4 h-4 animate-spin"/> : <Zap className="w-4 h-4"/>}
          </Button>
        </div>
      </div>
    </div>
  )
}
```

**Tasks**:
- [x] Create PreviewCanvas component with aspect-ratio placeholder
- [x] Create PlaygroundMode component (image-only)
- [x] Add LocalStorage type guard for aspect ratio validation
- [x] Wire up to existing bridge.quickGenerate
- [x] Add "New Generation" button to clear and start fresh
- [x] Handle loading state with spinner overlay
- [x] Handle errors with Alert component
- [x] Style to match app aesthetic

**Success criteria**:
- Can generate images in Playground
- Preview canvas shows aspect ratio placeholder
- Loading spinner during generation
- Result appears in canvas (auto-saved to gallery)
- "New Generation" clears for next prompt

---

### Phase 5: Assistant Mode Refinements
**Goal**: Move autonomy toggle near input area

**Files to modify**:
- `src/sip_studio/studio/frontend/src/components/ChatPanel/index.tsx`

**Implementation**:
```tsx
// ChatPanel/index.tsx changes:

// 1. Remove AutonomyToggle from header (around line 371)
// DELETE: <AutonomyToggle enabled={autonomyMode} onChange={handleSetAutonomyMode} disabled={isLoading || !brandSlug} />

// 2. Add AutonomyToggle near input area, in the Mode Toggle + Aspect Ratio section
<div className="px-4 max-w-3xl mx-auto w-full flex items-center gap-3">
  <ModeToggle ... />
  <AspectRatioSelector ... />
  <div className="flex-1" /> {/* Spacer */}
  <AutonomyToggle
    enabled={autonomyMode}
    onChange={handleSetAutonomyMode}
    disabled={isLoading || !brandSlug}
  />
</div>
```

**Tasks**:
- [x] Remove AutonomyToggle from header
- [x] Add AutonomyToggle to input area row
- [x] Adjust styling for inline appearance
- [x] Test appearance and functionality

**Success criteria**: Autonomy toggle visible near input, not in header

---

### Phase 6: Remove Old Quick Generator
**Goal**: Clean up deprecated components

**Files to modify**:
- `src/sip_studio/studio/frontend/src/App.tsx`

**Files to potentially delete/archive**:
- `src/sip_studio/studio/frontend/src/components/QuickGenerator/QuickGeneratorFAB.tsx`
- `src/sip_studio/studio/frontend/src/components/QuickGenerator/index.tsx`
- `src/sip_studio/studio/frontend/src/components/QuickGenerator/QuickGenerator.css`
- (Keep GeneratorForm.tsx and ResultsGrid.tsx if useful for reference)

**Implementation**:
```tsx
// App.tsx changes:

// 1. Remove state
// DELETE: const [quickGenOpen, setQuickGenOpen] = useState(false)

// 2. Remove FAB
// DELETE: {activeBrand && <QuickGeneratorFAB onClick={() => setQuickGenOpen(true)} disabled={!activeBrand} />}

// 3. Remove modal
// DELETE: {quickGenOpen && activeBrand && (<QuickGenerator brandSlug={activeBrand} onClose={() => setQuickGenOpen(false)} />)}

// 4. Remove import
// DELETE: import { QuickGenerator, QuickGeneratorFAB } from '@/components/QuickGenerator'
```

**Tasks**:
- [x] Remove quickGenOpen state from App.tsx
- [x] Remove QuickGeneratorFAB from App.tsx
- [x] Remove QuickGenerator modal from App.tsx
- [x] Remove import statement
- [x] Archive or delete QuickGenerator component files

**Success criteria**: No FAB, no modal, clean App.tsx

---

### Phase 7: Polish and Integration Testing
**Goal**: Ensure everything works together smoothly

**Tasks**:
- [ ] Test sidebar hover/collapse behavior
  - Starts collapsed (72px)
  - Expands on hover as overlay (no content shift)
  - Stays expanded when focus is within (keyboard accessible)
  - Collapses when mouse leaves (200ms delay)
  - Animations are smooth
- [ ] Test mode switching
  - Toggle between Assistant/Playground
  - Chat state preserved when switching (messages, scroll, draft)
  - Always starts in Assistant mode
- [ ] Test Playground generation flow (IMAGE ONLY)
  - Prompt input works
  - Product/Style selectors work (reset when brand changes)
  - Aspect ratio selector works
  - Generate button works
  - Loading spinner shows on canvas
  - Result appears (auto-saved to gallery)
  - "New Generation" button clears for next prompt
- [ ] Test Assistant mode with new layout
  - Chat is readable with expanded width
  - All existing features work
  - Autonomy toggle near input
- [ ] Test aspect ratio selector in Playground
  - Remembers last selection across sessions
  - All valid ratios work
- [ ] Verify settings persistence
  - Playground aspect ratio remembered (localStorage)
  - Sidebar collapsed state remembered
- [ ] Visual polish
  - Consistent spacing
  - Smooth transitions
  - Dark mode support
  - No layout shift on sidebar expand
- [ ] Fix any regressions
  - Run `cd src/sip_studio/studio/frontend && npm run build` - must succeed
  - Run `cd src/sip_studio/studio/frontend && npm run lint` - no errors
  - Run `python -m pytest tests/` - all tests pass
  - Run `ruff check src/` - no linting errors

**Success criteria**:
- All features work
- UI feels cohesive and polished
- No regressions
