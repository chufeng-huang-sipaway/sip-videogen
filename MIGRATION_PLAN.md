# Task Plan: Enable Server-Side Conversation History

## Goal
Enable OpenAI's server-side conversation history to eliminate client-side history management and compaction.

## Key Discovery
**The Agents SDK already uses Responses API!** We just need to enable server-side history features.

## Phases
- [x] Phase 1: Research Responses API documentation
- [x] Phase 2: Analyze current implementation
- [x] Phase 3: Design migration approach
- [ ] Phase 4: Create implementation plan

## Key Questions (Answered)
1. ~~How does the Responses API work?~~ → Server-side history with `previous_response_id`
2. ~~What SDK version is required?~~ → Already using correct SDK
3. ~~How do we handle tools?~~ → Same as before, SDK handles it
4. ~~What happens to existing sessions?~~ → Keep for metadata, let OpenAI handle history
5. ~~How much code can we delete?~~ → Most of compaction logic

## Decisions Made
- **Use `auto_previous_response_id=True`** for automatic response chaining
- **Keep session storage for metadata** (settings, project, UI state)
- **Let OpenAI handle conversation history** via Responses API
- **Delete client-side compaction** - server handles truncation with `truncation: "auto"`

## Implementation Plan

### What Changes

| Component | Current | After Migration |
|-----------|---------|-----------------|
| **History Storage** | Client-side (messages.json) | Server-side (OpenAI) |
| **Compaction** | Client LLM calls | Server automatic (`truncation: "auto"`) |
| **Token Counting** | Manual estimation | Not needed |
| **Response Chaining** | Manual history array | `auto_previous_response_id=True` |

### Code Changes Required

#### 1. `agent.py` - Add response chaining (~5 lines)
```python
# Before
result = await Runner.run(self._agent, ctx.full_prompt, hooks=ctx.hooks)

# After
result = await Runner.run(
    self._agent,
    ctx.full_prompt,
    hooks=ctx.hooks,
    auto_previous_response_id=True,  # NEW: Chain responses automatically
    model_settings=ModelSettings(
        extra_args={"truncation": "auto"}  # NEW: Server handles context limits
    ),
)
```

#### 2. `session_manager.py` - Store response IDs (~10 lines)
```python
@dataclass
class SessionMeta:
    # ... existing fields ...
    last_response_id: str | None = None  # NEW: Track for conversation continuity
```

#### 3. Session Resume - Pass response ID (~5 lines)
```python
# When resuming a session
result = await Runner.run(
    self._agent,
    message,
    previous_response_id=session.last_response_id,  # Resume from last response
    auto_previous_response_id=True,
)
```

### Code to DELETE (Simplification!)

| File | Lines | What to Delete |
|------|-------|----------------|
| `session_history_manager.py` | ~200 | Token counting, compaction, LLM summarization |
| `agent.py` | ~50 | Manual history building, budget trimming |
| `context_budget.py` | ~100 | Token estimation logic |

### What to KEEP

| Component | Reason |
|-----------|--------|
| `SessionManager` | Session metadata, settings, UI state |
| `session_manager.py` models | Session/Settings dataclasses |
| Bridge API | Frontend still needs session list/switch |
| Migration code | Convert old sessions to new format |

## Migration Steps

### Step 1: Update Agent Calls (Low Risk)
- Add `auto_previous_response_id=True` to `Runner.run()` calls
- Add `truncation: "auto"` to model settings
- Test that conversations work

### Step 2: Store Response IDs (Low Risk)
- Add `last_response_id` field to `SessionMeta`
- Save response ID after each chat turn
- Load and pass when resuming session

### Step 3: Remove Compaction (Medium Risk)
- Delete auto-compaction scheduling
- Delete token counting logic
- Delete LLM summarization calls
- Keep fallback for non-US regions (where `store=true` unavailable)

### Step 4: Simplify History Manager (Medium Risk)
- Remove most of `session_history_manager.py`
- Keep minimal message storage for UI display
- Let OpenAI handle actual conversation history

## Testing Plan

1. **New conversation** - Verify chaining works
2. **Resume session** - Verify `previous_response_id` continues conversation
3. **Long conversation** - Verify auto-truncation works at 272K limit
4. **Tool calls** - Verify tools still work with response chaining
5. **Streaming** - Verify streaming works with new parameters

## Rollback Plan

If issues arise:
1. Remove `auto_previous_response_id` parameter
2. Fall back to client-side history (existing code)
3. Compaction code still exists until Step 3

## Timeline Estimate

| Step | Effort |
|------|--------|
| Step 1: Update Agent Calls | Small (1-2 hours) |
| Step 2: Store Response IDs | Small (1-2 hours) |
| Step 3: Remove Compaction | Medium (2-4 hours) |
| Step 4: Simplify History | Medium (2-4 hours) |
| Testing | Medium (2-4 hours) |

**Total: ~10-16 hours of work**

## Status
**Currently in Phase 4** - Implementation plan complete, ready for execution

## Next Steps
1. Review this plan
2. Decide on execution approach (incremental vs all-at-once)
3. Start implementation
