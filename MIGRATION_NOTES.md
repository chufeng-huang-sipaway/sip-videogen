# Notes: OpenAI Responses API Migration

## Key Findings

### Responses API Basics
```python
# Simple request
response = client.responses.create(
    model="gpt-5.1",
    input="Hello",
    instructions="You are helpful.",  # Replaces system message
    store=True  # Enable server-side history
)

# Chain conversation using previous_response_id
response2 = client.responses.create(
    model="gpt-5.1",
    input="What did I say?",
    previous_response_id=response.id,  # Links to previous turn
    store=True
)
```

### Conversation Threading Options
1. **`previous_response_id`** - Chain responses together
2. **Conversations API** - More robust, manages conversation IDs

### Key Parameter Changes
| Chat Completions | Responses API |
|-----------------|---------------|
| `messages` | `input` (string or array) |
| `messages[0].role="system"` | `instructions` parameter |
| `response_format` | `text.format` |
| Manual history array | `previous_response_id` |
| Manual tool orchestration | Built-in agentic loop |

### Tools/Function Calling
- **Flatter schema** - No top-level "function" wrapper
- **Built-in tools** - web_search, image_generation, code_interpreter
- **Agentic loop** - Multi-tool calls in single request

### Truncation Options
- `truncation: "disabled"` (default) - Fails if too long
- `truncation: "auto"` - Auto-drops old messages
- `/responses/compact` endpoint - Server-side compaction

### SDK Version
- `openai>=2.15.0` required
- Full async/streaming support

### Benefits
- 40-80% better cache utilization (cheaper!)
- 3% better performance on benchmarks
- No client-side history management needed
- Server-side state preserved for 30 days

### Limitations
- `store=true` not available in non-US regions
- All previous tokens still billed (but cached better)

## Current Implementation Analysis

### SDK Used: `openai-agents` (NOT direct Chat Completions!)
The BrandAdvisor uses the **Agents SDK** which abstracts away the OpenAI API:
```python
from agents import Agent, Runner

self._agent = Agent(
    name="Brand Marketing Advisor",
    model="gpt-5.1",
    instructions=system_prompt,
    tools=ADVISOR_TOOLS,
)

# Non-streaming
result = await Runner.run(self._agent, prompt, hooks=hooks)

# Streaming
async for chunk in Runner.run_streamed(self._agent, prompt, hooks=hooks):
    yield chunk.text
```

### Direct OpenAI Client Usage (Utility only)
Only used for compaction/summarization:
```python
# session_history_manager.py
from openai import AsyncOpenAI
client = AsyncOpenAI()
response = await client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
)
```

### MAJOR DISCOVERY: SDK Already Uses Responses API!

The `openai-agents` SDK **already uses Responses API by default** via `OpenAIResponsesModel`.

**We don't need to migrate APIs - just enable server-side history!**

#### Option 1: Auto-chain responses
```python
result = await Runner.run(
    agent,
    "your message",
    auto_previous_response_id=True,  # Auto-chain all responses
)
```

#### Option 2: Use OpenAI Conversations API
```python
from agents.memory import OpenAIConversationsSession

session = OpenAIConversationsSession()  # Server-side storage!

result = await Runner.run(
    agent,
    "your message",
    session=session,
)
```

#### Option 3: Manual conversation ID
```python
result = await Runner.run(
    agent,
    "your message",
    conversation_id="conv_xyz789",  # Persistent conversation
)
```

### What This Means
- **No API migration needed** - already on Responses API
- **Just add parameters** to Runner.run() calls
- **Most compaction code can be deleted** - server handles truncation
- **Better caching** - 40-80% improvement automatically

### Files That Would Change
| File | Change |
|------|--------|
| `agent.py` | Agent/Runner configuration |
| `session_history_manager.py` | Direct OpenAI client calls |
| `session_manager.py` | Store `response_id` instead of full history |

### What Might Be Deleted
If Responses API handles history server-side:
- Auto-compaction logic (server handles truncation)
- Token counting/estimation
- Most of `session_history_manager.py`
