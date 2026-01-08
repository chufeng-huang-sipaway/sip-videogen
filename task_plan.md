# Task Plan: Chat Settings Redesign

## Goal
Transform the chat interface settings from "generation-first commands" to "passive defaults" that only apply when the agent decides to generate, while enabling the agent to have natural conversations without defaulting to image generation.

## Problem Analysis

### Current Issues

1. **UI Signals Wrong Intent**
   - Aspect ratio selector is prominent (suggests "generate now")
   - Image/Video is a toggle (suggests exclusive choice)
   - Settings feel like commands, not preferences

2. **Agent Prompt Too Aggressive**
   - Line 3: "Your job is to GENERATE images, not to advise or plan"
   - Line 88-101: "Core Principle: Action First" pushes immediate generation
   - Blocks natural conversation, consulting, brainstorming

3. **Data Flow Incorrect**
   - Settings injected as context instructions telling agent to generate
   - `advisor/agent.py:185-191`: "**Generation Mode**: Image - Generate images using generate_image tool"
   - This pushes generation even when user wants conversation

### Desired Behavior

1. **Settings as Passive Defaults**
   - Stored per-brand, applied only when generating
   - Both image AND video settings coexist (not exclusive)
   - Tucked away in settings popup (not prominent)

2. **Conversational Agent**
   - Can brainstorm, consult, advise, ideate
   - Only generates when explicitly requested
   - Reads settings when it decides to generate

## Phases

- [x] Phase 1: Research & Design
- [x] Phase 2: UI Implementation (Settings Button + Popup)
- [x] Phase 3: Backend Data Model Update
- [x] Phase 4: Agent Prompt Tuning
- [x] Phase 5: Testing & Polish

---

## Phase 1: Research & Design

### Files to Analyze
- [x] `src/sip_studio/studio/frontend/src/components/ChatPanel/index.tsx` - Current chat UI
- [x] `src/sip_studio/studio/frontend/src/components/ChatPanel/AspectRatioSelector.tsx` - Current selector
- [x] `src/sip_studio/studio/frontend/src/hooks/useChat.ts` - State management
- [x] `src/sip_studio/studio/frontend/src/types/aspectRatio.ts` - Type definitions
- [x] `src/sip_studio/advisor/prompts/advisor.md` - Agent system prompt
- [x] `src/sip_studio/advisor/agent.py` - Context injection logic

### Key Findings

**Available Aspect Ratios (from Playground):**
| Ratio | Label | Platform Hint |
|-------|-------|---------------|
| 1:1 | Square | Instagram, Feed |
| 16:9 | Landscape | YouTube, Web |
| 9:16 | Portrait | TikTok, Reels |
| 4:3 | Classic | Presentation |
| 3:4 | Portrait Classic | Social |
| 3:2 | Photo | Photography |
| 2:3 | Portrait Photo | Portrait |
| 4:5 | Portrait | Instagram Post |
| 5:4 | Landscape | Print |

**Video Constraints (VEO):**
- Only 16:9 and 9:16 supported
- Duration: 4, 6, or 8 seconds

### Design Decisions

**UI Design:**
1. Replace AspectRatioSelector + ModeToggle with single **Settings button** (gear icon)
2. Settings button opens **popup/popover** with:
   - **Image Defaults** section
     - Aspect ratio dropdown (9 options)
   - **Video Defaults** section
     - Aspect ratio toggle (16:9 / 9:16)
3. Show current settings as subtle hint text below button (e.g., "Image: 16:9 | Video: 9:16")
4. Remove AutonomyToggle from main UI (move to settings or remove entirely)

**Data Model:**
```typescript
interface ChatPreferences {
  imageAspectRatio: AspectRatio  // Default: '16:9'
  videoAspectRatio: '16:9' | '9:16'  // Default: '16:9'
}
```

**Agent Context Injection:**
- Remove generation mode injection ("Generate images using generate_image tool")
- Remove aspect ratio instruction from turn context
- Settings only read by tools when generating (already happens via `set_active_aspect_ratio`)

**Agent Prompt Changes:**
- Remove "Your job is to GENERATE images" language
- Remove "Action First" principle
- Add conversational capability framing
- Emphasize: generate only when explicitly requested

---

## Phase 2: UI Implementation

### Tasks
- [ ] 2.1 Create `GenerationSettings` component (popup)
  - Image aspect ratio dropdown
  - Video aspect ratio toggle
  - Compact, non-intrusive design
- [ ] 2.2 Create `SettingsButton` component (gear icon trigger)
  - Small gear icon
  - Shows current settings summary on hover/below
- [ ] 2.3 Update `ChatPanel/index.tsx`
  - Remove `AspectRatioSelector`
  - Remove `ModeToggle`
  - Add `SettingsButton` near input area
- [ ] 2.4 Update `useChat.ts` hook
  - Change state: `aspectRatio` → `imageAspectRatio` + `videoAspectRatio`
  - Update persistence logic
- [ ] 2.5 Update bridge types and calls
  - Update `ChatContext` interface
  - Update `saveChatPrefs` / `getChatPrefs`

### Component Placement
```
┌─────────────────────────────────────────────────┐
│  Chat messages area                             │
│                                                 │
│                                                 │
├─────────────────────────────────────────────────┤
│ [+] Type @ to mention...          [⚙️] [↑]     │
│                              Image: 16:9        │
│                              Video: 9:16        │
└─────────────────────────────────────────────────┘
```

---

## Phase 3: Backend Data Model Update

### Tasks
- [ ] 3.1 Update `ChatPrefs` model in storage
  - Add `image_aspect_ratio`, `video_aspect_ratio`
  - Deprecate `aspect_ratio`, `generation_mode`
- [ ] 3.2 Update bridge.py
  - Update `save_chat_prefs()` signature
  - Update `get_chat_prefs()` return
- [ ] 3.3 Migration logic for existing prefs
  - Map old `aspect_ratio` → `image_aspect_ratio`
  - Default `video_aspect_ratio` to '16:9'

---

## Phase 4: Agent Prompt Tuning

### Tasks
- [ ] 4.1 Rewrite `advisor.md` introduction
  - Remove "Your job is to GENERATE images"
  - Frame as versatile brand advisor
- [ ] 4.2 Remove "Action First" section
  - Replace with balanced approach
  - Generate when explicitly requested
- [ ] 4.3 Add conversation capability section
  - Brainstorming, consulting, ideation
  - Answer questions without generating
- [ ] 4.4 Update aspect ratio handling
  - Remove context injection of aspect ratio instruction
  - Tools read from session state (already implemented)

### Prompt Direction

**FROM:**
```
You CREATE marketing assets on demand. Your job is to GENERATE images, not to advise or plan.
...
Core Principle: Action First
When user asks for an image → CALL generate_image IMMEDIATELY.
```

**TO:**
```
You are a versatile brand advisor and creative partner. You can:
- Have natural conversations about branding, marketing, and creative direction
- Brainstorm ideas and provide strategic consulting
- Generate images and videos when explicitly requested

Generate only when the user explicitly asks you to create visual content.
For questions, discussions, or brainstorming, engage conversationally without generating.
```

---

## Phase 5: Testing & Polish

### Tasks
- [ ] 5.1 Test conversation flow (no auto-generation)
- [ ] 5.2 Test explicit generation request (uses correct settings)
- [ ] 5.3 Test settings persistence across sessions
- [ ] 5.4 Test migration from old prefs format
- [ ] 5.5 Visual polish and accessibility

---

## Status
**COMPLETED** - All phases implemented and build passing

## Key Questions
1. ~~Should AutonomyToggle remain?~~ → Keep it for supervised mode (useful feature)
2. ~~Where to place settings button?~~ → Near input box, right side
3. ~~How to show current settings?~~ → Small hint text below button

## Decisions Made
- Settings button with popup over inline selectors (cleaner UI)
- Both image and video settings coexist (not exclusive)
- Agent prompt needs significant rewrite (too generation-focused)
- Remove context injection of generation instructions
