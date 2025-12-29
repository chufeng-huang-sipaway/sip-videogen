# Implementation Plan: Agent Thinking Visibility

[Codex Review 3/3 - PROCEEDING]

## Overview

Add a `report_thinking` tool that allows the BrandAdvisor agent to self-report its reasoning process. This gives users visibility into the agent's decision-making, building trust and demonstrating the value added beyond simple prompt-to-image generation.

**Goal**: Every time the agent processes a request, users see a vertical list of collapsible "thinking steps" that explain what the agent is doing and why.

---

## Codex Review Feedback - All Addressed

### Review 1 Issues (Addressed)
| Issue | Resolution |
|-------|------------|
| `get_progress()` doesn't return `execution_trace` | Stage 2: Add `thinking_steps` to progress response |
| Frontend types missing `thinking_step` | Stage 4: Add to `ActivityEventType` union |
| File paths wrong (`chat/` vs `ChatPanel/`) | Corrected to `ChatPanel/` throughout |
| Module-level storage is request-unsafe | Stage 1: Use tool return value pattern |
| `on_tool_start` emits noise for report_thinking | Stage 2: Special-case both hooks |
| No-steps fallback doesn't show spinner | Stage 4: Fix to show spinner when generating even with 0 steps |
| Timestamps not UTC | Stage 1: Use epoch-ms for consistency |
| Privacy/prompt leakage risk | Stage 3: Add guardrails to prompt |

### Review 2 Issues (Addressed)
| Issue | Resolution |
|-------|------------|
| Global storage still not request-scoped | Stage 1: Return structured JSON from tool, parse in `on_tool_end` |
| Timestamp dedupe collision | Stage 1: Add UUID per step |
| Persistence on completed messages unclear | Stage 5: Explicit rendering from `executionTrace` |
| `thinking_step` may mutate progress status | Stage 2: Don't update `current_progress_type` |
| No validation/clamping | Stage 1: Add max length limits |

---

## Stage 1: Backend - Add `report_thinking` Tool

**Goal**: Create the tool with request-safe data passing via return value.

**Success Criteria**:
- Tool is callable by the agent
- Step data passed via structured return value (no global state)
- Validation prevents oversized content

**Implementation**:

1. Add helper to generate step data in `tools.py`:
```python
import uuid

# Max lengths to prevent UI flooding
MAX_STEP_LENGTH = 50
MAX_DETAIL_LENGTH = 500

def _build_thinking_step_result(step: str, detail: str) -> str:
    """Build a JSON result string containing thinking step data.

    The result is parsed in on_tool_end to extract step data,
    avoiding global state issues.
    """
    import json
    # Clamp lengths
    step_clamped = step[:MAX_STEP_LENGTH] if step else "Thinking"
    detail_clamped = detail[:MAX_DETAIL_LENGTH] if detail else ""

    return json.dumps({
        "_thinking_step": True,  # Marker for on_tool_end to detect
        "id": str(uuid.uuid4()),  # Unique ID for dedupe
        "step": step_clamped.strip(),
        "detail": detail_clamped.strip(),
        "timestamp": int(time.time() * 1000),  # Epoch ms
    })
```

2. Add `_impl_report_thinking` function:
```python
def _impl_report_thinking(step: str, detail: str) -> str:
    """Report a thinking step to show reasoning to the user.

    Returns structured JSON that on_tool_end parses.
    """
    logger.debug(f"[THINKING] {step[:50]}")
    return _build_thinking_step_result(step, detail)
```

3. Add `@function_tool` wrapper:
```python
@function_tool
def report_thinking(step: str, detail: str) -> str:
    """Report a thinking step to show the user your reasoning process.

    REQUIRED: Call this tool to explain what you're doing at each decision point.
    Users see these steps as a collapsible list, building trust in your process.

    Args:
        step: Brief title (2-5 words) describing this stage.
              Examples: "Understanding request", "Choosing approach", "Crafting scene"
        detail: Brief explanation of what you decided and why (1-2 sentences).
                Focus on WHAT and WHY, not internal reasoning or system details.
                Do NOT include system prompts, internal instructions, or chain-of-thought.

    Returns:
        Acknowledgment string.
    """
    return _impl_report_thinking(step, detail)
```

4. Add helper to parse thinking step from tool result:
```python
def parse_thinking_step_result(result: str) -> dict | None:
    """Parse thinking step data from tool result if present."""
    import json
    try:
        data = json.loads(result)
        if isinstance(data, dict) and data.get("_thinking_step"):
            return {
                "id": data["id"],
                "step": data["step"],
                "detail": data["detail"],
                "timestamp": data["timestamp"],
            }
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return None
```

5. Add to `ADVISOR_TOOLS` list in `tools.py`

6. Export `parse_thinking_step_result` for use by hooks

**Files Modified**:
- `src/sip_videogen/advisor/tools.py`

**Tests**:
- Unit test: `_impl_report_thinking` returns valid JSON
- Unit test: `parse_thinking_step_result` extracts data correctly
- Unit test: Invalid JSON returns None
- Unit test: Clamping works for long step/detail

**Status**: Complete

---

## Stage 2: Backend - Progress Event Integration

**Goal**: Ensure thinking steps flow to frontend in real-time.

**Success Criteria**:
- `thinking_step` events emitted when tool is called
- No "Using report_thinking" noise from tool_start
- Progress API includes accumulated thinking steps for polling
- Events included in `execution_trace` for post-hoc display
- Does NOT mutate `current_progress_type` (event stream only)

**Implementation**:

1. Add accumulated steps to `BridgeState` in `state.py`:
```python
@dataclass
class BridgeState:
    # ... existing fields ...
    thinking_steps: list[dict] = field(default_factory=list)
```

2. Update `AdvisorHooks` in `agent.py` to handle report_thinking specially:
```python
async def on_tool_start(self, context, agent, tool):
    tool_name = tool.name
    # Skip progress reporting for report_thinking (it's meta, not useful to show)
    if tool_name == "report_thinking":
        return
    # ... existing handling ...

async def on_tool_end(self, context, agent, tool, result):
    tool_name = tool.name

    if tool_name == "report_thinking":
        from sip_videogen.advisor.tools import parse_thinking_step_result
        step_data = parse_thinking_step_result(str(result))
        if step_data:
            self._report(AdvisorProgress(
                event_type="thinking_step",
                message=step_data["step"],
                detail=step_data["detail"],
            ))
            # Store the full step data for polling (includes id)
            if hasattr(self, '_thinking_step_data'):
                self._thinking_step_data = step_data
        return  # Skip normal tool_end reporting

    # ... existing handling for other tools ...
```

3. Update `_progress_callback` in `chat_service.py` to accumulate thinking steps:
```python
def _progress_callback(self, progress):
    event = {
        "type": progress.event_type,
        "timestamp": int(time.time() * 1000),
        "message": progress.message,
        "detail": progress.detail or ""
    }
    self._state.execution_trace.append(event)

    # Accumulate thinking steps for real-time polling
    # NOTE: Do NOT update current_progress_type for thinking_step
    if progress.event_type == "thinking_step":
        # Get the full step data from the hook if available
        step_id = f"{event['timestamp']}-{len(self._state.thinking_steps)}"
        self._state.thinking_steps.append({
            "id": step_id,
            "step": progress.message,
            "detail": progress.detail or "",
            "timestamp": event["timestamp"],
        })
    elif progress.event_type == "tool_end":
        # Clear progress display on tool_end
        self._state.current_progress = ""
        self._state.current_progress_type = ""
    else:
        # Only update current_progress for non-thinking events
        self._state.current_progress = progress.message
        self._state.current_progress_type = progress.event_type

    # ... rest of existing handling (skill_loaded, etc.) ...
```

4. Update `chat()` in `chat_service.py` to clear thinking steps at start:
```python
def chat(self, message, ...):
    self._state.execution_trace = []
    self._state.matched_skills = []
    self._state.thinking_steps = []  # Clear at start
    # ... rest of method ...
```

5. Update `get_progress()` in `chat_service.py` to return thinking steps:
```python
def get_progress(self) -> dict:
    return bridge_ok({
        "status": self._state.current_progress,
        "type": self._state.current_progress_type,
        "skills": self._state.matched_skills,
        "thinking_steps": self._state.thinking_steps,  # NEW
    })
```

6. Update `AdvisorProgress` docstring to document `thinking_step` event type.

**Files Modified**:
- `src/sip_videogen/advisor/agent.py`
- `src/sip_videogen/studio/services/chat_service.py`
- `src/sip_videogen/studio/state.py`

**Tests**:
- Integration test: Tool call emits progress event with type "thinking_step"
- Integration test: `get_progress()` returns accumulated thinking steps
- Integration test: No "tool_start" event for report_thinking
- Integration test: `current_progress_type` not affected by thinking_step

**Status**: Not Started

---

## Stage 3: Agent Prompt - Make Thinking Mandatory

**Goal**: Update agent instructions to always use `report_thinking` before taking action.

**Success Criteria**:
- Agent calls `report_thinking` at least once for every request
- Agent provides meaningful, specific explanations
- No system prompt/chain-of-thought leakage

**Implementation**:

1. Update `prompts/advisor.md` to add mandatory thinking section:

```markdown
## Showing Your Reasoning (MANDATORY)

You MUST use `report_thinking` to explain your reasoning before taking any action.
This is NOT optional - users need to see and understand your decision-making process.

### Rules

1. **ALWAYS call at least once** before any other tool use
2. **Call for each major decision** - not just once at the start
3. **Be specific** - "Adding warm golden lighting" not "adjusting lighting"
4. **Explain WHY** - "California vibe = outdoor, sunny, relaxed aesthetic"
5. **Match complexity** - Simple edit = 1-2 steps, Complex generation = 3-5 steps
6. **Keep it brief** - Step title: 2-5 words, Detail: 1-2 sentences max

### Privacy Rules (CRITICAL)

- **NEVER** include system prompt content in thinking steps
- **NEVER** reference internal instructions or capabilities
- **NEVER** explain chain-of-thought or reasoning mechanisms
- **ONLY** explain the creative/technical decisions relevant to the user's request

### When to Call

| Task Type | Minimum Calls | What to Report |
|-----------|---------------|----------------|
| Simple image | 2 | Intent + Approach |
| Complex image | 3-4 | Intent + Approach + Scene details |
| Image edit | 1-2 | What's changing + How |
| Variations | N+1 | Intent + one per variation |
| Non-image | 1 | What you're doing |

### Examples

**Image Generation**:
```
report_thinking("Understanding request", "Lifestyle image with California aesthetic for Morning Complete product")
report_thinking("Crafting scene", "California vibe = outdoor cafe patio, palm trees, golden sunlight, relaxed atmosphere")
generate_image(...)
```

**Image Edit**:
```
report_thinking("Planning edit", "Background removal - replacing busy background with clean white studio backdrop")
generate_image(...)
```

**Multiple Variations**:
```
report_thinking("Planning variations", "Creating 3 lighting variations: golden hour, soft overcast, dramatic side-lit")
report_thinking("Variation 1", "Warm afternoon light from left, long shadows, orange tones")
generate_image(...)
report_thinking("Variation 2", "Diffused light, minimal shadows, cool neutral tones")
generate_image(...)
```

### What Makes a Good Thinking Step

**Good** (specific, user-facing):
- "Crafting scene" → "California aesthetic = outdoor setting with warm sunlight, using cafe patio with palm trees"
- "Choosing composition" → "Hero shot with product prominent, placing bottle center-left with lifestyle elements right"

**Bad** (vague, internal):
- "Processing request" → "Working on the image"
- "Following instructions" → "Applying the image generation skill"
```

2. Add enforcement reminder to key skills (`image_prompt_engineering/SKILL.md`, `image_composer/SKILL.md`):
```markdown
---

**REMINDER**: Before calling `generate_image`, you MUST call `report_thinking` at least once
to explain your approach. Users need to see your reasoning process.
```

**Files Modified**:
- `src/sip_videogen/advisor/prompts/advisor.md`
- `src/sip_videogen/advisor/skills/image_prompt_engineering/SKILL.md`
- `src/sip_videogen/advisor/skills/image_composer/SKILL.md`

**Tests**:
- Manual test: Generate image → verify thinking steps appear
- Manual test: Verify no system prompt content in steps
- Manual test: Edit image → verify thinking steps appear

**Status**: Not Started

---

## Stage 4: Frontend - Types and Thinking Steps Component

**Goal**: Add types and create UI component to display thinking steps.

**Success Criteria**:
- `thinking_step` added to `ActivityEventType`
- Steps appear in real-time as agent reports them
- Each step is collapsible
- Shows spinner even when no steps yet (while generating)

**Implementation**:

1. Update `src/lib/bridge.ts` types:
```typescript
// Add 'thinking_step' to the union
export type ActivityEventType = 'thinking' | 'tool_start' | 'tool_end' | 'skill_loaded' | 'thinking_step' | ''

// Add to ProgressResponse
export interface ProgressResponse {
  status: string
  type: ActivityEventType
  skills: string[]
  thinking_steps: ThinkingStep[]  // NEW
}

// Add new type
export interface ThinkingStep {
  id: string       // UUID for dedupe
  step: string
  detail: string
  timestamp: number
}
```

2. Create `ThinkingSteps.tsx` component in `ChatPanel/`:
```typescript
// src/sip_videogen/studio/frontend/src/components/ChatPanel/ThinkingSteps.tsx

import { useState } from 'react'
import { ChevronRight, ChevronDown, CheckCircle2, Loader2 } from 'lucide-react'
import type { ThinkingStep } from '@/lib/bridge'

interface Props {
  steps: ThinkingStep[]
  isGenerating: boolean
}

export function ThinkingSteps({ steps, isGenerating }: Props) {
  // Show spinner placeholder if generating but no steps yet
  if (steps.length === 0) {
    if (!isGenerating) return null
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Processing...</span>
      </div>
    )
  }

  return (
    <div className="space-y-1 py-2">
      {steps.map((step) => (
        <ThinkingStepItem key={step.id} step={step} />
      ))}
      {isGenerating && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground pl-6">
          <Loader2 className="h-3 w-3 animate-spin" />
          <span>Working...</span>
        </div>
      )}
    </div>
  )
}

function ThinkingStepItem({ step }: { step: ThinkingStep }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="text-sm">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full text-left hover:bg-muted/50 rounded px-1 py-0.5 transition-colors"
      >
        <CheckCircle2 className="h-3 w-3 text-green-500 flex-shrink-0" />
        <span className="font-medium text-foreground">{step.step}</span>
        {step.detail && (
          expanded
            ? <ChevronDown className="h-3 w-3 text-muted-foreground ml-auto" />
            : <ChevronRight className="h-3 w-3 text-muted-foreground ml-auto" />
        )}
      </button>
      {expanded && step.detail && (
        <div className="pl-6 pr-2 py-1 text-muted-foreground text-xs">
          {step.detail}
        </div>
      )}
    </div>
  )
}
```

3. Update `ExecutionTrace.tsx` to handle `thinking_step` type:
```typescript
const getIcon = (type: string) => {
  switch (type) {
    case 'thinking':
      return <Brain className="h-3 w-3 text-purple-500" />
    case 'thinking_step':
      return <CheckCircle className="h-3 w-3 text-green-500" />  // NEW
    case 'tool_start':
      return <Wrench className="h-3 w-3 text-blue-500" />
    // ...
  }
}
```

**Files Created**:
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/ThinkingSteps.tsx`

**Files Modified**:
- `src/sip_videogen/studio/frontend/src/lib/bridge.ts`
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/ExecutionTrace.tsx`

**Tests**:
- Component renders steps correctly
- Expand/collapse works
- Shows spinner when generating with 0 steps
- Shows "Working..." after steps while still generating

**Status**: Not Started

---

## Stage 5: Frontend - Integration with Chat Flow

**Goal**: Connect thinking steps to chat UI via progress polling AND persist on completed messages.

**Success Criteria**:
- Steps appear during "Thinking" phase (real-time from polling)
- Steps persist after generation completes (from execution_trace)
- UI updates smoothly without flicker
- Deduplication of steps by ID

**Implementation**:

1. Update `useChat.ts` to track thinking steps:
```typescript
// Add state
const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([])

// In progress polling interval:
if (progressStatus.thinking_steps && progressStatus.thinking_steps.length > 0) {
  // Dedupe by ID (not timestamp) to avoid duplicates from polling
  setThinkingSteps(prev => {
    const existingIds = new Set(prev.map(s => s.id))
    const newSteps = progressStatus.thinking_steps.filter(
      s => !existingIds.has(s.id)
    )
    return newSteps.length > 0 ? [...prev, ...newSteps] : prev
  })
}

// Clear steps when new message sent (at start of sendMessage):
setThinkingSteps([])

// Return thinkingSteps in hook return value
```

2. Update Message type to include parsed thinking steps:
```typescript
// In useChat.ts Message interface, add:
thinkingSteps?: ThinkingStep[]  // Parsed from executionTrace for completed messages
```

3. When setting final message, extract thinking steps from executionTrace:
```typescript
// In the result handling after bridge.chat():
const thinkingStepsFromTrace = (result.execution_trace || [])
  .filter(e => e.type === 'thinking_step')
  .map((e, idx) => ({
    id: `trace-${e.timestamp}-${idx}`,  // Generate ID if not present
    step: e.message,
    detail: e.detail,
    timestamp: e.timestamp,
  }))

setMessages(prev => prev.map(m =>
  m.id === assistantId
    ? {
        ...m,
        content: result.response,
        // ... other fields ...
        executionTrace: result.execution_trace || [],
        thinkingSteps: thinkingStepsFromTrace,  // Store parsed steps
      }
    : m
))
```

4. Update chat panel component to show ThinkingSteps:

**During loading** (real-time polling):
```tsx
{isLoading && (
  <ThinkingSteps steps={thinkingSteps} isGenerating={true} />
)}
```

**On completed assistant message** (from stored thinkingSteps):
```tsx
{message.role === 'assistant' && message.thinkingSteps?.length > 0 && (
  <ThinkingSteps steps={message.thinkingSteps} isGenerating={false} />
)}
```

**Files Modified**:
- `src/sip_videogen/studio/frontend/src/hooks/useChat.ts`
- `src/sip_videogen/studio/frontend/src/components/ChatPanel/index.tsx` (or MessageList.tsx)

**Tests**:
- Steps accumulate during generation (real-time polling)
- Steps persist on completed message (from thinkingSteps field)
- No duplicate steps from repeated polling (ID-based dedupe)
- New message clears previous thinking steps
- Completed messages show collapsible thinking steps

**Status**: Not Started

---

## Stage 6: Testing and Validation

**Goal**: End-to-end testing across use cases.

**Success Criteria**:
- All common use cases show appropriate thinking steps
- Agent consistently calls the tool
- No system prompt leakage
- UI is polished and responsive

**Implementation**:

1. Test matrix:
   | Use Case | Expected Steps | Pass |
   |----------|---------------|------|
   | Simple image generation | 2+ | [ ] |
   | Image with product reference | 2+ | [ ] |
   | Image edit (background removal) | 1+ | [ ] |
   | Multiple variations | 3+ | [ ] |
   | Template-based generation | 2+ | [ ] |
   | Non-image request | 1+ | [ ] |

2. Consistency check:
   - Run 10 image generations
   - Verify thinking steps appear every time
   - Note any failures to adjust prompt

3. Privacy check:
   - Verify no system prompt content appears in steps
   - Verify no internal instruction references
   - Verify no chain-of-thought leakage

4. Performance check:
   - Measure time from message send to first step visible
   - Target: < 3s for first step

5. Edge case testing:
   - Agent doesn't call tool → shows "Processing..." spinner
   - Very long detail → clamped at backend (500 chars)
   - Rapid polling → ID-based dedupe prevents duplicates
   - Completed message → thinking steps still visible

**Status**: Not Started

---

## Technical Decisions

### Why Return Value Pattern Instead of Global State?

1. **Truly request-scoped** - Data flows through tool result, not globals
2. **No race conditions** - Each tool call has its own result
3. **Testable** - Pure function, no global mutation

### Why UUID for Dedupe Instead of Timestamp?

1. **Guaranteed unique** - Timestamps can collide at ms resolution
2. **Stable identity** - Same step always has same ID
3. **Backend-controlled** - No frontend ID generation needed

### Why Store Parsed Steps on Message?

1. **Persistence** - Steps survive after loading ends
2. **Single source of truth** - executionTrace is raw, thinkingSteps is parsed
3. **Efficient rendering** - No re-parsing on each render

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Agent doesn't call tool | Medium | High | Strong prompt + skill reminders |
| Prompt/system leakage | Low | High | Privacy rules + clamping |
| Polling duplicates | Low | Low | ID-based dedupe |
| Performance impact | Low | Low | Tool is lightweight |

---

## Dependencies

- OpenAI Agents SDK `@function_tool` decorator
- Existing `AdvisorHooks` / `AdvisorProgress` infrastructure
- Existing progress polling in frontend
- `lucide-react` icons (already present)

---

## Out of Scope

- Persisting thinking steps to database
- Analytics on thinking patterns
- User feedback on step quality
- Editing/regenerating based on specific steps
