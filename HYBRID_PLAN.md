# Task Plan: Hybrid Server-Side History + Smart Compaction

## Goal
Combine OpenAI's server-side response chaining with intelligent compaction to preserve context while simplifying client-side code.

## Phases
- [x] Phase 1: Research current implementation and SDK capabilities
- [x] Phase 2: Design hybrid architecture
- [x] Phase 3: Create implementation plan
- [x] Phase 4: Implementation complete

## Key Questions (Answered)
1. ~~How does `auto_previous_response_id` work?~~ → Auto-chains within a single run
2. ~~What parameters does `Runner.run()` accept?~~ → See SDK findings below
3. ~~How do we pass initial history when resuming?~~ → Use `previous_response_id` parameter
4. ~~What's the right compaction threshold?~~ → ~200K tokens (75% of 272K)

## SDK Findings

### Runner.run() Parameters
```python
Runner.run(
    starting_agent: Agent,
    input: str | list[TResponseInputItem],
    context: TContext | None = None,
    max_turns: int = DEFAULT_MAX_TURNS,
    hooks: RunHooks | None = None,
    run_config: RunConfig | None = None,
    previous_response_id: str | None = None,      # ← Key for resuming!
    auto_previous_response_id: bool = False,       # ← Auto-chain within run
    conversation_id: str | None = None,            # ← Server conversation
    session: Session | None = None,                # ← Session object
)
```

### Key Parameter: `previous_response_id`
- Pass the ID from previous `result.response_id`
- OpenAI server retrieves full conversation context
- No need to send history in each call!

### Result Object
```python
result = await Runner.run(agent, message)
result.response_id  # ← Save this for next call
result.final_output  # ← The response
```

## Current Implementation Analysis

### Files Involved
- `agent.py` lines 505, 530, 560, 625 - Runner.run() calls
- `session_history_manager.py` - Client-side history + compaction
- `session_manager.py` - Session CRUD

### Current Token Limits (Too Low!)
```python
TOKEN_SOFT_LIMIT = 6000   # Triggers compaction
TOKEN_HARD_LIMIT = 8000   # Emergency truncation
MAX_CONTEXT_LIMIT = 7500  # Hard limit
```

### Current Flow
1. Build full prompt with history text
2. Send to Runner.run()
3. Save user+assistant messages to disk
4. Check if compaction needed (at 6K tokens!)

## Decisions Made
- Use `previous_response_id` for response chaining (server handles history)
- Keep client-side compaction but raise threshold to 200K
- Store `last_response_id` in SessionMeta
- Summary persists across compaction events
- Delete most token counting code (server handles it)

## Status
**Phase 4** - Plan complete, ready for user review

---

## Phase 2: Hybrid Architecture Design

### The Problem with Pure Server-Side

```
Conversation: [msg1...msg100] = 300K tokens
OpenAI truncation: drops msg1-msg50 silently
Result: Context LOST forever
```

### The Hybrid Solution

```
┌─────────────────────────────────────────────────────────────┐
│                    HYBRID FLOW                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Turn 1: User sends message                                  │
│  ├─ Send: message only (no history!)                         │
│  ├─ Server: stores context                                   │
│  └─ Save: result.response_id → session.last_response_id      │
│                                                              │
│  Turn 2-N: User sends follow-up                              │
│  ├─ Send: message + previous_response_id                     │
│  ├─ Server: retrieves full context, responds                 │
│  └─ Save: new response_id                                    │
│                                                              │
│  At ~200K tokens: SMART COMPACTION                           │
│  ├─ Generate summary of old messages (LLM call)              │
│  ├─ Store summary in session                                 │
│  ├─ Clear response_id (start fresh chain)                    │
│  └─ Next turn: include summary in system prompt              │
│                                                              │
│  Result: Server handles 0-200K, we summarize before loss     │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│    Agent     │────▶│   OpenAI     │
└──────────────┘     └──────────────┘     └──────────────┘
                            │                     │
                            ▼                     ▼
                     ┌──────────────┐     ┌──────────────┐
                     │ SessionMeta  │     │ Server Store │
                     │ - response_id│     │ - 30 day TTL │
                     │ - summary    │     │ - auto-trunc │
                     └──────────────┘     └──────────────┘
```

### What Changes

| Before | After |
|--------|-------|
| Send full history every call | Send only message + response_id |
| Compact at 6K tokens | Compact at 200K tokens |
| Complex prompt building | Simple message pass-through |
| Manual token counting | Server handles limits |

### New SessionMeta Fields

```python
@dataclass
class SessionMeta:
    id: str
    title: str
    # ... existing fields ...
    last_response_id: str | None = None  # NEW: Chain responses
    compaction_summary: str | None = None  # NEW: Preserved context
```

### New Constants

```python
# Token limits for GPT-5.1 (272K context)
COMPACTION_THRESHOLD = 200_000  # ~75% of context
SUMMARY_TARGET_TOKENS = 2_000   # Summary size target
```

### Compaction Trigger Logic

```python
# Rough estimation: ~4 chars per token
estimated_tokens = len(all_messages_text) / 4

if estimated_tokens > COMPACTION_THRESHOLD:
    summary = await generate_summary(messages)
    session.compaction_summary = summary
    session.last_response_id = None  # Reset chain
    # Next call will include summary in system prompt
```

### Session Resume Logic

```python
# When resuming a session
if session.last_response_id:
    # Continue existing chain
    result = await Runner.run(
        agent, message,
        previous_response_id=session.last_response_id
    )
else:
    # Fresh start (after compaction or new session)
    # Summary is in system prompt if available
    result = await Runner.run(agent, message)

# Always save new response_id
session.last_response_id = result.response_id
```

### What to Keep vs Delete

| KEEP | DELETE |
|------|--------|
| Summary generation | Per-call history building |
| Message storage (for UI) | Token counting per message |
| High-threshold compaction | Low threshold constants |
| Session metadata | Complex prompt assembly |

### Edge Cases

1. **OpenAI server truncates before we compact**
   - Server drops old messages silently
   - Our summary prevents total loss
   - Summary included in subsequent prompts

2. **Response ID expires (30 days)**
   - Session still has messages for UI
   - Start fresh chain with summary

3. **Session switch**
   - Load new session's response_id
   - Include that session's summary in prompt

4. **New session after compaction**
   - response_id is None
   - Summary in system prompt
   - Fresh chain starts

---

## Phase 3: Implementation Plan

### Stage 1: Update SessionMeta Model
**File:** `session_manager.py`

```python
# Add to SessionMeta dataclass
@dataclass
class SessionMeta:
    # ... existing fields ...
    last_response_id: str | None = None
    compaction_summary: str | None = None
```

**Changes:**
- Add `last_response_id` field
- Add `compaction_summary` field
- Update `to_dict()` / `from_dict()` methods

### Stage 2: Update Token Constants
**File:** `session_history_manager.py`

```python
# OLD
TOKEN_SOFT_LIMIT = 6000
TOKEN_HARD_LIMIT = 8000
MAX_CONTEXT_LIMIT = 7500

# NEW
COMPACTION_THRESHOLD = 200_000  # 200K tokens (~75% of 272K)
SUMMARY_TARGET_TOKENS = 2_000
```

### Stage 3: Modify Runner.run() Calls
**File:** `agent.py`

**Before (line 505):**
```python
result = await Runner.run(self._agent, ctx.full_prompt, hooks=ctx.hooks)
```

**After:**
```python
# Get response_id from session if available
prev_response_id = None
if self._session_history:
    prev_response_id = self._get_last_response_id()

result = await Runner.run(
    self._agent,
    ctx.raw_user_message,  # Just the message, not full history!
    hooks=ctx.hooks,
    previous_response_id=prev_response_id,
)

# Save new response_id
if self._session_history and hasattr(result, 'response_id'):
    self._save_response_id(result.response_id)
```

**Apply to:**
- Line 505 (`chat_with_metadata`)
- Line 530 (retry path)
- Line 560 (retry path)
- Line 625 (`chat_stream`)

### Stage 4: Add Response ID Storage Methods
**File:** `agent.py`

```python
def _get_last_response_id(self) -> str | None:
    """Get last response ID from current session."""
    if not self._session_manager or not self._current_session_id:
        return None
    session = self._session_manager.get_session(self._current_session_id)
    return session.last_response_id if session else None

def _save_response_id(self, response_id: str) -> None:
    """Save response ID to current session."""
    if not self._session_manager or not self._current_session_id:
        return
    self._session_manager.update_session_response_id(
        self._current_session_id, response_id
    )
```

### Stage 5: Add SessionManager Method
**File:** `session_manager.py`

```python
def update_session_response_id(self, session_id: str, response_id: str) -> bool:
    """Update session's last response ID."""
    with brand_lock(self.brand_slug):
        index = self._load_index()
        for s in index.sessions:
            if s.id == session_id:
                s.last_response_id = response_id
                self._save_index(index)
                return True
        return False
```

### Stage 6: Simplify Prompt Building
**File:** `agent.py` - `_prepare_chat_context()`

**Before:**
- Build history_text from all messages
- Include in full_prompt
- Complex budget trimming

**After:**
- No history_text needed (server has it)
- Just user message + turn context
- Simpler prompt assembly

```python
def _prepare_chat_context(self, message: str, ...) -> ChatContext:
    raw_user_message = message
    skills_context, matched_skills = self._get_relevant_skills_context(raw_user_message)

    # Build turn context (project/products/style refs)
    turn_context = ""
    if self.brand_slug and (project_slug or attached_products or attached_style_references):
        builder = HierarchicalContextBuilder(...)
        turn_context = builder.build_turn_context()

    # Simple prompt - no history needed!
    if turn_context:
        augmented_message = f"## Context\n{turn_context}\n\n## Request\n{raw_user_message}"
    else:
        augmented_message = raw_user_message

    prompt_parts = []
    if skills_context:
        prompt_parts.append(skills_context)
    prompt_parts.append(augmented_message)

    full_prompt = "\n\n".join(prompt_parts)
    # ... rest unchanged
```

### Stage 7: Update Compaction Logic
**File:** `session_history_manager.py`

```python
def _check_compaction(self) -> None:
    """Check if compaction needed at 200K threshold."""
    self._ensure_loaded()
    # Rough estimate: ~4 chars per token
    total_chars = sum(len(m.content) for m in self._messages)
    estimated_tokens = total_chars / 4

    if estimated_tokens >= COMPACTION_THRESHOLD:
        schedule_compaction(self)

async def _compact_with_llm(self) -> None:
    """Generate summary and reset response chain."""
    # Generate summary of all messages
    summary = await _generate_summary(self._messages)
    if summary is None:
        summary = _fallback_summary(self._messages)

    # Store summary
    self._summary = summary
    self._summary_token_count = count_tokens(summary)

    # Clear response_id to start fresh chain
    if self._session_manager:
        self._session_manager.update_session_response_id(
            self.session_id, None  # Reset chain
        )

    self._save()
```

### Stage 8: Delete Unnecessary Code

**Delete from `session_history_manager.py`:**
- `estimate_messages_tokens()` - not needed per-call
- `TOKEN_SOFT_LIMIT`, `TOKEN_HARD_LIMIT` constants
- Complex token counting logic

**Delete from `agent.py`:**
- `_enforce_context_limit()` - server handles this
- History text building in `_prepare_chat_context()`
- Budget manager trimming of history

**Keep:**
- Message storage for UI display
- Summary generation
- Session metadata

### Testing Plan

1. **New conversation** - Verify no `previous_response_id` on first call
2. **Follow-up message** - Verify `previous_response_id` passed
3. **Long conversation** - Verify compaction at 200K
4. **Session resume** - Verify response chain continues
5. **Post-compaction** - Verify summary in prompt, no response_id
6. **Session switch** - Verify correct response_id loaded

### Rollback Plan

If issues arise:
1. Revert `previous_response_id` usage
2. Fall back to full history sending
3. Lower compaction threshold if needed

### Risk Assessment

| Risk | Mitigation |
|------|------------|
| OpenAI rate limits | Existing retry logic |
| Response ID expiry | Summary provides fallback |
| Server-side bugs | Keep messages locally for recovery |
| 30-day TTL | Summary persists indefinitely |

---

## Summary

**Lines of Code:**
- Add: ~50 lines (response ID handling)
- Modify: ~30 lines (Runner.run calls, prompt building)
- Delete: ~100+ lines (token counting, history assembly)

**Net Result:** Simpler code, better caching, preserved context
