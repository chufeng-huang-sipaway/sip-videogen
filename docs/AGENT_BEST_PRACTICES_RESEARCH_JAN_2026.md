# Agent Building Best Practices Research - January 2026

## Executive Summary

This document presents research findings on AI agent building best practices as of January 2026, analyzes the current sip-videogen project's agent architecture against these practices, and provides specific recommendations for improvement.

**Key Finding**: The project already follows several best practices (single-agent-with-skills architecture, progressive disclosure, context budget management). However, there are significant opportunities for improvement in **guardrails**, **MCP integration**, **tool consolidation**, and **observability**.

---

## Part 1: Agent Building Best Practices (January 2026)

### 1.1 Core Principles

#### From Anthropic: Building Effective Agents
Sources: [Building Effective AI Agents](https://www.anthropic.com/research/building-effective-agents), [Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

1. **Start Simple, Add Complexity Only When Needed**
   - The most successful implementations use simple, composable patterns rather than complex frameworks
   - Consider whether you need agentic systems at all — they trade latency and cost for better task performance
   - Build with simple, composable patterns instead of specialized libraries

2. **Context Engineering > Prompt Engineering**
   - Context engineering is the natural progression of prompt engineering
   - Find the smallest possible set of high-signal tokens that maximize the likelihood of desired outcomes
   - LLMs are constrained by finite attention budgets — quality of context matters more than quantity

3. **Tool Design Deserves Equal Attention**
   - Tool definitions and specifications should receive as much prompt engineering attention as overall prompts
   - Even small refinements to tool descriptions can yield dramatic improvements
   - Claude Sonnet 3.5 achieved state-of-the-art performance on SWE-bench after precise refinements to tool descriptions

4. **Agents for Open-Ended Problems Only**
   - Use agents for problems where it's difficult to predict required steps and you can't hardcode a fixed path
   - The autonomous nature means higher costs and potential for compounding errors
   - Recommend extensive testing in sandboxed environments with appropriate guardrails

#### From OpenAI: Practical Guide to Building Agents
Sources: [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/), [Building Agents Track](https://developers.openai.com/tracks/building-agents/)

1. **Maximize Single Agent Capabilities First**
   - OpenAI's general recommendation is to maximize a single agent's capabilities before introducing multi-agent systems
   - Start with strong foundations: capable models + well-defined tools + clear, structured instructions
   - Evolve to multi-agent systems only when complexity warrants it

2. **Layered Guardrails Are Critical**
   - Think of guardrails as a layered defense mechanism
   - A single guardrail is unlikely to provide sufficient protection
   - Combine LLM-based guardrails, rules-based guardrails (regex), and moderation APIs
   - Support both parallel execution (best latency) and blocking execution (highest safety)

3. **Handoffs for Decentralized Control**
   - Handoffs pass application control from one agent to another as a one-way transfer
   - Think of agents as independent units; your application orchestrates them
   - In the Agents SDK, a handoff is a type of tool/function

### 1.2 Multi-Agent Design Patterns

#### Google's Eight Essential Multi-Agent Design Patterns
Source: [Google Multi-Agent Design Patterns (InfoQ)](https://www.infoq.com/news/2026/01/multi-agent-design-patterns/)

| Pattern | Use Case | Complexity |
|---------|----------|------------|
| **Sequential Pipeline** | Step-by-step processing with clear dependencies | Low |
| **Parallel Fan-Out** | Independent sub-tasks that can run concurrently | Medium |
| **Supervisor** | Best starting point for multi-agent setups | Medium |
| **Orchestrator-Worker** | "Digital symphony" of coordinated agents | High |
| **Group Chat** | Collaborative problem-solving through discussion | High |
| **Human-in-the-Loop** | High-stakes decisions requiring human authorization | Variable |
| **Hierarchical** | Complex organizations with sub-teams | High |
| **Reflection** | Self-evaluation and iterative improvement | Medium |

**Key Insight**: The supervisor pattern is usually the best place to start if your application calls for multi-agent setup.

### 1.3 Tool Design Best Practices

Source: [Writing Tools for Agents (Anthropic)](https://www.anthropic.com/engineering/writing-tools-for-agents)

1. **Tool Count Matters**
   - Research shows performance drops significantly when an agent has more than **10-15 tools**
   - Enterprise systems need hundreds of functions — this is a key reason to adopt multi-agent patterns
   - Consider tool consolidation or dynamic tool loading

2. **Documentation Quality**
   - Clear, precise tool descriptions improve success rates dramatically
   - Include example inputs/outputs in tool descriptions
   - Document edge cases and error conditions

3. **Agent-Computer Interface (ACI)**
   - Carefully craft your ACI through thorough tool documentation and testing
   - Prioritize transparency by explicitly showing the agent's planning steps
   - Maintain simplicity in your agent's design

### 1.4 Model Context Protocol (MCP) - The New Standard

Sources: [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/2025-11-25), [What is MCP (IBM)](https://www.ibm.com/think/topics/model-context-protocol)

1. **Industry Adoption**
   - OpenAI officially adopted MCP in March 2025
   - Anthropic donated MCP to the Agentic AI Foundation (AAIF) under Linux Foundation in December 2025
   - MCP creates "USB-C-like standardization" for AI tool connectivity

2. **Key Benefits**
   - Standardizes how models discover, select, and call tools
   - Enables any AI model to connect seamlessly with any data source or tool
   - Security teams can apply existing organizational policies to agent capabilities

3. **2026 Roadmap**
   - Agent-to-Agent communication extensions
   - MCP Servers acting as agents themselves
   - "Fractal" agentic systems where tasks decompose into sub-tasks handled by specialized sub-agents

4. **Enterprise Governance**
   - Trusted gateways and allowlisting for security
   - Protection against Tool Poisoning Attacks
   - Control context bloat for enterprise AI agents

### 1.5 Production Best Practices

Sources: [Best Practices for AI Agent Implementations](https://onereach.ai/blog/best-practices-for-ai-agent-implementations/), [Temporal Integration](https://temporal.io/blog/announcing-openai-agents-sdk-integration)

1. **Modular Design**
   - Design for flexibility and scalability from the start
   - Modular architecture enables growth and evolution
   - Compartmentalization mirrors proven software engineering patterns

2. **Memory Architecture**
   - Working memory holds current task data
   - Persistent memory recalls historical context across sessions
   - Vector databases store data as embeddings and retrieve by semantic similarity

3. **Security & Isolation**
   - Design agents to be as isolated as practical from each other
   - Single points of failure should not be shared between agents
   - Ensure compute isolation between agents

4. **Durable Execution**
   - OpenAI and Temporal integration adds durable execution to agents
   - Agents can recover from failures, network issues, and infrastructure problems
   - Critical for production reliability

5. **Observability**
   - Built-in tracing for visualization, debugging, and monitoring
   - OpenAI SDK includes evaluation, fine-tuning, and distillation tools
   - Essential for understanding agent behavior in production

---

## Part 2: Current Project Architecture Analysis

### 2.1 Architecture Overview

The sip-videogen project implements **two distinct agent patterns**:

#### A. Brand Marketing Advisor (Single Agent with Skills)
Location: `src/sip_studio/advisor/agent.py`

```
┌─────────────────────────────────────────────────────────────┐
│                    BrandAdvisor Agent                        │
│                      (GPT-5.1, 272K context)                 │
├─────────────────────────────────────────────────────────────┤
│  Skills (Progressive Disclosure)                             │
│  ├── image-composer                                          │
│  ├── image-prompt-engineering                                │
│  ├── logo-design                                             │
│  ├── brand-identity                                          │
│  └── product-management                                      │
├─────────────────────────────────────────────────────────────┤
│  Tools (35+ universal tools)                                 │
│  ├── generate_image, propose_images                          │
│  ├── create_product, update_product, delete_product          │
│  ├── create_style_reference, analyze_product_packaging       │
│  ├── web_search, request_deep_research                       │
│  └── ... and more                                            │
├─────────────────────────────────────────────────────────────┤
│  State Management                                            │
│  ├── SessionManager (CRUD for sessions)                      │
│  ├── SessionHistoryManager (auto-compaction)                 │
│  ├── SessionContextCache (lean context ~300 tokens)          │
│  └── ContextBudgetManager (250K token limit)                 │
└─────────────────────────────────────────────────────────────┘
```

#### B. Video Generation Orchestration (Multi-Agent Team)
Location: `src/sip_studio/agents/`

```
┌─────────────────────────────────────────────────────────────┐
│                    Showrunner (Orchestrator)                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│    ┌─────────────┐    ┌───────────────────┐                 │
│    │ Screenwriter │ → │ ProductionDesigner │                │
│    └─────────────┘    └───────────────────┘                 │
│           │                    │                             │
│           ▼                    ▼                             │
│    ┌─────────────────────────────────────┐                  │
│    │       ContinuitySupervisor           │                  │
│    └─────────────────────────────────────┘                  │
│                       │                                      │
│                       ▼                                      │
│              ┌──────────────┐                                │
│              │ MusicDirector │                               │
│              └──────────────┘                                │
│                       │                                      │
│                       ▼                                      │
│        VideoScript + MusicBrief (Output)                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Strengths (Aligned with Best Practices)

| Best Practice | Project Implementation | Score |
|---------------|----------------------|-------|
| **Single agent first** | Brand Advisor uses single-agent-with-skills pattern | ✅ Excellent |
| **Progressive disclosure** | Skills inject activation prompts (~200 tokens) vs full instructions (10K+) | ✅ Excellent |
| **Context engineering** | ContextBudgetManager, SessionContextCache, lean context mode | ✅ Excellent |
| **Session management** | SessionHistoryManager with auto-compaction, response ID chaining | ✅ Excellent |
| **Error handling** | Tenacity retry, context overflow recovery, MaxTurnsExceeded handling | ✅ Good |
| **Multi-agent for complex tasks** | Video generation uses orchestrator pattern | ✅ Good |
| **Agent-as-tool pattern** | Agents expose themselves as tools for orchestration | ✅ Good |
| **Structured outputs** | Pydantic models for all agent outputs | ✅ Good |
| **Dynamic turn management** | Task estimation with pattern matching | ✅ Good |

### 2.3 Gaps & Improvement Opportunities

| Best Practice | Current State | Impact |
|---------------|--------------|--------|
| **Guardrails** | ❌ No guardrails implementation | High |
| **MCP integration** | ❌ No MCP support | Medium-High |
| **Tool count** | ⚠️ 35+ tools (recommended <15) | Medium |
| **Observability/Tracing** | ⚠️ Basic logging only | Medium |
| **Tool documentation** | ⚠️ Docstrings only, no examples | Medium |
| **Durable execution** | ❌ No Temporal/durable workflow support | Medium |
| **Agent isolation** | ⚠️ Module-level globals for state | Low-Medium |

---

## Part 3: Specific Improvement Recommendations

### 3.1 HIGH PRIORITY: Implement Guardrails

**Current State**: No input validation or output guardrails.

**Recommendation**: Implement layered guardrails using OpenAI Agents SDK patterns.

```python
# Proposed: src/sip_studio/advisor/guardrails.py

from agents import InputGuardrail, OutputGuardrail, GuardrailTripwireTriggered

class ContentPolicyGuardrail(InputGuardrail):
    """Block inappropriate content requests."""

    async def check(self, input_text: str) -> bool:
        # Use fast model (gpt-4o-mini) for validation
        # Return False to block, True to allow
        pass

class PIIDetectionGuardrail(OutputGuardrail):
    """Detect and redact PII in outputs."""

    async def check(self, output_text: str) -> str:
        # Scan for PII patterns
        # Redact or raise GuardrailTripwireTriggered
        pass

class BrandSafetyGuardrail(OutputGuardrail):
    """Ensure outputs align with brand guidelines."""

    async def check(self, output_text: str, brand_context: dict) -> str:
        # Validate against brand voice, prohibited terms, etc.
        pass

# Usage in BrandAdvisor:
self._agent = Agent(
    name="Brand Marketing Advisor",
    model="gpt-5.1",
    instructions=system_prompt,
    tools=ADVISOR_TOOLS,
    input_guardrails=[ContentPolicyGuardrail()],
    output_guardrails=[PIIDetectionGuardrail(), BrandSafetyGuardrail()],
)
```

**Benefits**:
- Prevent malicious/inappropriate requests before expensive model calls
- Ensure output quality and brand alignment
- Add compliance layer for enterprise use cases

---

### 3.2 HIGH PRIORITY: Tool Consolidation Strategy

**Current State**: 35+ tools, exceeding recommended 10-15 tool limit.

**Recommendation**: Implement dynamic tool loading based on skill activation.

```python
# Proposed: Dynamic tool sets per skill

CORE_TOOLS = [
    # Always available (5-7 tools)
    generate_image,
    propose_images,
    propose_choices,
    load_brand,
    activate_skill,
]

SKILL_TOOL_MAPPING = {
    "image-composer": [generate_image, propose_images],
    "product-management": [
        create_product, update_product, delete_product,
        add_product_image, set_product_primary_image,
    ],
    "style-references": [
        create_style_reference, update_style_reference,
        add_style_reference_image, reanalyze_style_reference,
    ],
    "research": [
        web_search, request_deep_research,
        get_research_status, search_research_cache,
    ],
}

class BrandAdvisor:
    def _get_tools_for_turn(self, activated_skills: list[str]) -> list:
        """Dynamically compose tool set based on active skills."""
        tools = list(CORE_TOOLS)
        for skill in activated_skills:
            if skill in SKILL_TOOL_MAPPING:
                tools.extend(SKILL_TOOL_MAPPING[skill])
        return tools  # Typically 10-15 tools per turn
```

**Alternative**: Consolidate related tools into single tools with modes:

```python
# Before: 5 separate product tools
create_product, update_product, delete_product, add_product_image, set_product_primary_image

# After: 1 consolidated tool
@function_tool
async def manage_product(
    action: Literal["create", "update", "delete", "add_image", "set_primary_image"],
    slug: str,
    **kwargs
) -> str:
    """Unified product management tool."""
    pass
```

---

### 3.3 MEDIUM PRIORITY: MCP Integration

**Current State**: No MCP support. Custom tool implementations for external services.

**Recommendation**: Adopt MCP for external tool connectivity.

```python
# Proposed: src/sip_studio/mcp/server.py

from mcp import MCPServer, Tool, Resource

class SipStudioMCPServer(MCPServer):
    """MCP Server exposing sip-studio capabilities."""

    @Tool
    async def generate_brand_image(
        self, prompt: str, brand_slug: str, aspect_ratio: str = "1:1"
    ) -> dict:
        """Generate brand-aligned image via MCP."""
        # Expose internal capabilities via MCP protocol
        pass

    @Resource
    async def get_brand_context(self, brand_slug: str) -> dict:
        """Expose brand context as MCP resource."""
        pass

# Benefits:
# 1. Standardized interface for external AI agents
# 2. Security governance via MCP gateways
# 3. Future-proof for agent-to-agent communication
```

**Migration Path**:
1. Wrap existing tools as MCP-compatible endpoints
2. Add MCP server for external integration
3. Enable MCP client for consuming external MCP services (e.g., file systems, databases)

---

### 3.4 MEDIUM PRIORITY: Enhanced Observability

**Current State**: Basic Python logging with `get_logger()`.

**Recommendation**: Implement comprehensive tracing and observability.

```python
# Proposed: src/sip_studio/observability/tracing.py

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

tracer = trace.get_tracer("sip_studio.advisor")

class ObservableAdvisorHooks(AdvisorHooks):
    """Hooks with OpenTelemetry tracing."""

    async def on_agent_start(self, context, agent):
        with tracer.start_as_current_span("agent.run") as span:
            span.set_attribute("agent.name", agent.name)
            span.set_attribute("agent.model", agent.model)

    async def on_tool_start(self, context, agent, tool):
        with tracer.start_as_current_span(f"tool.{tool.name}") as span:
            span.set_attribute("tool.name", tool.name)

    async def on_llm_start(self, context, agent):
        with tracer.start_as_current_span("llm.call") as span:
            span.set_attribute("model", agent.model)
            span.set_attribute("tokens.system", len(agent.instructions or ""))

# Metrics to track:
# - Tool success/failure rates
# - Latency per tool/agent
# - Token usage per turn
# - Guardrail trigger rates
# - Session length distribution
```

---

### 3.5 MEDIUM PRIORITY: Improve Tool Documentation

**Current State**: Basic docstrings without examples.

**Recommendation**: Rich tool descriptions following Anthropic's guidance.

```python
# Before
@function_tool
async def generate_image(prompt: str, aspect_ratio: str = "1:1") -> str:
    """Generate an image using AI."""
    pass

# After
@function_tool
async def generate_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    reference_image: str | None = None,
) -> str:
    """Generate a brand-aligned image using AI image generation.

    This tool creates high-quality images based on detailed text prompts.
    For best results, use the image-composer and image-prompt-engineering
    skills to craft prompts before calling this tool.

    Args:
        prompt: Detailed image description (80+ words recommended).
            Should include: subject, setting, lighting, mood, style, camera angle.
            Example: "A professional product photograph of artisanal coffee beans
            in a rustic ceramic bowl, warm morning sunlight streaming through
            a kitchen window, shallow depth of field, earthy brown tones with
            golden highlights, lifestyle photography style, shot from 45-degree
            angle above"
        aspect_ratio: Image dimensions. Options:
            - "1:1" (square, best for social media posts)
            - "16:9" (landscape, best for headers/banners)
            - "9:16" (portrait, best for stories/reels)
            - "4:3" (standard photo ratio)
        reference_image: Optional path to reference image for style guidance.
            The AI will extract visual style elements (colors, mood, composition)
            from this image while creating new content.

    Returns:
        Path to generated image file (e.g., "images/generated_001.png")

    Raises:
        ImageGenerationError: If generation fails after retries.
        ContentPolicyError: If prompt violates content policies.

    Examples:
        # Basic usage
        >>> await generate_image("A golden retriever playing in autumn leaves")
        "images/generated_golden_retriever.png"

        # With aspect ratio
        >>> await generate_image(
        ...     "Product shot of wireless earbuds on marble surface",
        ...     aspect_ratio="1:1"
        ... )
        "images/generated_earbuds.png"

        # With style reference
        >>> await generate_image(
        ...     "Modern minimalist logo for tech startup",
        ...     reference_image="references/brand_style.png"
        ... )
        "images/generated_logo.png"
    """
    pass
```

---

### 3.6 LOW-MEDIUM PRIORITY: State Isolation Improvement

**Current State**: Module-level globals for pending interactions.

```python
# Current pattern in tools/
_pending_interaction = None
_pending_memory_update = None
_pending_research_clarification = None
```

**Recommendation**: Request-scoped context using contextvars.

```python
# Proposed: src/sip_studio/advisor/context.py

from contextvars import ContextVar
from dataclasses import dataclass

@dataclass
class TurnContext:
    """Request-scoped context for a single conversation turn."""
    session_id: str
    brand_slug: str
    pending_interaction: dict | None = None
    pending_memory_update: dict | None = None
    pending_research: dict | None = None
    tool_results: list = field(default_factory=list)

# Context variable for request-scoped state
turn_context: ContextVar[TurnContext] = ContextVar("turn_context")

# Usage in tools:
@function_tool
async def propose_choices(options: list[str]) -> str:
    ctx = turn_context.get()
    ctx.pending_interaction = {"type": "choices", "options": options}
    return "Waiting for user selection"
```

---

### 3.7 LOW PRIORITY: Durable Execution for Long-Running Tasks

**Current State**: No durable workflow support. Long tasks can fail without recovery.

**Recommendation**: Consider Temporal integration for video generation pipeline.

```python
# Proposed: src/sip_studio/workflows/video_generation.py

from temporalio import workflow, activity
from temporalio.client import Client

@activity.defn
async def develop_scenes(idea: str, num_scenes: int) -> dict:
    """Durable scene development activity."""
    return await screenwriter_agent.develop_scenes(idea, num_scenes)

@activity.defn
async def identify_elements(scenes: dict) -> dict:
    """Durable production design activity."""
    return await production_designer_agent.identify_shared_elements(scenes)

@workflow.defn
class VideoGenerationWorkflow:
    """Durable video generation with automatic retry and recovery."""

    @workflow.run
    async def run(self, idea: str, num_scenes: int) -> dict:
        # Each step is durable - survives crashes/restarts
        scenes = await workflow.execute_activity(
            develop_scenes, args=[idea, num_scenes],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        elements = await workflow.execute_activity(
            identify_elements, args=[scenes],
            start_to_close_timeout=timedelta(minutes=3),
        )

        # ... continue with other steps
        return {"scenes": scenes, "elements": elements}
```

---

## Part 4: Implementation Roadmap

### Phase 1: Quick Wins (1-2 weeks)
1. **Tool documentation enhancement** - Update tool docstrings with examples
2. **Basic input guardrail** - Add content policy check before agent execution
3. **Tool consolidation analysis** - Identify tools that can be merged

### Phase 2: Core Improvements (2-4 weeks)
1. **Implement guardrail system** - Input and output guardrails with layered defense
2. **Dynamic tool loading** - Load tools based on activated skills
3. **Enhanced observability** - Add OpenTelemetry tracing

### Phase 3: Strategic Enhancements (4-8 weeks)
1. **MCP server implementation** - Expose capabilities via MCP protocol
2. **State isolation refactor** - Move to contextvars-based state management
3. **Durable execution** - Temporal integration for video pipeline

### Phase 4: Future Considerations
1. **MCP client integration** - Consume external MCP services
2. **Agent-to-agent communication** - As MCP 2026 roadmap delivers
3. **Fine-tuning pipeline** - Use observability data for model improvement

---

## Part 5: Summary

### What the Project Does Well

1. **Architecture Choice**: Single-agent-with-skills for Brand Advisor is exactly what Anthropic and OpenAI recommend — maximizing single agent capabilities before going multi-agent.

2. **Progressive Disclosure**: The skills system with activation prompts (~200 tokens) vs full instructions (10K+) is excellent context engineering.

3. **Context Management**: ContextBudgetManager, SessionHistoryManager with auto-compaction, and lean context mode demonstrate sophisticated context engineering.

4. **Error Handling**: Tenacity retry patterns, context overflow recovery, and MaxTurnsExceeded handling show production-readiness.

5. **Structured Outputs**: Pydantic models for all agent outputs ensure type safety and validation.

### Key Improvements Needed

| Priority | Improvement | Effort | Impact |
|----------|-------------|--------|--------|
| 🔴 High | Guardrails (input/output validation) | Medium | High |
| 🔴 High | Tool consolidation (<15 tools) | Medium | High |
| 🟡 Medium | MCP integration | High | Medium-High |
| 🟡 Medium | Enhanced observability | Medium | Medium |
| 🟡 Medium | Tool documentation | Low | Medium |
| 🟢 Low | State isolation (contextvars) | Medium | Low-Medium |
| 🟢 Low | Durable execution (Temporal) | High | Medium |

### Conclusion

The sip-videogen project demonstrates strong alignment with 2026 agent building best practices in its core architecture. The main gaps are in **safety/guardrails** and **tool management**. Implementing the recommended guardrails and tool consolidation strategies would bring the project to industry-leading standards.

---

## References

### Primary Sources
- [Building Effective AI Agents - Anthropic](https://www.anthropic.com/research/building-effective-agents)
- [Effective Context Engineering for AI Agents - Anthropic](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Writing Tools for Agents - Anthropic](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [OpenAI Agents SDK Documentation](https://openai.github.io/openai-agents-python/)
- [OpenAI Building Agents Track](https://developers.openai.com/tracks/building-agents/)
- [OpenAI Agents SDK Guardrails](https://openai.github.io/openai-agents-python/guardrails/)
- [OpenAI Agents SDK Handoffs](https://openai.github.io/openai-agents-python/handoffs/)

### Design Patterns
- [Google's Eight Essential Multi-Agent Design Patterns - InfoQ](https://www.infoq.com/news/2026/01/multi-agent-design-patterns/)
- [AI Agent Orchestration Patterns - Azure](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)
- [Agent System Design Patterns - Databricks](https://docs.databricks.com/aws/en/generative-ai/guide/agent-system-design-patterns)
- [Choose Design Pattern for Agentic AI - Google Cloud](https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system)

### MCP & Standards
- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [Introducing Model Context Protocol - Anthropic](https://www.anthropic.com/news/model-context-protocol)
- [What is MCP - IBM](https://www.ibm.com/think/topics/model-context-protocol)

### Production & Enterprise
- [Best Practices for AI Agent Implementations - OneReach](https://onereach.ai/blog/best-practices-for-ai-agent-implementations/)
- [Production-ready Agents with OpenAI SDK + Temporal](https://temporal.io/blog/announcing-openai-agents-sdk-integration)
- [Complete Guide to AI Agent Architecture - Lindy](https://www.lindy.ai/blog/ai-agent-architecture)

---

*Document generated: January 2026*
*Project: sip-videogen*
*Analysis scope: Brand Marketing Advisor, Video Generation Agents*
