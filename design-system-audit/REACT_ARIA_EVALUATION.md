# React Aria Evaluation for Sip Studio

**Date:** 2026-01-14
**Status:** Evaluation Complete
**Recommendation:** Stay with Radix UI unless it becomes unmaintained

---

## Executive Summary

React Aria (Adobe) provides excellent accessibility primitives but would require significant migration effort for Sip Studio due to:
1. Missing components (Avatar, ScrollArea)
2. Context Menu discouraged for accessibility reasons
3. Different composition pattern (slot-based vs asChild)

**Migration effort estimate:** ~3-4 weeks for full migration with custom component development.

---

## Current Radix UI Inventory

### Components Used (15 total)

| Component | File | Key Features Used |
|-----------|------|-------------------|
| Dialog | ui/dialog.tsx | Root, Trigger, Portal, Close, Overlay, Content, Title, Description |
| AlertDialog | ui/alert-dialog.tsx | Root, Trigger, Portal, Overlay, Content, Title, Description, Action, Cancel |
| Select | ui/select.tsx | Root, Group, Value, Trigger, Icon, Content, Portal, Viewport, ScrollUpButton, ScrollDownButton, Label, Item, ItemIndicator, ItemText, Separator |
| DropdownMenu | ui/dropdown-menu.tsx | Root, Trigger, Content, Portal, Item, CheckboxItem, RadioItem, RadioGroup, Label, Separator, Group, Sub, SubTrigger, SubContent, ItemIndicator |
| Accordion | ui/accordion.tsx | Root, Item, Header, Trigger, Content |
| Tabs | ui/tabs.tsx | Root, List, Trigger, Content |
| Tooltip | ui/tooltip.tsx | Provider, Root, Trigger, Content, Portal |
| Avatar | ui/avatar.tsx | Root, Image, Fallback |
| Separator | ui/separator.tsx | Root |
| ScrollArea | ui/scroll-area.tsx | Root, Viewport, Scrollbar, Thumb, Corner |
| ContextMenu | ui/context-menu.tsx | Root, Trigger, Content, Portal, Item, CheckboxItem, RadioItem, RadioGroup, Label, Separator, Group, Sub, SubTrigger, SubContent, ItemIndicator |
| Switch | ui/switch.tsx | Root, Thumb |
| Slider | ui/slider.tsx | Root, Track, Range, Thumb |
| Slot | ui/button.tsx | asChild polymorphic composition |
| Popover | ChatPanel/QuickInsertPopover.tsx | Root, Trigger, Portal, Content |

---

## React Aria Equivalents

### Full Parity (10 components) 🟢

| Radix | React Aria | Notes |
|-------|-----------|-------|
| Dialog | Dialog + Modal | Requires explicit Modal wrapper |
| AlertDialog | AlertDialog | Same name, same behavior |
| Select | Select + ListBox | Uses ListBox for options |
| DropdownMenu | Menu | Different name, same behavior |
| Accordion | DisclosureGroup | Different name (stable Nov 2024) |
| Tabs | Tabs | Same name and API |
| Tooltip | Tooltip + TooltipTrigger | Similar pattern |
| Separator | Separator | Same name |
| Switch | Switch | Same name |
| Slider | Slider | Same name, multi-thumb support |

### Partial Parity (2 components) 🟡

| Radix | React Aria | Gap |
|-------|-----------|-----|
| Slot | slot prop pattern | Different composition model - requires code changes |
| Popover | Popover | Same but different internal structure |

### No Equivalent (3 components) 🔴

| Radix | React Aria Status | Workaround |
|-------|------------------|------------|
| Avatar | Not included | Build custom component |
| ScrollArea | Not included (GitHub #7286) | Use native scroll or custom |
| ContextMenu | Discouraged for a11y | Build custom or drop feature |

---

## API Comparison: Dialog Example

### Current Radix Implementation
```tsx
import * as DialogPrimitive from "@radix-ui/react-dialog"

// Composition
<Dialog>
  <DialogTrigger asChild>
    <Button>Open</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogTitle>Title</DialogTitle>
    <DialogDescription>Description</DialogDescription>
  </DialogContent>
</Dialog>
```

### React Aria Equivalent
```tsx
import {DialogTrigger, Modal, Dialog, Heading, Button} from 'react-aria-components'

// Composition (note: Modal wrapper required, different props)
<DialogTrigger>
  <Button>Open</Button>
  <Modal>
    <Dialog>
      {({close}) => (
        <>
          <Heading slot="title">Title</Heading>
          <p>Description</p>
          <Button onPress={close}>Close</Button>
        </>
      )}
    </Dialog>
  </Modal>
</DialogTrigger>
```

### Key API Differences
1. **Modal wrapper required** - Radix Portal is implicit, React Aria Modal is explicit
2. **Render props for close** - React Aria uses render props, Radix uses DialogClose component
3. **Slot-based titles** - React Aria uses `slot="title"` vs Radix DialogTitle component
4. **No asChild** - React Aria passes props via context, no polymorphic composition

---

## Migration Effort Assessment

### Low Effort (1-2 hours each)
- Dialog → Dialog + Modal
- Tabs → Tabs
- Switch → Switch
- Slider → Slider
- Separator → Separator
- Tooltip → Tooltip
- Accordion → DisclosureGroup

### Medium Effort (4-8 hours each)
- Select → Select + ListBox (different sub-components)
- DropdownMenu → Menu (rename + restructure)
- Popover → Popover (minor API changes)
- Slot pattern → slot prop (refactor composition)

### High Effort (1-2 days each)
- Avatar → Custom component (build from scratch)
- ScrollArea → Custom or native (build or accept limitations)
- ContextMenu → Custom or remove (accessibility concerns)

### Total Estimated Effort
- **Full migration:** 3-4 weeks
- **Hybrid approach:** 1-2 weeks (keep Radix for Avatar, ScrollArea, ContextMenu)

---

## Pros and Cons

### React Aria Advantages
1. **Adobe backing** - More resources, faster updates
2. **Stricter accessibility** - Won't implement anti-patterns
3. **Better TypeScript** - More precise types
4. **Date/Time/Color pickers** - Comprehensive form controls
5. **Drag-and-drop** - Built into ListBox, GridList

### Radix UI Advantages
1. **Complete component set** - Avatar, ScrollArea included
2. **ContextMenu supported** - Important for desktop apps
3. **asChild pattern** - More flexible composition
4. **Simpler mental model** - Less wrapper nesting
5. **Shadcn ecosystem** - Pre-built styled components
6. **Smaller bundle** - Less code to ship

---

## Maintenance Assessment

### Radix UI (WorkOS)
- Last commit: Recent (actively maintained)
- Issues resolved: Timely
- Breaking changes: Infrequent
- Community: Large shadcn ecosystem

### React Aria (Adobe)
- Last commit: Very recent (actively maintained)
- Issues resolved: Very timely
- Breaking changes: Stable with versioning
- Community: Adobe Spectrum users

**Both are actively maintained.** No immediate concern for either library.

---

## Recommendation

### Decision: **Stay with Radix UI**

**Rationale:**
1. **Desktop app needs ContextMenu** - Radix supports it, React Aria discourages it
2. **Avatar is heavily used** - Would need custom implementation
3. **ScrollArea used throughout** - Custom scrollbars important for macOS native feel
4. **No accessibility gaps** - Radix meets all WCAG requirements
5. **Migration cost > benefit** - 3-4 weeks effort for marginal improvement
6. **Radix actively maintained** - No abandonment risk currently

### When to Reconsider
- If WorkOS deprioritizes Radix development
- If major accessibility issues discovered in Radix
- If React Aria adds Avatar and ScrollArea
- If app removes ContextMenu functionality

### Migration Triggers
1. Radix goes 12+ months without security updates
2. React Aria reaches feature parity with Radix
3. Significant accessibility issues in Radix not addressed
4. WorkOS announces Radix deprecation

---

## Appendix: Component-by-Component Migration Notes

### Dialog → React Aria Dialog
```tsx
// BEFORE (Radix)
<Dialog open={open} onOpenChange={setOpen}>
  <DialogTrigger asChild><Button>Open</Button></DialogTrigger>
  <DialogContent>
    <DialogTitle>Settings</DialogTitle>
    <DialogDescription>Configure app settings</DialogDescription>
    <DialogClose asChild><Button>Close</Button></DialogClose>
  </DialogContent>
</Dialog>

// AFTER (React Aria) - more verbose
<DialogTrigger isOpen={open} onOpenChange={setOpen}>
  <Button>Open</Button>
  <Modal isDismissable>
    <Dialog>
      {({close}) => (
        <>
          <Heading slot="title">Settings</Heading>
          <Text slot="description">Configure app settings</Text>
          <Button onPress={close}>Close</Button>
        </>
      )}
    </Dialog>
  </Modal>
</DialogTrigger>
```

### Select → React Aria Select
```tsx
// BEFORE (Radix)
<Select value={value} onValueChange={setValue}>
  <SelectTrigger><SelectValue placeholder="Select..." /></SelectTrigger>
  <SelectContent>
    <SelectItem value="a">Option A</SelectItem>
    <SelectItem value="b">Option B</SelectItem>
  </SelectContent>
</Select>

// AFTER (React Aria) - requires ListBox
<Select selectedKey={value} onSelectionChange={setValue}>
  <Label>Options</Label>
  <Button><SelectValue /></Button>
  <Popover>
    <ListBox>
      <ListBoxItem id="a">Option A</ListBoxItem>
      <ListBoxItem id="b">Option B</ListBoxItem>
    </ListBox>
  </Popover>
</Select>
```

### Avatar → Custom Component Required
```tsx
// Radix Avatar (exists)
<Avatar>
  <AvatarImage src={url} />
  <AvatarFallback>JD</AvatarFallback>
</Avatar>

// React Aria (must build custom)
function Avatar({src, fallback}: {src?: string; fallback: string}) {
  const [imgError, setImgError] = useState(false);
  return (
    <div className="avatar">
      {src && !imgError ? (
        <img src={src} onError={() => setImgError(true)} alt="" />
      ) : (
        <span className="fallback">{fallback}</span>
      )}
    </div>
  );
}
```
