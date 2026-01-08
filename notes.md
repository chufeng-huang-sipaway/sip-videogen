# Notes: Chat Settings Redesign

## Current Implementation Analysis

### Frontend Data Flow
```
ChatPanel → useChat hook → bridge.chat() → ChatService → BrandAdvisor.chat_with_metadata()
                ↓
         aspectRatio, generationMode stored in state
                ↓
         Passed via ChatContext to bridge
                ↓
         Injected into agent turn context (THIS IS THE PROBLEM)
```

### Problem Code Locations

**1. Context Injection (advisor/agent.py:184-191)**
```python
if inject_generation_mode:
    mode = generation_mode if generation_mode in ("image", "video") else "image"
    mode_ctx = f"**Generation Mode**: {mode.capitalize()} - {'Generate videos...' if mode == 'video' else 'Generate images...'}"
    turn_context = f"{turn_context}\n\n{mode_ctx}"
    if aspect_ratio:
        set_active_aspect_ratio(aspect_ratio)
        ar_ctx = f"**Aspect Ratio**: Use {aspect_ratio} for any image or video generation."
        turn_context = f"{turn_context}\n\n{ar_ctx}"
```

This injects instructions that push the agent toward generation even for conversational requests.

**2. Agent Prompt (advisor/prompts/advisor.md:1-3, 88-101)**
```markdown
# Brand Production Tool
You CREATE marketing assets on demand. Your job is to GENERATE images, not to advise or plan.
...
## Core Principle: Action First
When user asks for an image → CALL `generate_image` IMMEDIATELY.
```

This framing prevents the agent from having natural conversations.

### What Should Change

**Context Injection:**
- REMOVE generation mode instruction entirely
- KEEP `set_active_aspect_ratio()` call (tools read this when generating)
- Settings become passive defaults, not active instructions

**Agent Prompt:**
- Reframe as versatile advisor, not production tool
- Allow conversational engagement
- Generate only on explicit request

---

## UI Component Structure

### Current (to be removed)
```
ChatPanel
├── ModeToggle (Image | Video toggle)
├── AspectRatioSelector (varies by mode)
└── AutonomyToggle (Supervised toggle)
```

### New Structure
```
ChatPanel
├── SettingsButton (⚙️ icon)
│   └── GenerationSettingsPopup
│       ├── ImageSettings
│       │   └── AspectRatioDropdown (9 options)
│       └── VideoSettings
│           └── AspectRatioToggle (16:9 | 9:16)
└── AutonomyToggle (keep as-is, or move to settings)
```

---

## Type Changes

### Current Types
```typescript
// useChat.ts state
aspectRatio: AspectRatio  // Single value
generationMode: GenerationMode  // 'image' | 'video'

// ChatContext
aspect_ratio?: AspectRatio
generation_mode?: GenerationMode
```

### New Types
```typescript
// useChat.ts state
imageAspectRatio: AspectRatio  // Default for image generation
videoAspectRatio: VideoAspectRatio  // '16:9' | '9:16'

// ChatContext
image_aspect_ratio?: AspectRatio
video_aspect_ratio?: VideoAspectRatio
// REMOVE generation_mode - not needed as instruction
```

---

## Backend Changes

### Bridge API Updates

**getChatPrefs response:**
```python
# Old
{"aspect_ratio": "16:9", "generation_mode": "image"}

# New
{"image_aspect_ratio": "16:9", "video_aspect_ratio": "16:9"}
```

**saveChatPrefs signature:**
```python
# Old
def save_chat_prefs(brand_slug, aspect_ratio, generation_mode)

# New
def save_chat_prefs(brand_slug, image_aspect_ratio, video_aspect_ratio)
```

### Tool Context

The `set_active_aspect_ratio()` mechanism is actually good - tools read this when generating.

What needs to change is HOW/WHEN it's set:
- Currently: Set from chat context for every message
- New: Set based on which type of generation is requested
  - Image generation → use imageAspectRatio
  - Video generation → use videoAspectRatio

This means the advisor/agent.py needs to:
1. Receive both aspect ratios
2. NOT inject them as instructions
3. Store them in session state
4. Tools read appropriate one based on generation type

---

## Files to Modify

### Frontend
- `components/ChatPanel/index.tsx` - Main changes
- `components/ChatPanel/AspectRatioSelector.tsx` - Keep for reuse in popup
- `components/ChatPanel/ModeToggle.tsx` - DELETE
- `hooks/useChat.ts` - State model change
- `lib/bridge.ts` - ChatContext type update
- `types/aspectRatio.ts` - Add VideoAspectRatio type

### Backend
- `studio/bridge.py` - API signature update
- `studio/services/chat_service.py` - Pass both ratios
- `advisor/agent.py` - Remove context injection, store both ratios
- `advisor/prompts/advisor.md` - Prompt rewrite
- `advisor/tools/image_tools.py` - May need to read from session differently

---

## Testing Scenarios

1. **Conversation without generation**
   - User: "What makes a good hero image?"
   - Agent: [Discusses without generating] ✓

2. **Explicit generation request**
   - User: "Generate a hero image for my product"
   - Agent: [Generates using stored imageAspectRatio] ✓

3. **Video generation**
   - User: "Create a short video showcasing this"
   - Agent: [Generates using stored videoAspectRatio] ✓

4. **Settings change**
   - User changes image ratio to 9:16
   - User: "Generate an image"
   - Agent: [Generates with 9:16] ✓

5. **Brainstorming session**
   - User: "Give me 5 ideas for summer campaign"
   - Agent: [Lists ideas, doesn't generate] ✓
   - User: "Love idea 3, generate that"
   - Agent: [Now generates] ✓
