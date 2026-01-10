# Research Notes: Agent Reliability Issues

## Issue 1: Memory Loss

### Current State
- `ConversationHistoryManager` (history_manager.py:30) is **in-memory only**
- History stored in `self._messages: list[Message] = []`
- No persistence to disk

### Trigger Points for History Loss
1. **Brand switch** - `set_brand()` calls `self._history_manager.clear()` by default (agent.py:128)
2. **App restart** - New BrandAdvisor instance = fresh history manager
3. **"Create New Chat" button** - Explicitly clears history

### What IS Persisted
- User preferences via `update_memory` tool → `~/.sip-studio/brands/{slug}/memory.json`
- This is loaded into system prompt (prompt_builder.py:122-134)
- But this is NOT conversation history, just key-value preferences

### User's Expectation
> "If user does not click 'Create New Chat', keep it going"
> "Switching projects means work on new project AS CONTEXT, not lose history"

### Solution Direction
1. Save conversation history to disk per-brand
2. Only clear on explicit "Create New Chat"
3. Project switching should NOT clear history

---

## Issue 2: Todo List Never Created

### Current State
- Tools exist: `create_todo_list`, `update_todo_item`, `check_interrupt`, etc. (todo_tools.py)
- UI infrastructure exists (state.py:278-370)
- Push mechanism exists (`_push_todo_list`, `_push_todo_update`)

### The Problem: NO INSTRUCTIONS IN PROMPT
Searched advisor.md - ZERO mentions of:
- `create_todo_list` ❌
- `update_todo_item` ❌
- `check_interrupt` ❌
- "todo" at all ❌

The model has the tools but **no guidance to use them**.

### Compare to Claude Code
Claude Code's system prompt has explicit instructions:
```
CRITICAL: For any request involving 3+ items, you MUST:
1. Call create_todo_list() FIRST
2. Work through EVERY item
3. Call complete_todo_list() when ALL items done
```

### Solution Direction
Add explicit todo list usage instructions to advisor.md

---

## Issue 3: File Write Refusal

### Current State
- `write_file` tool exists (file_tools.py:161-170)
- Sandboxed to brand directory only (safe)
- System prompt mentions it briefly: `"**read_file** / **write_file** / **list_files** - Access brand directory"` (advisor.md:134)

### The Problem: VAGUE INSTRUCTIONS
1. Only 1 line mentions write_file
2. No examples of WHEN to use it
3. No guidance that it SHOULD be used for brand updates
4. Model may not know it can update `identity.json` or `identity_full.json`

### What User Tried
> "I gave the URL and said... can you interpret this and UPDATE the brand identity"
> "Agent tells me it cannot update files"
> "Agent asks me to copy/paste"

### Solution Direction
1. Add explicit examples of using write_file
2. Tell model it CAN and SHOULD update brand files
3. Clarify what files can be written

---

## Architecture Understanding

### Conversation Flow
```
Frontend → Bridge.chat() → ChatService.chat() → BrandAdvisor.chat_with_metadata()
                                                       ↓
                                              Runner.run(agent, prompt)
                                                       ↓
                                              OpenAI API (GPT-5.1)
```

### History Flow (Current)
```
User message → _prepare_chat_context() → get_formatted(history)
                                                ↓
                                        history_text string
                                                ↓
                                        Prepended to prompt
                                                ↓
                              LOST on brand switch or restart
```

### History Flow (Target)
```
User message → _prepare_chat_context() → get_formatted(history)
                                                ↓
                        ON EVERY ADD: save to ~/.sip-studio/brands/{slug}/chat_history.json
                                                ↓
                        ON STARTUP: load from disk if file exists
                                                ↓
                        ON "NEW CHAT" ONLY: clear history (not on brand switch!)
```

---

## Key Files to Modify

| File | Change |
|------|--------|
| `history_manager.py` | Add save/load persistence |
| `agent.py` | Change set_brand to NOT clear history by default |
| `advisor.md` | Add todo list usage instructions |
| `advisor.md` | Add file write examples and encouragement |
| `chat_service.py` | (maybe) Ensure history loaded on startup |

---

## Implementation Risk Assessment

| Change | Risk | Mitigation |
|--------|------|------------|
| History persistence | Data loss if format changes | Versioned JSON format |
| Not clearing on brand switch | Cross-brand contamination | Keep per-brand history files |
| Todo prompt changes | Over-use of todo lists | "3+ items" threshold |
| File write encouragement | Accidental data corruption | Already sandboxed to brand dir |
