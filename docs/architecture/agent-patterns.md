# Agent Pattern Decisions
This document explains why Brand Studio maintains two distinct agent patterns for brand-related tasks.
## Overview
Brand Studio uses two agent architectures that serve fundamentally different purposes:
| Pattern | Agent | Use Case |
|---------|-------|----------|
| Conversational | BrandAdvisor | Ongoing multi-turn chat with dynamic skills |
| Orchestration | BrandDirector | One-shot brand creation with specialist agents |
## BrandAdvisor: Conversational Agent
**File**: `src/sip_videogen/advisor/agent.py`
**Model**: GPT-5.1 (272K context, adaptive reasoning)
### When to Use
- Interactive brand marketing conversations
- Tasks requiring multiple back-and-forth exchanges
- Skill-based operations (mascot generation, asset creation)
- Context-aware responses with conversation history
### Architecture
```
User Message
    ↓
[Skill Matching] → Load relevant SKILL.md files
    ↓
[Context Budget] → Trim history/skills if over budget
    ↓
[Agent Execution] → GPT-5.1 with 5 universal tools
    ↓
[History Update] → Add turn to conversation history
    ↓
Response
```
### Key Characteristics
- **Stateful**: Maintains `ConversationHistoryManager` across turns
- **Dynamic skills**: Loads skill instructions based on message triggers
- **Budget-aware**: Uses `ContextBudgetManager` to prevent context overflow
- **Tools**: `generate_image`, `read_file`, `write_file`, `list_files`, `load_brand`, `propose_choices`, `update_memory`
### Code Example
```python
advisor=BrandAdvisor(brand_slug="summit-coffee")
response=await advisor.chat("Create a playful mascot")
#Stateful - continues conversation
response=await advisor.chat("Make it more energetic")
```
## BrandDirector: Orchestration Agent
**File**: `src/sip_videogen/agents/brand_director.py`
**Model**: Default (orchestrator doesn't need large context)
### When to Use
- Creating complete brand identities from scratch
- Evolving existing brands with comprehensive changes
- Tasks requiring coordinated specialist work
- One-shot operations with structured output
### Architecture
```
Brand Concept
    ↓
[Brand Director] ← Orchestrator
    ├── brand_strategist   → Core identity, values, positioning
    ├── visual_designer    → Color palette, typography, imagery
    ├── brand_voice        → Personality, tone, messaging
    └── brand_guardian     → Validation, consistency check
    ↓
BrandIdentityFull (structured output)
```
### Key Characteristics
- **Stateless**: No conversation history; single task completion
- **Agent-as-tool**: Specialists are wrapped as `Tool` objects
- **Structured output**: Returns `BrandDirectorOutput` Pydantic model
- **Progress tracking**: Uses `RunHooks` for real-time status updates
### Code Example
```python
identity=await develop_brand(
    concept="A sustainable coffee brand targeting young professionals",
    progress_callback=lambda p:print(f"{p.agent_name}: {p.message}")
)
#Returns complete BrandIdentityFull - no further interaction needed
```
## Why Two Patterns?
### Different Cognitive Modes
**BrandAdvisor** serves **exploratory cognition**:
- User doesn't know exactly what they want
- Needs guidance and options
- Benefits from iterative refinement
- "Help me create a mascot" → discussion → refinement → final asset
**BrandDirector** serves **directive cognition**:
- User knows the outcome (complete brand identity)
- Requires coordinated multi-specialist work
- Single comprehensive output
- "Create a brand for my coffee startup" → full identity
### Unification Would Fail
Attempting to merge these patterns would result in:
1. **Bloated context**: Conversation history irrelevant for one-shot operations
2. **Confused orchestration**: Skills don't map to multi-agent coordination
3. **Poor UX**: Users would get chat responses when they want structured output
4. **Complexity**: Single agent trying to be both conversational and orchestrative
### When to Add New Agents
**Add to BrandAdvisor skills** when:
- Task is conversational
- Requires user refinement
- Can be expressed as markdown instructions
**Add as BrandDirector specialist** when:
- Task produces structured output component
- Requires coordination with other specialists
- Is part of brand identity creation
## File References
| Component | Path |
|-----------|------|
| BrandAdvisor | `src/sip_videogen/advisor/agent.py` |
| Skills registry | `src/sip_videogen/advisor/skills/registry.py` |
| Advisor tools | `src/sip_videogen/advisor/tools.py` |
| BrandDirector | `src/sip_videogen/agents/brand_director.py` |
| Strategist | `src/sip_videogen/agents/brand_strategist.py` |
| Visual designer | `src/sip_videogen/agents/visual_designer.py` |
| Voice writer | `src/sip_videogen/agents/brand_voice.py` |
| Guardian | `src/sip_videogen/agents/brand_guardian.py` |
