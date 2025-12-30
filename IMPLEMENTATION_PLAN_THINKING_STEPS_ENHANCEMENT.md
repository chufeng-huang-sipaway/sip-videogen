# Implementation Plan: Enhance ThinkingSteps with Value-Add Details

**[Codex Review 3/3]**

## Problem Summary

The current ThinkingSteps implementation shows high-level reasoning ("Understanding request", "Composing scene") but lacks the **value-add details** that demonstrate why using the agent is better than prompting directly:
- What skills were loaded and how they helped
- How the prompt was enriched (product specs, template constraints)
- What the final prompt looks like
- What was sent to the API

Additionally, there's UI redundancy (old ExecutionTrace) and alignment issues.

## User Decisions
- **Prompt display**: Diff-style - show what was ADDED vs original (most informative)
- **Generation details**: Inside ThinkingSteps as the final expandable step

## Architecture Overview

```
ThinkingSteps Component (enhanced)
├── Skills Section (top) - chips showing loaded skills
├── Agent Thinking Steps - from report_thinking tool calls
├── Prompt Enhancement Step - diff showing original → additions (from metadata)
└── Generation Details Step - API summary (from metadata)
```

## Data Schemas (Confirmed)

### Backend Progress Response (`get_progress()` - chat_service.py:54-56)
```python
# Backend returns:
return bridge_ok({
  "status": self._state.current_progress,
  "type": self._state.current_progress_type,
  "skills": self._state.matched_skills,      # Field name is "skills"
  "thinking_steps": self._state.thinking_steps
})
```

### Frontend Types (bridge.ts:31-36, 313-333)
```typescript
export interface ProgressStatus {
  status: string
  type: ActivityEventType
  skills: string[]                    // Matches backend "skills" field
  thinking_steps: ThinkingStep[]
}

export interface ImageGenerationMetadata {
  prompt: string
  original_prompt?: string            // Optional, may be undefined
  model: string
  aspect_ratio: string
  image_size: string
  reference_image: string | null
  reference_images?: string[]
  reference_images_detail?: ReferenceImageDetail[]
  product_slugs: string[]
  validate_identity: boolean
  validation_passed?: boolean | null
  validation_warning?: string | null
  validation_attempts?: number | null
  final_attempt_number?: number | null
  attempts?: GenerationAttemptMetadata[] | null
  request_payload?: Record<string, unknown> | null
  generated_at: string
  generation_time_ms: number
  api_call_code: string
}
```

**Key confirmation**: Field names already match between backend and frontend (snake_case throughout).

### Prompt Structure
When validation runs, `prompt` contains `original_prompt` + additions:
```
{original_prompt}

[IDENTITY REQUIREMENT - Attempt N]
- improvement 1
- improvement 2
```

---

## Stage 1: Remove Redundant ExecutionTrace (Conditional)

**Goal**: Hide old "View activity (X steps)" when ThinkingSteps is present

**Files**:
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/MessageList.tsx`

**Changes**:
```tsx
// Only show ExecutionTrace if NO thinkingSteps exist (fallback for non-report_thinking flows)
{message.role === 'assistant' &&
 message.executionTrace &&
 message.executionTrace.length > 0 &&
 (!message.thinkingSteps || message.thinkingSteps.length === 0) && (
  <div className="mt-2 w-full"><ExecutionTrace events={message.executionTrace} /></div>
)}
```

**Note**: This preserves ExecutionTrace for flows that don't use `report_thinking` (e.g., brand analysis).

**Success Criteria**:
- [ ] ExecutionTrace hidden when thinkingSteps exist
- [ ] ExecutionTrace still shows for flows without report_thinking
- [ ] Frontend builds without errors

**Status**: Not Started

---

## Stage 2: Fix "Working..." Alignment

**Goal**: Align the "Working..." indicator with step items

**Files**:
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/ThinkingSteps.tsx`

**Changes**:
Line 15, remove `pl-6`:
```tsx
<div className="flex items-center gap-2 text-sm text-muted-foreground">
```

**Success Criteria**:
- [ ] "Working..." indicator aligns with step items above it

**Status**: Not Started

---

## Stage 3: Add Skills Display (Message-Scoped)

**Goal**: Show loaded skills as chips at the top of ThinkingSteps

**Codex Feedback Addressed**:
- Skills tracked per-message (not global) to avoid leakage
- Use `useRef` + state sync to avoid stale closures in async polling

**Files**:
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/ThinkingSteps.tsx`
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/MessageList.tsx`
- `src/sip_videogen/studio/frontend/src/hooks/useChat.ts`

### 3.1 Update ThinkingSteps Props
```tsx
interface Props {
  steps: ThinkingStep[]
  isGenerating: boolean
  skills?: string[]  // NEW
}
```

### 3.2 Render Skills Section (with overflow handling)
```tsx
{skills && skills.length > 0 && (
  <div className="flex flex-wrap gap-1.5 mb-2 overflow-x-auto">
    {skills.slice(0, 5).map((skill) => (
      <span key={skill} className="text-[9px] uppercase tracking-wider text-muted-foreground border border-border/40 px-1.5 py-0.5 rounded-sm whitespace-nowrap">
        {skill.length > 25 ? skill.slice(0, 22) + '...' : skill}
      </span>
    ))}
    {skills.length > 5 && (
      <span className="text-[9px] text-muted-foreground">+{skills.length - 5} more</span>
    )}
  </div>
)}
```

### 3.3 Add loadedSkills to Message Interface (useChat.ts)
```tsx
export interface Message {
  // ... existing fields
  loadedSkills?: string[]  // NEW
}
```

### 3.4 Track Skills with useRef (Closure-Safe)
```tsx
// At hook level (NOT inside sendMessage):
const [loadedSkills, setLoadedSkills] = useState<string[]>([])
const loadedSkillsRef = useRef<string[]>([])  // Closure-safe reference

// In sendMessage function:
// Clear at start
setLoadedSkills([])
loadedSkillsRef.current = []

// In polling loop, accumulate skills (closure-safe via ref):
if (data.skills && data.skills.length > 0) {
  const newSkills = data.skills.filter((s: string) => !loadedSkillsRef.current.includes(s))
  if (newSkills.length > 0) {
    loadedSkillsRef.current = [...loadedSkillsRef.current, ...newSkills]
    setLoadedSkills([...loadedSkillsRef.current])  // Sync state for UI
  }
}

// Persist on message completion (use ref for latest values):
setMessages(prev => prev.map(m =>
  m.id === assistantId
    ? {
        ...m,
        loadedSkills: loadedSkillsRef.current.length > 0 ? [...loadedSkillsRef.current] : undefined
      }
    : m
))
```

### 3.5 Pass Skills to ThinkingSteps for BOTH Loading and Completed
```tsx
// During loading (MessageList):
<ThinkingSteps steps={thinkingSteps} isGenerating={true} skills={loadedSkills} />

// On completed message (MessageBubble):
<ThinkingSteps steps={message.thinkingSteps || []} isGenerating={false} skills={message.loadedSkills} />
```

**Success Criteria**:
- [ ] Skills appear as chips above thinking steps during generation
- [ ] Skills persist on completed messages
- [ ] Skills clear when starting new message
- [ ] Long skill names truncated, overflow handled
- [ ] No skill leakage between concurrent messages

**Status**: Complete

---

## Stage 4: Create PromptDiff Component

**Goal**: Show what was ADDED to the original prompt in diff-style

**Codex Feedback Addressed**:
- Handle whitespace-only originals as missing
- Handle identical prompts (no additions) explicitly
- Remove unused `before` variable

**Files**:
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/PromptDiff.tsx` (NEW)

**Component Design**:
```tsx
interface Props {
  originalPrompt: string
  finalPrompt: string
}

export function PromptDiff({ originalPrompt, finalPrompt }: Props) {
  // Normalize and handle edge cases
  const origTrim = (originalPrompt || '').trim()
  const finalTrim = (finalPrompt || '').trim()

  // Edge case: both empty/whitespace
  if (!origTrim && !finalTrim) return null

  // Edge case: no final prompt
  if (!finalTrim) {
    return <div className="text-xs text-muted-foreground">No prompt generated</div>
  }

  // Edge case: no original prompt (treat whitespace-only as missing)
  if (!origTrim) {
    return (
      <div className="text-xs">
        <span className="text-green-600">+ {truncate(finalTrim, 400)}</span>
      </div>
    )
  }

  // Edge case: identical prompts (no additions)
  if (origTrim === finalTrim) {
    return (
      <div className="text-xs">
        <div className="text-muted-foreground">No modifications made to prompt</div>
        <div className="mt-1">{truncate(origTrim, 200)}</div>
      </div>
    )
  }

  // Check if original is contained in final (common case)
  if (finalTrim.includes(origTrim)) {
    const afterIdx = finalTrim.indexOf(origTrim) + origTrim.length
    const additions = finalTrim.slice(afterIdx).trim()

    return (
      <div className="text-xs space-y-2">
        <div>
          <span className="text-muted-foreground">Original:</span>
          <span className="ml-2">{truncate(origTrim, 200)}</span>
        </div>
        {additions && (
          <div className="text-green-600 dark:text-green-400 whitespace-pre-wrap">
            <span className="font-medium">+ Added:</span>
            <div className="pl-4">{truncate(additions, 500)}</div>
          </div>
        )}
      </div>
    )
  }

  // Prompts don't overlap (rewritten case) - show both
  return (
    <div className="text-xs space-y-2">
      <div>
        <span className="text-muted-foreground">Original:</span>
        <div className="pl-4">{truncate(origTrim, 200)}</div>
      </div>
      <div>
        <span className="text-muted-foreground">Final (rewritten):</span>
        <div className="pl-4">{truncate(finalTrim, 300)}</div>
      </div>
    </div>
  )
}

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + '...' : s
}
```

**Edge Cases Handled**:
- Empty/whitespace original_prompt → show final only
- Empty/whitespace final_prompt → show "No prompt generated"
- Identical prompts → show "No modifications made"
- Original not in final (rewritten) → show both with "rewritten" label
- Very long prompts → truncated with ellipsis

**Success Criteria**:
- [ ] Component renders original prompt
- [ ] Component highlights additions clearly
- [ ] Handles all edge cases gracefully
- [ ] Long prompts truncated appropriately
- [ ] No unused variables

**Status**: Not Started

---

## Stage 5: Create GenerationSummary Component

**Goal**: Show API call summary as compact info

**Codex Feedback Addressed**:
- Add `type="button"` to prevent form submit
- Add validation attempts/warnings (matches Stage 7 test expectations)
- Only show "View full API call" if api_call_code exists

**Files**:
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/GenerationSummary.tsx` (NEW)

**Component Design**:
```tsx
import type { ImageGenerationMetadata } from '@/lib/bridge'

interface Props {
  metadata: ImageGenerationMetadata
  onViewFullDetails?: () => void
}

export function GenerationSummary({ metadata, onViewFullDetails }: Props) {
  const refCount = metadata.reference_images?.length || (metadata.reference_image ? 1 : 0)
  const genTime = metadata.generation_time_ms
    ? `${(metadata.generation_time_ms / 1000).toFixed(1)}s`
    : null

  return (
    <div className="text-xs space-y-1">
      {metadata.model && (
        <div><span className="text-muted-foreground">Model:</span> {metadata.model}</div>
      )}
      {metadata.aspect_ratio && (
        <div><span className="text-muted-foreground">Aspect ratio:</span> {metadata.aspect_ratio}</div>
      )}
      {refCount > 0 && (
        <div><span className="text-muted-foreground">Reference images:</span> {refCount}</div>
      )}
      {metadata.product_slugs && metadata.product_slugs.length > 0 && (
        <div>
          <span className="text-muted-foreground">Products:</span>{' '}
          {metadata.product_slugs.join(', ')} <span className="text-green-500">✓</span>
        </div>
      )}
      {genTime && (
        <div><span className="text-muted-foreground">Generation time:</span> {genTime}</div>
      )}
      {/* Validation info (if multiple attempts were made) */}
      {metadata.validation_attempts != null && metadata.validation_attempts > 1 && (
        <div>
          <span className="text-muted-foreground">Validation attempts:</span> {metadata.validation_attempts}
          {metadata.validation_passed === true && <span className="text-green-500 ml-1">✓ passed</span>}
          {metadata.validation_passed === false && <span className="text-yellow-500 ml-1">⚠ warnings</span>}
        </div>
      )}
      {metadata.validation_warning && (
        <div className="text-yellow-600 dark:text-yellow-400 text-xs">
          ⚠ {metadata.validation_warning}
        </div>
      )}
      {/* Only show if api_call_code exists */}
      {onViewFullDetails && metadata.api_call_code && (
        <button
          type="button"
          onClick={onViewFullDetails}
          className="text-primary hover:underline mt-1"
        >
          View full API call →
        </button>
      )}
    </div>
  )
}
```

**Success Criteria**:
- [ ] Shows model, aspect ratio, reference image count
- [ ] Shows injected products if any
- [ ] Shows generation time if available
- [ ] Shows validation attempts/warnings if present
- [ ] Links to PromptDetailsModal only if api_call_code exists
- [ ] Gracefully handles missing fields
- [ ] Button has type="button"

**Status**: Not Started

---

## Stage 6: Integrate Metadata into ThinkingSteps

**Goal**: Add prompt diff and generation summary as expandable steps

**Codex Feedback Addressed**:
- Synthetic step IDs namespaced to avoid collision
- StepItem updated for custom expanded content
- Stable React keys
- Per-message modal wiring
- Guard against missing metadata on images
- **Fix #2**: Update early-return logic so metadata steps render even when thinkingSteps is empty
- **Fix #3**: Normalize image types before accessing `.metadata`
- **Fix #6**: Modal state at parent (MessageList) level, not inside map loop

**Files**:
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/ThinkingSteps.tsx`
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/MessageList.tsx`

### 6.1 Update ThinkingSteps Props
```tsx
import type { ImageGenerationMetadata } from '@/lib/bridge'

interface Props {
  steps: ThinkingStep[]
  isGenerating: boolean
  skills?: string[]
  imageMetadata?: ImageGenerationMetadata | null  // NEW
  onViewFullDetails?: () => void  // NEW
}
```

### 6.2 Fix Early Return Logic (Fix #2)

**Problem**: Current code returns `null` when `steps.length === 0 && !isGenerating`, preventing metadata steps from rendering.

**Solution**: Check for imageMetadata before early-returning:
```tsx
export function ThinkingSteps({ steps, isGenerating, skills, imageMetadata, onViewFullDetails }: Props) {
  // Only show spinner if generating with no steps AND no metadata
  if (steps.length === 0 && !imageMetadata) {
    if (!isGenerating) return null
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Processing...</span>
      </div>
    )
  }

  // Rest of component renders steps + metadata steps...
}
```

### 6.3 Update StepItem to Support Custom Expanded Content
```tsx
function StepItem({
  step,
  expandedContent
}: {
  step: ThinkingStep
  expandedContent?: React.ReactNode
}) {
  const [exp, setExp] = useState(false)
  const hasContent = Boolean(step.detail || expandedContent)

  return (
    <div className="text-sm">
      <button
        type="button"
        onClick={() => hasContent && setExp(!exp)}
        className={`flex items-center gap-2 w-full text-left ${hasContent ? 'hover:bg-muted/50 cursor-pointer' : ''} rounded px-1 py-0.5 transition-colors`}
      >
        <CheckCircle2 className="h-3 w-3 text-green-500 flex-shrink-0" />
        <span className="font-medium text-foreground">{step.step}</span>
        {hasContent && (
          exp ? <ChevronDown className="h-3 w-3 text-muted-foreground ml-auto" />
               : <ChevronRight className="h-3 w-3 text-muted-foreground ml-auto" />
        )}
      </button>
      {exp && (
        <div className="pl-6 pr-2 py-1">
          {expandedContent || (step.detail && (
            <div className="text-muted-foreground text-xs">{step.detail}</div>
          ))}
        </div>
      )}
    </div>
  )
}
```

### 6.4 Add Metadata Steps After Agent Steps
```tsx
export function ThinkingSteps({ steps, isGenerating, skills, imageMetadata, onViewFullDetails }: Props) {
  // ... early return logic from 6.2 ...
  // ... skills rendering ...
  // ... steps.map() ...

  {/* Metadata-based steps - only show when NOT generating and metadata exists */}
  {!isGenerating && imageMetadata && (
    <>
      <StepItem
        key="synthetic-prompt-diff"
        step={{ id: 'synthetic-prompt-diff', step: 'Prompt enhancement', detail: '', timestamp: 0 }}
        expandedContent={
          <PromptDiff
            originalPrompt={imageMetadata.original_prompt || ''}
            finalPrompt={imageMetadata.prompt || ''}
          />
        }
      />
      <StepItem
        key="synthetic-gen-details"
        step={{ id: 'synthetic-gen-details', step: 'Generation details', detail: '', timestamp: 0 }}
        expandedContent={
          <GenerationSummary
            metadata={imageMetadata}
            onViewFullDetails={onViewFullDetails}
          />
        }
      />
    </>
  )}
}
```

### 6.5 Image Type Normalization (Fix #3)

**Problem**: `message.images` type is `GeneratedImage[] | string[]`, so direct `.metadata` access fails TypeScript.

**Solution**: Normalize images before accessing metadata:
```tsx
import type { GeneratedImage } from '@/lib/bridge'

// Helper to normalize images (can be shared utility)
function normalizeImages(images: (GeneratedImage | string)[] | undefined): GeneratedImage[] {
  if (!images) return []
  return images.map(img => typeof img === 'string' ? { url: img } : img)
}

// Usage in MessageList:
const normalizedImages = normalizeImages(message.images)
const firstImageMetadata = normalizedImages[0]?.metadata ?? null
```

### 6.6 Modal State at Parent Level (Fix #6)

**Problem**: If modal state is declared inside `.map()`, each message gets its own state (wasteful, buggy).

**Solution**: Declare modal state at `MessageList` component level (OUTSIDE the map loop):

```tsx
// MessageList.tsx - at component level, NOT inside messages.map()
export function MessageList({ messages, ... }: Props) {
  // Modal state lives here at parent level
  const [promptDetailsMessage, setPromptDetailsMessage] = useState<Message | null>(null)
  const [showPromptDetails, setShowPromptDetails] = useState(false)

  return (
    <div>
      {messages.map((message) => {
        // Normalize images for THIS message
        const normalizedImages = normalizeImages(message.images)
        const firstImageMetadata = normalizedImages[0]?.metadata ?? null

        // Determine if we should show ThinkingSteps
        const hasThinkingContent = (message.thinkingSteps && message.thinkingSteps.length > 0) || firstImageMetadata

        return (
          <div key={message.id}>
            {/* ... other message content ... */}

            {message.role === 'assistant' && hasThinkingContent && (
              <ThinkingSteps
                steps={message.thinkingSteps || []}
                isGenerating={false}
                skills={message.loadedSkills}
                imageMetadata={firstImageMetadata}
                onViewFullDetails={() => {
                  setPromptDetailsMessage(message)  // Captures THIS message
                  setShowPromptDetails(true)
                }}
              />
            )}
          </div>
        )
      })}

      {/* Modal rendered ONCE at parent level, uses captured message */}
      {showPromptDetails && promptDetailsMessage && (
        <PromptDetailsModal
          metadata={normalizeImages(promptDetailsMessage.images)[0]?.metadata ?? null}
          onClose={() => setShowPromptDetails(false)}
        />
      )}
    </div>
  )
}
```

### 6.7 Multi-Image Handling
For messages with multiple images, show first image metadata with indication:
```tsx
{normalizedImages.length > 1 && firstImageMetadata && (
  <div className="text-xs text-muted-foreground mt-1">
    Showing metadata for image 1 of {normalizedImages.length}
  </div>
)}
```

**Success Criteria**:
- [ ] Prompt enhancement step shows diff-style additions
- [ ] Generation details step shows API summary with validation info
- [ ] "View full API call" opens correct message's PromptDetailsModal
- [ ] Steps only appear when image metadata exists (not during generation)
- [ ] All steps are collapsible/expandable
- [ ] Synthetic step IDs don't collide with real step UUIDs
- [ ] Multi-image messages show clear indication
- [ ] Missing metadata on images handled gracefully (null guard)
- [ ] **Fix #2**: Metadata steps render even when thinkingSteps is empty
- [ ] **Fix #3**: Image type normalization prevents TypeScript errors
- [ ] **Fix #6**: Modal state at parent level, correct message opens

**Status**: Complete

---

## Stage 7: Testing and Polish

**Goal**: Verify all flows work correctly

**Test Cases**:
1. Simple image generation:
   - [ ] Shows 2+ thinking steps
   - [ ] Shows prompt enhancement with additions
   - [ ] Shows generation details

2. Image with product reference:
   - [ ] Shows product injection in diff
   - [ ] Shows products in generation details with ✓

3. Image with validation attempts > 1:
   - [ ] Shows `[IDENTITY REQUIREMENT - Attempt N]` additions in diff
   - [ ] Shows validation_attempts count in generation details
   - [ ] Shows validation_warning if present

4. Multiple variations:
   - [ ] Shows "metadata for image 1 of N" indicator
   - [ ] First image metadata used for shared display

5. Non-image flows (e.g., brand analysis):
   - [ ] ExecutionTrace still shows (fallback)
   - [ ] No prompt/generation steps (no metadata)

6. Edge cases:
   - [ ] No images generated → no metadata steps
   - [ ] Identical prompts → "No modifications made"
   - [ ] No skills loaded → no skills section
   - [ ] Very long prompts → truncated
   - [ ] Missing metadata fields → graceful degradation
   - [ ] Images without metadata → handled (null guard)

7. State management:
   - [ ] Skills update during generation
   - [ ] Skills persist after completion
   - [ ] Correct modal opens for clicked message (not stale)
   - [ ] Expand/collapse state stable on re-renders
   - [ ] No skill leakage between messages

**Status**: Not Started

---

## Files Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `frontend/src/components/ChatPanel/ThinkingSteps.tsx` | Modify | Fix alignment, add skills, add metadata display, synthetic steps |
| `frontend/src/components/ChatPanel/MessageList.tsx` | Modify | Conditional ExecutionTrace, pass skills + metadata, modal wiring |
| `frontend/src/hooks/useChat.ts` | Modify | Add loadedSkills to Message, track with useRef, persist |
| `frontend/src/components/ChatPanel/PromptDiff.tsx` | Create | Diff-style prompt enhancement display |
| `frontend/src/components/ChatPanel/GenerationSummary.tsx` | Create | API call summary display with validation info |

---

## UI Mockup (After Changes)

```
┌─────────────────────────────────────────────────────────────────┐
│ IMAGE-PROMPT-ENGINEERING   IMAGE-COMPOSER                       │  ← Skills
├─────────────────────────────────────────────────────────────────┤
│ ✓ Understanding request                                    [▸]  │  ← Agent steps
│ ✓ Composing scene                                          [▸]  │
│ ✓ Prompt enhancement                                       [▾]  │  ← Synthetic
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ Original: "a lifestyle image of this product..."        │   │
│   │ + Added:                                                │   │
│   │   [IDENTITY REQUIREMENT - Attempt 1]                    │   │
│   │   - Object must maintain exact visual identity...       │   │
│   └─────────────────────────────────────────────────────────┘   │
│ ✓ Generation details                                       [▾]  │  ← Synthetic
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ Model: gemini-3-pro-image-preview                       │   │
│   │ Aspect ratio: 1:1                                       │   │
│   │ Reference images: 3                                     │   │
│   │ Products: morning-complete ✓                            │   │
│   │ Generation time: 4.2s                                   │   │
│   │ Validation attempts: 2 ✓ passed                         │   │
│   │ [View full API call →]                                  │   │
│   └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│ Showing metadata for image 1 of 3                               │  ← Multi-image
│ Generated 3 images                                              │
│ [image thumbnails]                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Dependencies

**No new npm dependencies required.**
- Prompt diff uses simple string matching based on known format
- Backend already provides `skills` in progress response (confirmed in chat_service.py:54-56)
- Frontend `ImageGenerationMetadata` type already exists in bridge.ts:313-333 (snake_case, matches backend)
- `images[].metadata` populated via `encode_new_images()` in chat_service.py:44

---

## Out of Scope

- Changing PromptDetailsModal (keep for detailed view)
- Changing backend metadata capture (already comprehensive)
- Real-time prompt diff during generation (only shown after completion)
- Character-level diff algorithm (simple block-based is sufficient)
- Image selector for multi-image metadata (future enhancement)

---

## Codex Unresolved Comments (Review 3/3)

The following minor feedback from the final Codex review can be addressed during implementation if needed:

### 1. ActivityCard Skills Duplication (Verify First)
- **Issue**: `ActivityCard` may show skills; if so, there could be duplicate skill chips.
- **Resolution**: During implementation, check if `ActivityCard` renders skills. If so, hide it when `ThinkingSteps` is shown.
- **Note**: Likely a false positive - need to verify `ActivityCard` exists and shows skills.

### 2. PromptDiff Matching Precision (Minor)
- **Issue**: `finalTrim.includes(origTrim)` can mis-detect if original is a common substring.
- **Resolution**: Consider using `finalTrim.startsWith(origTrim)` for more precise matching.
- **Note**: Low risk since original prompt is typically a full sentence.

### 3. Expand/Collapse State Toggle (Minor)
- **Issue**: `setExp(!exp)` can flip incorrectly under batched updates.
- **Resolution**: Use functional update: `setExp(prev => !prev)`
- **Note**: Very low risk for single-click toggles.

### 4. First Image Metadata Search (Minor)
- **Issue**: First image may lack metadata even if later images have it.
- **Resolution**: Consider `normalizedImages.find(img => img.metadata)?.metadata`
- **Note**: Edge case - first image almost always has metadata.

---

**Resolved in Stage 6:**
- ~~#2 Metadata steps when thinkingSteps empty~~ → Stage 6.2
- ~~#3 Image type normalization~~ → Stage 6.5
- ~~#6 Modal state location~~ → Stage 6.6
