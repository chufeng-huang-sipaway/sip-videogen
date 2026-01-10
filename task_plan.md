# Task Plan: Agent Reliability Improvements

## Goal
Fix three critical agent behavior issues: memory persistence across project switches, reliable todo list usage for long tasks, and file modification capabilities.

## Problem Summary

| Issue | Symptom | Root Cause (Confirmed) |
|-------|---------|------------------------|
| Memory loss | Agent forgets on project switch | History in-memory only, cleared on brand switch |
| Todo list unused | Agent generates 4 then stops | **Zero instructions in prompt** to use todo tools |
| File write refusal | Agent asks to copy/paste | Only 1 vague line mentions write_file |

## Phases

- [x] Phase 1: Deep research - understand current behavior
- [x] Phase 2: Design solutions for each issue
- [ ] Phase 3: Implement memory persistence
- [ ] Phase 4: Implement todo list enforcement
- [ ] Phase 5: Implement file write enablement
- [ ] Phase 6: Test and validate

## Detailed Design

### Phase 3: Memory Persistence

**Goal**: Conversation history survives app restart and brand/project switching

**Changes**:
1. `history_manager.py` - Add `save_to_disk()` and `load_from_disk()` methods
   - Path: `~/.sip-studio/brands/{slug}/chat_history.json`
   - Format: `{"version": 1, "messages": [...], "summary": "..."}`
   - Auto-save on every `add()` call

2. `agent.py` - Change `set_brand()` behavior
   - Remove `preserve_history=False` default
   - Load history from new brand's disk file
   - User switching brands = "continue conversation in new brand context"

3. `chat_service.py` - Add `clear_chat()` as explicit action
   - This is the ONLY way to clear history
   - Maps to frontend "Create New Chat" button

**Test cases**:
- [ ] History survives app restart
- [ ] Switching brands loads that brand's history
- [ ] "Create New Chat" clears history
- [ ] Project switching does NOT clear history

### Phase 4: Todo List Enforcement

**Goal**: Agent reliably creates and completes todo lists for multi-step tasks

**Changes**:
1. `advisor.md` - Add new section (after "Your Tools"):
```markdown
## Multi-Step Task Management (CRITICAL)

When user requests tasks with 3+ items (e.g., "generate 10 images", "create 5 variations"):

**YOU MUST:**
1. Call `create_todo_list(title, items)` FIRST - list ALL items upfront
2. Call `update_todo_item(id, "in_progress")` BEFORE starting each item
3. Call `check_interrupt()` BETWEEN items (user may want to pause/stop)
4. Call `update_todo_item(id, "done")` AFTER completing each item
5. Call `complete_todo_list(summary)` when ALL items are done

**NEVER:**
- Generate "a few" items and stop - complete the ENTIRE list
- Skip creating the todo list for multi-item requests
- Ignore check_interrupt - always check between items

**Example - "Generate 10 product images":**
1. create_todo_list("10 Product Images", ["Image 1: Hero shot", "Image 2: Lifestyle", ...])
2. For each item:
   - update_todo_item(id, "in_progress")
   - generate_image(...)
   - add_todo_output(id, path, "image")
   - update_todo_item(id, "done")
   - check_interrupt()
3. complete_todo_list("Generated 10 product images")
```

**Test cases**:
- [ ] "Generate 10 images" creates a 10-item todo list
- [ ] All 10 items are completed
- [ ] UI shows todo progress
- [ ] Pause/stop works via check_interrupt

### Phase 5: File Write Enablement

**Goal**: Agent understands it CAN and SHOULD write files

**Changes**:
1. `advisor.md` - Expand file tools section:
```markdown
### File Management

You have full read/write access to the brand directory:
- **read_file(path)** - Read any file in the brand directory
- **write_file(path, content)** - Create or update files
- **list_files(path)** - Browse directory contents

**USE write_file WHEN:**
- User asks you to update brand identity → write to `identity.json` or `identity_full.json`
- User asks you to save notes/learnings → write to a markdown file
- User asks you to create a config file → create it directly

**Example - User: "Update the brand tagline to 'Fresh Every Day'"**
1. read_file("identity.json") - get current identity
2. Modify the tagline field
3. write_file("identity.json", updated_content) - save changes
4. Confirm: "Updated your brand tagline to 'Fresh Every Day'"

**NEVER say "I can't modify files" or "please copy/paste" - you CAN write files.**
```

**Test cases**:
- [ ] "Update the tagline" actually updates identity.json
- [ ] Agent doesn't ask user to copy/paste
- [ ] Writes are atomic and don't corrupt files

## Key Questions Answered

1. ✅ What triggers history clear? → Brand switch (set_brand default behavior)
2. ✅ Where is conversation state? → In-memory only in ConversationHistoryManager
3. ✅ Is prompt instructing todo usage? → **NO - zero mentions**
4. ✅ Does model know write_file exists? → Barely - 1 vague line
5. ✅ What makes Claude Code work? → Explicit mandatory instructions

## Decisions Made

1. **History persistence format**: JSON with version field for future migration
2. **History location**: Per-brand file at `~/.sip-studio/brands/{slug}/chat_history.json`
3. **Brand switch behavior**: Load new brand's history (not clear)
4. **Todo threshold**: "3+ items" triggers mandatory todo list creation
5. **File write guidance**: Explicit examples with "NEVER say can't modify"

## Errors Encountered
- (none yet)

## Status
**Currently in Phase 3** - Ready to implement memory persistence
