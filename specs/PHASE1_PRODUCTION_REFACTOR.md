# Phase 1: Production Refactor Specification
## Enhanced Chat Agent + Image Generator Toolbox

**Version**: 1.0
**Date**: 2026-01-07
**Status**: Draft

---

## Executive Summary

This specification defines a major refactor of Sip Studio's image production experience. We are splitting the current chat interface into two distinct modes:

1. **Enhanced Chat Agent** - An intelligent, Claude Code-like assistant that handles ideation, brainstorming, and complex multi-step tasks autonomously
2. **Image Generator Toolbox** - A quick, no-conversation tool for users who already know what they want

The goal is to serve two user types: those who need guidance and ideation support, and those who just need fast execution.

---

## Problem Statement

### Current State
The existing chat interface works well for specific image generation tasks (3-5 iterations to completion). However, it falls short in two scenarios:

1. **Ideation Gap**: Users who don't have a clear prompt struggle. They need brainstorming, suggestions, and exploration—not just execution.

2. **Speed Gap**: Users who DO have a clear idea must go through conversational UI when they just want quick image generation.

### User Pain Points
- Non-technical users with good taste can't articulate prompts but can give feedback
- No support for complex, multi-step tasks (e.g., "generate 10 campaign ideas with 5 images each")
- No visibility into what the agent is doing during long operations
- No way to interrupt or redirect mid-task
- Users who know what they want still go through chat friction

---

## Goals

### Must Have (P0)
- [ ] Chat agent can create and display inline to-do lists for multi-step tasks
- [ ] Chat agent shows real-time progress on task execution
- [ ] User can interrupt/stop the agent mid-task
- [ ] Autonomy toggle: auto-execute vs. propose-and-wait modes
- [ ] Image Generator toolbox as floating quick-action
- [ ] Agent can create/update style references, products, projects on user's behalf

### Should Have (P1)
- [ ] Agent remembers context when interrupted (can resume)
- [ ] Approval UI with "Approve" / "Accept Auto" / "Something else" buttons
- [ ] Batch image generation (1-10 images in toolbox)
- [ ] Progress UI that feels responsive and informative

### Nice to Have (P2)
- [ ] Agent proactively suggests when to use toolbox vs. chat
- [ ] Keyboard shortcuts for common actions
- [ ] Sound/notification when long task completes

---

## Non-Goals (Out of Scope)

- **Conversation persistence** - Handled in Phase 2
- **Conversation history sidebar** - Handled in Phase 2
- **Memory compacting strategy** - Handled in Phase 2
- **Video generation improvements** - Separate initiative
- **Multi-brand conversations** - Brand must be selected first
- **Collaborative features** - Single user for now

---

## User Stories

### User Type A: The Tastemaker (Non-Technical)
> "I have good taste but can't write prompts. I know what's wrong when I see it, but I can't describe what I want from scratch."

**Story A1**: As a tastemaker, I want to have a brainstorming session with the agent so that I can explore ideas without knowing exactly what I want.

**Story A2**: As a tastemaker, I want to give feedback like "too average, make it wilder" and have the agent understand and iterate.

**Story A3**: As a tastemaker, I want to say "generate 10 campaign ideas" and come back after lunch to pick my favorites.

### User Type B: The Executor (Knows What They Want)
> "I already have the idea. I just need to see it visualized quickly."

**Story B1**: As an executor, I want to quickly generate 5 versions of my idea without going through a conversation.

**Story B2**: As an executor, I want to select my product, style reference, and aspect ratio, type my prompt, and get images immediately.

---

## Feature Specifications

### Feature 1: Enhanced Chat Agent

#### 1.1 Inline To-Do List

**Trigger**: When the agent identifies a multi-step task (e.g., "generate 10 ideas with images for each")

**Behavior**:
1. Agent analyzes the request and breaks it into discrete tasks
2. Agent renders a to-do list inline in the chat
3. Each item shows: task description, status (pending/in-progress/done/error)
4. List updates in real-time as tasks complete
5. Completed items show generated outputs (images) inline

**UI Mockup**:
```
┌─────────────────────────────────────────────────────┐
│ 🤖 Agent: I'll generate 10 Valentine's campaign     │
│    ideas with 3 images each. Here's my plan:       │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ □ Idea 1: Romantic sunset run          ⏳ 2/3   │ │
│ │   [img1] [img2] [generating...]                 │ │
│ │ □ Idea 2: Heart-shaped trail           ○ pending│ │
│ │ □ Idea 3: Couples matching shoes       ○ pending│ │
│ │ □ Idea 4: Love letter packaging        ○ pending│ │
│ │ ...                                             │ │
│ │                                                 │ │
│ │ [⏸ Pause] [⏹ Stop] [💬 New Direction]          │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Data Model**:
```typescript
interface TodoItem {
  id: string;
  description: string;
  status: 'pending' | 'in_progress' | 'done' | 'error' | 'paused';
  outputs?: GeneratedImage[];  // Images produced by this task
  error?: string;              // Error message if failed
}

interface TodoList {
  id: string;
  title: string;
  items: TodoItem[];
  created_at: string;
  completed_at?: string;
  interrupted_at?: string;
  interrupt_reason?: string;
}
```

#### 1.2 Autonomy Toggle

**Location**: Chat panel header or settings area

**States**:
- **ON (Autonomous)**: Agent executes all tasks without asking for approval
- **OFF (Supervised)**: Agent proposes each action and waits for approval

**Behavior when OFF**:
1. Before generating images, agent shows proposal:
   ```
   🤖 I'm about to generate: "A romantic sunset run scene with
      Naked Running shoes, warm golden tones, couple silhouette"

      [✓ Approve] [✓✓ Accept All Auto] [✎ Modify] [✗ Skip]
   ```
2. User can:
   - **Approve**: Execute this one, ask again for next
   - **Accept All Auto**: Turn on autonomy for rest of session
   - **Modify**: Edit the prompt before execution
   - **Skip**: Skip this task, move to next

**Default**: OFF (supervised) - safer for new users

#### 1.3 Interruption & Context Preservation

**Interrupt Actions**:
- **Pause**: Stop after current task, can resume later
- **Stop**: Halt immediately, mark remaining as cancelled
- **New Direction**: Stop and provide new instructions

**Context Preservation**:
When interrupted, agent stores:
- Current to-do list state
- Completed outputs
- User's original request
- Point of interruption

**Resume Behavior**:
If user says "continue" or "resume", agent can pick up where it left off.

#### 1.4 Progress & Error Handling

**Progress Updates**:
- Update to-do item status immediately when task starts
- Show generating indicator on images in progress
- Display completion time estimates when possible

**Error Handling**:
- If task fails, mark as error with message
- Offer retry option
- Don't block entire list - continue with next tasks
- Summarize errors at end: "8/10 completed, 2 failed"

#### 1.5 Agent Data Management

**Capabilities**:
Agent can propose changes to:
- Style references (create, update, add images)
- Products (create, update, add images)
- Projects (create, update instructions)
- Brand profile sections

**Proposal Flow**:
```
🤖 Based on our conversation, I'd like to save this as a
   style reference called "Valentine Warmth":

   Color grading: Warm golden tones, lifted shadows
   Mood: Romantic, intimate

   [✓ Save] [✎ Edit] [✗ Don't Save]
```

---

### Feature 2: Image Generator Toolbox

#### 2.1 Entry Point

**Location**: Floating action button (FAB) in bottom-right area of main panel

**Visual Design**:
- Subtle but visible (not prominent, not hidden)
- Icon: Magic wand, paintbrush, or lightning bolt
- Tooltip: "Quick Image Generator"
- Does not interfere with chat input

#### 2.2 Toolbox UI

**Opens as**: Modal or slide-out panel

**Layout**:
```
┌─────────────────────────────────────────────────────┐
│  ⚡ Quick Generate                            [✕]   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Brand: Naked Running ✓ loaded                     │
│                                                     │
│  Product:        [Select product...        ▼]      │
│  Style Reference:[Select style ref...      ▼]      │
│  Aspect Ratio:   [1:1] [4:3] [16:9] [9:16]        │
│  Count:          [1] [3] [5] [10]                  │
│                                                     │
│  ┌───────────────────────────────────────────────┐ │
│  │ Describe your image...                        │ │
│  │                                               │ │
│  │                                               │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│              [⚡ Generate Images]                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Fields**:
| Field | Required | Default | Options |
|-------|----------|---------|---------|
| Brand | Auto-loaded | Current brand | Read-only display |
| Product | Optional | None | Dropdown of brand products |
| Style Reference | Optional | None | Dropdown of brand style refs |
| Aspect Ratio | Required | 1:1 | 1:1, 4:3, 16:9, 9:16 |
| Count | Required | 1 | 1, 3, 5, 10 |
| Prompt | Required | Empty | Free text |

#### 2.3 Generation Flow

1. User fills form and clicks "Generate"
2. Modal shows progress: "Generating 1/5..."
3. Images appear as they complete (progressive display)
4. All done → images shown in grid
5. User can:
   - Download individual images
   - Download all as zip
   - Send to chat for further iteration
   - Close and discard
   - Regenerate with same settings

#### 2.4 Output Handling

**Project Integration**:
- If a project is active, images are tagged with project slug
- Images appear in project's asset library

**No Conversation**:
- Generation does not create chat messages
- Results are self-contained in the toolbox modal
- "Send to Chat" option if user wants to iterate via conversation

---

## Technical Implementation

### Backend Changes

#### New Agent Tools

```python
# advisor/tools/todo_tools.py

async def create_todo_list(title: str, items: list[str]) -> TodoList:
    """Create a new to-do list for multi-step task tracking."""

async def update_todo_item(todo_id: str, item_id: str, status: str, outputs: list = None) -> TodoItem:
    """Update status of a to-do item."""

async def get_todo_list(todo_id: str) -> TodoList:
    """Get current state of a to-do list."""
```

#### Chat Service Changes

```python
# studio/services/chat_service.py

class ChatService:
    def chat(
        self,
        message: str,
        autonomy_mode: bool = False,  # NEW
        # ... existing params
    ) -> dict:
        """
        Returns dict with new fields:
        - todo_list: TodoList | None
        - pending_approval: ApprovalRequest | None
        """

    def respond_to_approval(
        self,
        approval_id: str,
        action: Literal['approve', 'approve_all', 'modify', 'skip'],
        modified_prompt: str | None = None,
    ) -> dict:
        """Handle user's response to an approval request."""

    def interrupt_task(
        self,
        action: Literal['pause', 'stop', 'new_direction'],
        new_message: str | None = None,
    ) -> dict:
        """Interrupt current task execution."""
```

#### Bridge Updates

```python
# studio/bridge.py - New methods

def set_autonomy_mode(self, enabled: bool) -> dict:
    """Toggle autonomy mode."""

def respond_to_approval(self, approval_id: str, action: str, modified_prompt: str = None) -> dict:
    """Respond to agent's approval request."""

def interrupt_task(self, action: str, new_message: str = None) -> dict:
    """Interrupt current task."""

def quick_generate(
    self,
    prompt: str,
    product_slug: str = None,
    style_reference_slug: str = None,
    aspect_ratio: str = "1:1",
    count: int = 1,
) -> dict:
    """Quick image generation without chat."""
```

### Frontend Changes

#### New Components

```
src/components/
├── ChatPanel/
│   ├── TodoList/
│   │   ├── index.tsx          # To-do list container
│   │   ├── TodoItem.tsx       # Individual item with status
│   │   └── TodoControls.tsx   # Pause/Stop/New Direction buttons
│   ├── ApprovalPrompt/
│   │   └── index.tsx          # Approval UI with buttons
│   └── AutonomyToggle/
│       └── index.tsx          # Toggle switch in header
├── QuickGenerator/
│   ├── index.tsx              # Main toolbox modal
│   ├── QuickGeneratorFAB.tsx  # Floating action button
│   ├── GeneratorForm.tsx      # Form with selectors
│   └── ResultsGrid.tsx        # Generated images display
```

#### New Context

```typescript
// context/GenerationContext.tsx

interface GenerationState {
  autonomyMode: boolean;
  activeTodoList: TodoList | null;
  pendingApproval: ApprovalRequest | null;
  isInterrupted: boolean;
}

interface GenerationActions {
  setAutonomyMode: (enabled: boolean) => void;
  respondToApproval: (id: string, action: string, modified?: string) => Promise<void>;
  interruptTask: (action: string, newMessage?: string) => Promise<void>;
}
```

### State Management

#### To-Do List State Flow

```
User sends complex request
    ↓
Agent creates TodoList (via tool)
    ↓
Backend emits todo_list in response
    ↓
Frontend renders TodoList component
    ↓
Agent starts executing items
    ↓
Each completion → update_todo_item → emit progress
    ↓
Frontend updates item status in real-time
    ↓
User can interrupt at any point
    ↓
On interrupt → store context → await user action
```

#### Progress Polling

Current implementation polls for progress. Extend to include:
- To-do list updates
- Approval requests
- Interruption status

---

## UI/UX Guidelines

### Visual Hierarchy
1. Chat Agent = Primary entry point (prominent)
2. Image Generator = Secondary tool (visible but not competing)

### Progress Feedback
- Never leave user waiting without feedback
- Update at least every 5 seconds during generation
- Show what's happening, not just "loading..."

### Error States
- Be honest about failures
- Provide actionable next steps
- Don't block entire workflow for single failure

### Interruption UX
- Confirm destructive actions (Stop)
- Make Pause/Resume obvious
- Preserve user's work/context

---

## Acceptance Criteria

### Chat Agent - To-Do List
- [ ] Agent can break complex requests into to-do items
- [ ] To-do list renders inline in chat
- [ ] Items show real-time status updates
- [ ] Generated images appear under their respective items
- [ ] User can see progress without scrolling away

### Chat Agent - Autonomy
- [ ] Toggle is visible and accessible
- [ ] OFF mode shows approval prompt before each generation
- [ ] "Accept All Auto" turns on autonomy for session
- [ ] ON mode executes without prompts

### Chat Agent - Interruption
- [ ] Pause button stops after current task
- [ ] Stop button halts immediately
- [ ] New Direction accepts user input
- [ ] Agent can resume from pause state

### Image Generator Toolbox
- [ ] FAB is visible but not prominent
- [ ] Modal opens with all required fields
- [ ] Brand is auto-loaded and displayed
- [ ] Product/Style ref dropdowns populate correctly
- [ ] Count selector works (1, 3, 5, 10)
- [ ] Generation shows progress
- [ ] Results display in grid
- [ ] Download individual/all works
- [ ] Close discards results (with confirmation if unsaved)

### Agent Data Management
- [ ] Agent can propose style reference creation
- [ ] Agent can propose product updates
- [ ] User can approve/edit/reject proposals
- [ ] Approved changes persist correctly

---

## Open Questions

1. **Concurrent generation**: Should toolbox generation work while chat agent is running? Or mutex?

2. **Toolbox history**: Should toolbox remember last-used settings? Last prompt?

3. **To-do persistence**: If user refreshes page mid-task, can we restore? (Probably Phase 2)

4. **Autonomy scope**: Per-session or persistent preference?

---

## Dependencies

- Existing BrandAdvisor agent infrastructure
- Current image generation pipeline (Gemini)
- PyWebView bridge communication
- React frontend architecture

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Long-running tasks timeout | High | Implement chunked execution with checkpoints |
| Progress updates lag | Medium | Optimize polling or implement SSE |
| User confusion between modes | Medium | Clear visual differentiation, onboarding |
| Interruption loses context | High | Robust state serialization before interrupt |

---

## Success Metrics

- **Task completion rate**: % of to-do lists fully completed
- **Interruption rate**: How often users interrupt (too high = UX issue)
- **Toolbox adoption**: % of generations via toolbox vs chat
- **Time to first image**: Faster with toolbox for clear ideas
- **User satisfaction**: Qualitative feedback on "feeling in control"

---

## Appendix: Current Codebase Reference

### Relevant Files
- `src/sip_studio/studio/services/chat_service.py` - Chat orchestration
- `src/sip_studio/advisor/agent.py` - BrandAdvisor agent
- `src/sip_studio/advisor/tools/` - Agent tools
- `src/sip_studio/studio/frontend/src/components/ChatPanel/` - Chat UI
- `src/sip_studio/studio/bridge.py` - Python-JS bridge

### Existing Tools to Leverage
- `generate_image()` - Core image generation
- `propose_choices()` - User interaction
- `update_memory()` - Preference storage
- `report_thinking()` - Progress emission
