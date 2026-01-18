# Implementation Plan: Tool Design Refactoring

## Problem Statement

Current agent has **48 tools** - 3x over industry-recommended limit of 10-15.
Research shows performance drops significantly above 15 tools.

**Key Issues:**
1. Tool count (48) causes selection confusion
2. Documentation lacks use cases, boundaries, examples
3. CRUD operations split across many tools (product: 8, style_ref: 8)
4. No dynamic loading despite existing skills infrastructure

---

## Strategy Overview

**Approach: Consolidate + Dynamic Loading + Documentation Enhancement**

| Component | Current | Target |
|-----------|---------|--------|
| Total tools | 48 | ~15 core + skill-loaded |
| Product tools | 8 | 3 |
| Style Reference tools | 8 | 2 |
| Todo/Task tools | 9 | 5 |
| Context tools | 3 | 1 |

---

## Stage 1: Tool Consolidation

**Goal:** Reduce 48 → ~25 tools via CRUD consolidation
**Success Criteria:** All tests pass, same functionality
**Status:** Not Started

### 1.1 Product Tools Consolidation

**Before (8 tools):**
- create_product, update_product, delete_product
- add_product_image, set_product_primary_image
- analyze_product_packaging, analyze_all_product_packaging, update_product_packaging_text

**After (3 tools):**
```python
manage_product(action: Literal["create", "update", "delete", "add_image", "set_primary"], slug: str | None, ...) -> str
analyze_packaging(slug: str | None, mode: Literal["single", "all"] = "single", offset: int = 0, limit: int = 20) -> str
update_packaging_text(slug: str, field: Literal["headline", "subheadline", "body", "tagline"], value: str) -> str
```

**Action-Specific Parameter Requirements:**

| Action | Required Params | Optional Params | Confirm Required |
|--------|-----------------|-----------------|------------------|
| create | name | description, attributes | No |
| update | slug | name, description, attributes | No |
| delete | slug | - | Yes (server-enforced) |
| add_image | slug, image_path | - | No |
| set_primary | slug, image_path | - | No |

**analyze_packaging modes:**
- `single`: Analyze one product (requires slug)
- `all`: Analyze all products (max 20, paginated with offset param)

**update_packaging_text** kept separate because:
- Mixing analysis + mutation is risky (Codex feedback)
- Clear separation: read tools vs write tools
- Server-side validation easier when mutation is explicit

**Standardized Parameter Names:**
- Use `slug` consistently (not `product_slug` or `style_ref_slug`)
- Entity type is implicit from tool name

**Standardized Return Format:**
- All tools return `str` (JSON-formatted for structured data)
- Agent parses JSON when needed, humans can read raw output

**Files to modify:**
- `src/sip_studio/advisor/tools/product_tools.py`
- `src/sip_studio/advisor/tools/__init__.py`

### 1.2 Style Reference Tools Consolidation

**Before (8 tools):**
- list_style_references, get_style_reference_detail
- create_style_reference, create_style_references_from_images
- update_style_reference, add_style_reference_image
- reanalyze_style_reference, delete_style_reference

**After (2 tools):**
```python
manage_style_reference(action: Literal["create", "create_batch", "update", "delete", "add_image", "reanalyze"], slug: str | None, ...) -> str
get_style_reference(slug: str | None = None, offset: int = 0, limit: int = 20) -> str  # None = list all
```

**Action-Specific Parameter Requirements:**

| Action | Required Params | Optional Params | Confirm Required |
|--------|-----------------|-----------------|------------------|
| create | name | description, image_path, default_strict | No |
| create_batch | image_paths | default_strict | No |
| update | slug | name, description, default_strict | No |
| delete | slug | - | Yes (server-enforced) |
| add_image | slug, image_path | reanalyze | No |
| reanalyze | slug | - | No |

**Pagination for List Operations:**
- `get_style_reference(None)`: Returns paginated list (default limit=20)
- Use `offset` param for pagination: `get_style_reference(None, offset=20, limit=20)`
- Response includes `total_count` and `has_more` for agent reasoning

**Batch Operation Handling:**
- `create_batch`: Max 10 images per call, returns partial success report
- Always returns structured JSON with success/failure breakdown

**Partial Failure Pattern:**
```python
# create_batch returns structured JSON string
'{"created": [{"name": "Hero Banner", "slug": "hero-banner"}], "failed": [{"path": "uploads/bad.png", "error": "Invalid image format"}], "total": 2, "success_count": 1}'
```

**File Path Validation:**
- `image_path` must start with `uploads/` (sandbox constraint)
- File must exist and be valid image type (png, jpg, webp)
- Max file size: 10MB
- Returns clear error message if validation fails

**Files to modify:**
- `src/sip_studio/advisor/tools/style_reference_tools.py`
- `src/sip_studio/advisor/tools/__init__.py`

### 1.3 Todo/Task Tools Deduplication

**Current:** Two overlapping systems (todo_tools + task_tools)
**Decision:** Keep task_tools (file-based persistence), deprecate todo_tools

**Before (9 tools):**
- create_todo_list, update_todo_item, add_todo_output, complete_todo_list, check_interrupt
- create_task_file, get_remaining_tasks, update_task, complete_task_file

**After (5 tools):**
- create_task_file, get_remaining_tasks, update_task, complete_task_file
- check_interrupt (KEEP - required for cancellation UX)

**check_interrupt Decision:**
- Initially considered removing, but it's needed for cancellation flows
- When user clicks "Stop" in UI, agent needs to detect and gracefully exit
- Keep as standalone tool, not bundled into task_tools

**Files to modify:**
- `src/sip_studio/advisor/tools/__init__.py` (remove todo_tools except check_interrupt)

### 1.4 Context Tools Consolidation

**Before (3 tools):**
- fetch_context_cached, get_cached_product_context, get_cached_style_reference_context

**After (1 tool):**
```python
get_context(entity_type: Literal["product", "style_reference"], slug: str) -> str
```

**Files to modify:**
- `src/sip_studio/advisor/tools/context_tools.py`
- `src/sip_studio/advisor/tools/__init__.py`

---

## Stage 2: Dynamic Tool Loading

**Goal:** Load tools based on activated skills (25 → ~10 active at once)
**Success Criteria:** Agent gets 8-12 tools per turn, not 25+
**Status:** Not Started

### 2.1 Define Tool Categories (Revised for Budget)

**Tool Budget Calculation:**
- Target: 8-12 tools active per turn
- Core: 5 tools (always on)
- Per-skill: 2-3 tools
- Max concurrent skills: 3 (increased to avoid thrashing for common workflows)

```python
# src/sip_studio/advisor/tools/registry.py (new file)

CORE_TOOLS = [
    "load_brand",         # Always needed
    "propose_choices",    # UI interaction
    "activate_skill",     # Meta tool - loads skill-specific tools
    "list_products",      # Quick navigation
    "check_interrupt",    # Cancellation support
]  # 5 tools

SKILL_TOOL_MAPPING = {
    "image-composer": ["generate_image", "propose_images"],  # 2 tools
    "image-prompt-engineering": [],  # Instructions only
    "product-management": ["manage_product", "analyze_packaging", "update_packaging_text"],  # 3 tools
    "style-references": ["manage_style_reference", "get_style_reference"],  # 2 tools
    "research": ["web_search", "request_deep_research", "get_research_status", "search_research_cache"],  # 4 tools
    "brand-identity": ["fetch_brand_detail", "browse_brand_assets"],  # 2 tools
    "file-operations": ["read_file", "write_file", "list_files"],  # 3 tools
}

# True lazy import using importlib to avoid circular dependencies
def _resolve_tool(name: str):
    """Lazy import tool by name using importlib.

    Handles missing tools gracefully with clear error.
    """
    import importlib
    # Tool name -> module path mapping (MUST be complete)
    TOOL_MODULES = {
        "load_brand": ("sip_studio.advisor.tools.brand_tools", "load_brand"),
        "manage_product": ("sip_studio.advisor.tools.product_tools", "manage_product"),
        "analyze_packaging": ("sip_studio.advisor.tools.product_tools", "analyze_packaging"),
        "update_packaging_text": ("sip_studio.advisor.tools.product_tools", "update_packaging_text"),
        "manage_style_reference": ("sip_studio.advisor.tools.style_reference_tools", "manage_style_reference"),
        "get_style_reference": ("sip_studio.advisor.tools.style_reference_tools", "get_style_reference"),
        "generate_image": ("sip_studio.advisor.tools.image_tools", "generate_image"),
        "propose_images": ("sip_studio.advisor.tools.image_tools", "propose_images"),
        "web_search": ("sip_studio.advisor.tools.research_tools", "web_search"),
        "request_deep_research": ("sip_studio.advisor.tools.research_tools", "request_deep_research"),
        "get_research_status": ("sip_studio.advisor.tools.research_tools", "get_research_status"),
        "search_research_cache": ("sip_studio.advisor.tools.research_tools", "search_research_cache"),
        # ... complete mapping for all tools
    }
    if name not in TOOL_MODULES:
        raise ValueError(f"Unknown tool '{name}'. Add to TOOL_MODULES in registry.py")
    try:
        module_path, attr_name = TOOL_MODULES[name]
        module = importlib.import_module(module_path)
        return getattr(module, attr_name)
    except (ImportError, AttributeError) as e:
        raise RuntimeError(f"Failed to load tool '{name}': {e}") from e
```

**Budget Enforcement:**
- Base: 5 core tools
- With 1 skill: 5 + 2-3 = 7-8 tools ✓
- With 2 skills: 5 + 4-6 = 9-11 tools ✓
- With 3 skills: 5 + 6-9 = 11-14 tools (at limit, acceptable)
- Max skills: 3 concurrent (covers product + style + image workflow)

### 2.2 Modify Agent Initialization (Order-Preserving)

```python
# src/sip_studio/advisor/agent.py

def _get_tools_for_turn(activated_skills: list[str]) -> list:
    """Compose tool set based on active skills.

    Uses order-preserving dedupe (not set) for deterministic tool ordering.
    """
    from sip_studio.advisor.tools.registry import CORE_TOOLS, SKILL_TOOL_MAPPING, _resolve_tool

    tool_names = list(CORE_TOOLS)
    for skill in activated_skills[:3]:  # Max 3 skills
        if skill in SKILL_TOOL_MAPPING:
            tool_names.extend(SKILL_TOOL_MAPPING[skill])

    # Order-preserving dedupe by tool name
    seen = set()
    unique_names = []
    for name in tool_names:
        if name not in seen:
            seen.add(name)
            unique_names.append(name)

    return [_resolve_tool(name) for name in unique_names]
```

### 2.3 Tool Refresh Mid-Run (Critical)

**Problem:** Agent calls `activate_skill`, but new tools aren't available until next user turn.

**Solution:** Use OpenAI Agents SDK's dynamic tool capability:

```python
# In agent runner, after each tool call:
def _on_tool_end(tool_name: str, result: str):
    if tool_name == "activate_skill":
        # Refresh tool list for next LLM call within same run
        current_skills = get_workflow_state().activated_skills
        agent.tools = _get_tools_for_turn(current_skills)
        logger.info(f"[AGENT] Refreshed tools: {len(agent.tools)} tools available")
```

**Alternative (if SDK doesn't support mid-run refresh):**
- `activate_skill` returns instructions + tells agent to proceed
- Agent can use newly-activated tools in same response (tools are resolved at call time)
- Test this behavior with SDK to confirm

### 2.4 How Agent Triggers `activate_skill`

**Problem:** Domain tools aren't core, so how does agent know to activate a skill?

**Solution:** System prompt instructs agent to activate skills based on user intent:

```markdown
## Skill-Based Tools

You have access to specialized skills. To use domain-specific tools, first activate the skill:

| User Intent | Activate Skill |
|-------------|----------------|
| Create/edit products | `activate_skill("product-management")` |
| Create/edit style references | `activate_skill("style-references")` |
| Generate images | `activate_skill("image-composer")` |
| Research topics | `activate_skill("research")` |
| Read/write files | `activate_skill("file-operations")` |

**Workflow:**
1. Identify user intent
2. Call `activate_skill(skill_name)` to load tools
3. Use the newly-available tools to complete the task

You can have up to 3 skills active at once. Skills persist across turns.
```

**Alternative (Auto-Activation):** For common workflows, could auto-activate based on user message keywords:
- "create product" → auto-activate product-management
- "generate image" → auto-activate image-composer
- Decision: Start with explicit activation, add auto-activation if needed

### 2.5 Skill Activation Lifecycle

**Activation:**
- Explicit via `activate_skill("skill-name")` tool call
- Agent decides when to activate based on user intent (see system prompt above)
- Max 3 concurrent skills enforced (covers product + style + image workflow)

**Persistence:**
- Activated skills stored in `SessionContextCache.activated_skills: list[str]`
- Persists across turns within same session
- Does NOT leak between sessions (session-scoped)

**Deactivation/Reset:**
- New session = empty skill list (fresh start)
- No explicit deactivate needed (skills auto-reset on new session)
- If agent activates 4th skill, oldest skill auto-deactivated (FIFO)

```python
# src/sip_studio/advisor/tools/skill_tools.py

MAX_CONCURRENT_SKILLS = 3

def _impl_activate_skill(skill_name: str) -> str:
    """Activate a skill and return its instructions.

    Handles unknown skills gracefully with clear error message.
    """
    registry = get_skills_registry()
    skill = registry.get(skill_name)

    # Handle unknown skill (prevent None.name crash)
    if skill is None:
        available = list(registry.skills.keys())
        return f"Error: Unknown skill '{skill_name}'. Available skills: {available}"

    state = get_workflow_state()

    # Enforce max skills (FIFO eviction)
    if skill_name not in state.activated_skills:
        if len(state.activated_skills) >= MAX_CONCURRENT_SKILLS:
            evicted = state.activated_skills.pop(0)
            logger.info(f"[SKILL] Evicted '{evicted}' to make room for '{skill_name}'")
        state.activated_skills.append(skill_name)

    # Return skill instructions
    return f"## {skill.name} - Full Instructions\n\n{skill.instructions}"
```

---

## Stage 3: Documentation Enhancement

**Goal:** All tools follow 5-step formula
**Success Criteria:** Each tool docstring has: purpose, use cases, boundaries, params with examples
**Status:** Not Started

### 3.1 Documentation Template

```python
@function_tool
def tool_name(param1: type, param2: type = default) -> str:
    """[One sentence purpose].

    PREREQUISITE: [Required state/calls, if any]

    Use when user wants to:
    - [Intent phrase 1]
    - [Intent phrase 2]

    Does NOT:
    - [What this tool cannot do]
    - [Redirect to correct tool]

    Args:
        param1: [Description]. [Constraints]. Example: "value"
        param2: [Description]. Defaults to X.

    Returns:
        [What the return value contains]

    Examples:
        tool_name("value1", param2="value2")
        tool_name("value1")  # Uses default param2
    """
```

### 3.2 Priority Order for Documentation

1. **High-frequency tools first:**
   - generate_image
   - manage_product (consolidated)
   - manage_style_reference (consolidated)
   - load_brand

2. **Then remaining tools by category**

---

## Stage 4: Global State Migration (Optional)

**Goal:** Move from module globals to contextvars
**Success Criteria:** Thread-safe state, testable
**Status:** Not Started (Lower Priority)

### Current (problematic):
```python
# research_tools.py
_pending_research_clarification: dict | None = None

# memory_tools.py
_pending_interaction = None
_pending_memory_update = None
```

### Target (contextvars):
```python
# context.py (new file)
from contextvars import ContextVar
from dataclasses import dataclass, field

@dataclass
class TurnContext:
    session_id: str
    brand_slug: str | None = None
    pending_interaction: dict | None = None
    pending_memory_update: dict | None = None
    pending_research: dict | None = None
    activated_skills: list[str] = field(default_factory=list)

turn_context: ContextVar[TurnContext] = ContextVar("turn_context")
```

---

## Stage 5: Migration & Cleanup

**Goal:** Update all references to old tool names
**Success Criteria:** No runtime "unknown tool" errors, all tests pass
**Status:** Not Started

### 5.1 Audit Old Tool References (Complete List)

Search for ALL old tool names:
```bash
# Product tools (8 → 3)
grep -rE "create_product|update_product|delete_product|add_product_image|set_product_primary_image|analyze_product_packaging|analyze_all_product_packaging|update_product_packaging_text" src/ tests/

# Style reference tools (8 → 2)
grep -rE "list_style_references|get_style_reference_detail|create_style_reference|create_style_references_from_images|update_style_reference|add_style_reference_image|reanalyze_style_reference|delete_style_reference" src/ tests/

# Todo tools (being removed)
grep -rE "create_todo_list|update_todo_item|add_todo_output|complete_todo_list" src/ tests/

# Context tools (3 → 1)
grep -rE "fetch_context_cached|get_cached_product_context|get_cached_style_reference_context" src/ tests/
```

**Files likely to need updates:**
- `src/sip_studio/advisor/skills/*.md` - Skill instruction files
- `src/sip_studio/advisor/prompts/*.py` - System prompts
- `src/sip_studio/advisor/tools/__init__.py` - ADVISOR_TOOLS list
- `tests/` - Test files that call tools directly
- Any `.py` file importing old tool names

### 5.2 Update Skill Instructions

Each skill file that mentions old tools must be updated:

| Old Tool Name | New Tool Name | New Usage |
|---------------|---------------|-----------|
| create_product | manage_product | `manage_product(action="create", name="...")` |
| update_product | manage_product | `manage_product(action="update", slug="...", ...)` |
| delete_product | manage_product | `manage_product(action="delete", slug="...", confirm=True)` |
| add_product_image | manage_product | `manage_product(action="add_image", slug="...", image_path="...")` |
| set_product_primary_image | manage_product | `manage_product(action="set_primary", slug="...", image_path="...")` |
| create_style_reference | manage_style_reference | `manage_style_reference(action="create", name="...")` |
| list_style_references | get_style_reference | `get_style_reference()` (no slug = list all) |
| get_style_reference_detail | get_style_reference | `get_style_reference(slug="...")` |
| create_style_references_from_images | manage_style_reference | `manage_style_reference(action="create_batch", image_paths=[...])` |
| update_style_reference | manage_style_reference | `manage_style_reference(action="update", slug="...", ...)` |
| delete_style_reference | manage_style_reference | `manage_style_reference(action="delete", slug="...", confirm=True)` |

### 5.3 Update Tests

```python
# Old test pattern
def test_create_product():
    result = _impl_create_product("Test Product")
    assert "Created" in result

# New test pattern
def test_manage_product_create():
    result = _impl_manage_product(action="create", name="Test Product")
    assert "Created" in result
```

### 5.4 Rollout Strategy

**Phase A: Add new tools alongside old (1 release)**
- Add `manage_product`, `manage_style_reference`, `get_style_reference`
- Keep old tools working (deprecated but functional)
- Log deprecation warnings when old tools called

**Phase B: Remove old tools (next release)**
- Remove deprecated tools from ADVISOR_TOOLS
- Verify no runtime errors in testing

**Note:** Since this is a desktop app with bundled updates, Phase A can be skipped if we're confident in testing. The old tools are internal - no external consumers.

---

## Implementation Order

| Stage | Priority | Effort | Impact |
|-------|----------|--------|--------|
| 1.1 Product consolidation | P0 | Medium | High |
| 1.2 Style Ref consolidation | P0 | Medium | High |
| 5.x Migration & cleanup | P0 | Medium | High |
| 2.x Dynamic loading | P0 | High | High |
| 3.x Documentation | P1 | Medium | High |
| 1.3 Todo/Task dedup | P2 | Low | Medium |
| 1.4 Context consolidation | P2 | Low | Low |
| 4.x Global state | P3 | Medium | Medium |

**Recommended execution:**
1. Stage 1.1-1.2 together (consolidation) - immediate tool count reduction
2. Stage 5 (migration) - update all references to new tool names
3. Stage 2 (dynamic loading) - highest impact for agent performance
4. Stage 3 (documentation) - can be done incrementally
5. Stages 1.3, 1.4, 4 (cleanup) - lower priority

---

## Verification

### Per-Stage Tests
- Run existing test suite: `pytest tests/`
- Manual test: Create product, add image, generate image
- Check tool count in agent initialization logs

### End-to-End Test
1. Start fresh session
2. Load brand
3. Create product with image
4. Create style reference
5. Generate image with product + style reference
6. Verify all operations work with reduced tool set

---

## Files to Create/Modify

**New files:**
- `src/sip_studio/advisor/tools/registry.py` - Tool categorization

**Modified files:**
- `src/sip_studio/advisor/tools/product_tools.py` - Consolidation
- `src/sip_studio/advisor/tools/style_reference_tools.py` - Consolidation
- `src/sip_studio/advisor/tools/context_tools.py` - Consolidation
- `src/sip_studio/advisor/tools/__init__.py` - Updated ADVISOR_TOOLS
- `src/sip_studio/advisor/agent.py` - Dynamic tool loading
- `src/sip_studio/advisor/tools/skill_tools.py` - Persist skill state

---

## Design Decisions (with Rationale)

These decisions were made during planning discussions. Documented here so developers understand the reasoning.

### Decision 1: Tailored Signatures (Not Uniform)

**Question:** Should `manage_product` and `manage_style_reference` have identical parameter structures?

**Options Considered:**

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Uniform | Same params for both tools | Predictable pattern | Irrelevant params confuse agent |
| B. Tailored | Domain-specific params | Only relevant params | Two patterns to learn |

**Decision: Option B (Tailored)**

```python
# Product-specific params
manage_product(action, slug, name=None, description=None, attributes=None, image_path=None, confirm=False)

# Style-reference-specific params
manage_style_reference(action, slug, name=None, image_path=None, default_strict=None, reanalyze=True, confirm=False)
```

**Rationale:** The agent is smart enough to handle domain-specific parameters. Including irrelevant params (like `attributes` for style references) would actually confuse the agent and lead to incorrect tool usage. Clear, domain-specific documentation in each tool's docstring makes the differences obvious.

---

### Decision 2: No Backwards Compatibility Concern

**Question:** How to handle backwards compatibility for code importing old tool names?

**Decision: Not applicable - no action needed**

**Rationale:** This concern doesn't apply to our architecture:
- Tools are **internal** to the agent system
- Users interact via the **UI**, not by calling Python functions directly
- When users install an updated DMG, all components update together
- There are no external consumers of our tool APIs

We can freely rename, restructure, or remove tools without breaking anything.

---

### Decision 3: Keep Research Tools As-Is

**Question:** Should research tools (4 tools) be consolidated further?

**Decision: No - keep them untouched**

**Rationale:**
- Research tools are already well-scoped (4 tools total)
- They don't contribute significantly to the 48-tool bloat problem
- They serve distinct purposes (web_search, request_deep_research, get_research_status, search_research_cache)
- Consolidating them would reduce clarity without meaningful benefit

---

## Core Principle: Agent Intelligence

**CRITICAL: The agent must proactively use available tools to complete tasks.**

This refactoring is NOT about limiting the agent's capabilities. It's about:
1. **Reducing confusion** - Fewer, better-documented tools → better tool selection
2. **Improving success rate** - Agent picks the right tool on first try
3. **Enabling competence** - Agent should feel capable and helpful, not restrictive

### What This Means for Implementation

**DO:**
- Write rich docstrings with "Use when user wants to..." phrases
- Include examples showing common use cases
- Document the full range of what each action can do
- Make the agent feel empowered with each tool

**DON'T:**
- Create tools that say "this feature is not available"
- Leave gaps where user requests can't be fulfilled
- Make the agent apologize for missing capabilities
- Document limitations without providing alternatives

### Example: Good vs Bad Tool Behavior

**BAD Agent Response:**
> "I don't have a tool to delete products. You'll need to do that manually."

**GOOD Agent Response:**
> "I'll delete that product for you."
> `manage_product(action="delete", slug="old-product", confirm=True)`
> "Done! The product 'Old Product' has been deleted."

The consolidated tools must maintain **full functionality** - we're reorganizing, not removing capabilities.

---

## Summary

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Tool signatures | Tailored per domain | Avoids irrelevant params, agent is smart enough |
| Backwards compatibility | Not a concern | Desktop app, no external API consumers |
| Research tools | Keep as-is | Already well-scoped, 4 tools is fine |
| Agent behavior | Proactive tool usage | Tools exist to be used, not to apologize |

---

## Codex Review Decisions (3/3 Reviews)

| Codex Comment | Decision | Rationale |
|---------------|----------|-----------|
| How agent triggers `activate_skill` | **Accept** | Added system prompt instructions in 2.4 |
| `analyze_packaging` pagination missing | **Accept** | Added offset/limit params to signature |
| `update_packaging_text.field` enum | **Accept** | Defined as Literal["headline", "subheadline", "body", "tagline"] |
| Migration audit too narrow | **Accept** | Expanded to all 27+ removed/renamed tools |
| Consolidated tools weaken schema | **Discard** | Known trade-off; runtime validation is standard for action-discriminated tools |
| Tool refresh mid-run SDK confirm | **Accept** | Added verification step in testing |
| slug vs product_slug inconsistency | **Accept** | Standardized all to `slug` |
| Tool count inconsistencies | **Accept** | Fixed: Product 8→3, Todo 9→5 |
| `_resolve_tool` error handling | **Accept** | Added ValueError/RuntimeError with clear messages |
| `search_research_cache` missing | **Accept** | Added to SKILL_TOOL_MAPPING |
| Contextvars timing | **Discard** | Out of scope; Stage 4 remains optional |

---

## Pre-Implementation Verification Steps

Before starting implementation:

1. **Verify SDK supports mid-run tool refresh:**
   ```python
   # Test: Can agent use tools added after activate_skill in same run?
   # If not, need to implement re-invocation pattern
   ```

2. **Verify Literal types work with function_tool:**
   ```python
   # Test: Does @function_tool support Literal["create", "update", ...]?
   # If not, use Enum or add schema hints
   ```

3. **Audit all old tool references:**
   ```bash
   # Run grep commands from 5.1 and save results
   # Ensure migration covers all hits
   ```

---

## No Unresolved Questions

All design questions have been resolved. Implementation can proceed.
