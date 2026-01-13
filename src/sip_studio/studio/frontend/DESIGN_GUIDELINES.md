# Brand Studio Design Guidelines

This document defines the visual language for Brand Studio. All UI must follow these guidelines.

## Color Palette (3 Colors Only)

### Brand Red
Primary brand color. Use for actions, selections, and emphasis.

| Token | Value | Usage |
|-------|-------|-------|
| `brand-500` | `#ED0942` | Primary buttons, active tabs, focus rings |
| `brand-600` | `#D4073B` | Hover states |
| `brand-700` | `#B20632` | Active/pressed states |
| `brand-a10` | `rgba(237,9,66,0.1)` | Selected backgrounds, hover tints |
| `brand-a20` | `rgba(237,9,66,0.2)` | Stronger selection backgrounds |
| `brand-a30` | `rgba(237,9,66,0.3)` | Focus rings, glows |

### Neutral Gray
For text, backgrounds, borders, and secondary UI.

| Token | Value | Light Mode | Dark Mode |
|-------|-------|------------|-----------|
| `neutral-0` | `#FFFFFF` | Surface | - |
| `neutral-50` | `#FAFAFA` | Background | - |
| `neutral-100` | `#F5F5F5` | Secondary bg, hover | - |
| `neutral-200` | `#E5E5E5` | Borders | - |
| `neutral-300` | `#D4D4D4` | Disabled borders | - |
| `neutral-400` | `#A3A3A3` | Placeholder text | Muted text |
| `neutral-500` | `#737373` | Muted text | - |
| `neutral-600` | `#525252` | Secondary text | - |
| `neutral-700` | `#404040` | - | Hover bg |
| `neutral-800` | `#262626` | - | Borders, secondary bg |
| `neutral-900` | `#171717` | Text | Surface |
| `neutral-950` | `#0A0A0A` | - | Background |

### Success Green
Only for positive confirmations. Never use for decorative purposes.

| Token | Value | Usage |
|-------|-------|-------|
| `success` | `#22C55E` | Success icons, completed states |
| `success-a10` | `rgba(34,197,94,0.1)` | Success alert backgrounds |

## Color Usage Rules

### DO
- Use `brand-500` for primary buttons
- Use `brand-a10` for selected/active item backgrounds
- Use `brand-500` for error text (red = error is intuitive)
- Use `neutral-100/800` for secondary buttons (light/dark)
- Use `success` only for success confirmations
- Use grayscale for everything else

### DON'T
- Add new colors without approval
- Use blue, yellow, orange, or purple
- Use success green for non-success purposes
- Mix multiple accent colors

## Typography

| Style | Size | Weight | Usage |
|-------|------|--------|-------|
| Display | 2.5rem (40px) | 700 | Hero sections |
| H1 | 1.5rem (24px) | 600 | Page titles |
| H2 | 1.25rem (20px) | 600 | Section headers |
| H3 | 1rem (16px) | 600 | Subsections |
| Body | 0.875rem (14px) | 400 | Default text |
| Small | 0.8125rem (13px) | 400 | Secondary text, labels |
| Caption | 0.75rem (12px) | 400 | Helper text, timestamps |
| Mono | 0.8125rem (13px) | 400 | Code, technical values |

## Spacing

Use Tailwind spacing scale consistently:
- `gap-1` (4px): Tight spacing (icon + text)
- `gap-2` (8px): Related items
- `gap-3` (12px): Default component padding
- `gap-4` (16px): Section spacing
- `gap-6` (24px): Major sections

## Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `rounded-sm` | 0.375rem (6px) | Small elements, badges |
| `rounded-md` | 0.5rem (8px) | Buttons, inputs, cards |
| `rounded-lg` | 0.75rem (12px) | Larger cards, modals |
| `rounded-xl` | 1rem (16px) | Feature cards |
| `rounded-full` | 9999px | Pills, avatars |

## Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `shadow-sm` | `0 1px 2px rgb(0 0 0/0.05)` | Subtle elevation |
| `shadow-md` | `0 4px 6px -1px rgb(0 0 0/0.1)` | Cards, dropdowns |
| `shadow-lg` | `0 10px 15px -3px rgb(0 0 0/0.1)` | Modals, popovers |
| `shadow-glow` | `0 0 20px rgba(237,9,66,0.3)` | Brand hover effect |

## Button Variants

```tsx
// Primary - Main actions
<Button variant="default">Create Brand</Button>
// Uses: bg-brand-500, hover:bg-brand-600, text-white

// Secondary - Alternative actions
<Button variant="secondary">Cancel</Button>
// Uses: bg-neutral-100 (light) / bg-neutral-800 (dark)

// Outline - Subtle emphasis
<Button variant="outline">Learn More</Button>
// Uses: border-neutral-200, hover:border-brand-500

// Ghost - Minimal presence
<Button variant="ghost">View All</Button>
// Uses: transparent, hover:bg-neutral-100

// Destructive - Dangerous actions
<Button variant="destructive">Delete</Button>
// Uses: bg-brand-500 (same as primary, red = danger)
```

## Input States

```css
/* Default */
border-color: neutral-200 (light) / neutral-700 (dark)

/* Focus */
border-color: brand-500
box-shadow: 0 0 0 3px brand-a10

/* Error */
border-color: brand-500

/* Disabled */
opacity: 0.5
cursor: not-allowed
```

## Component Patterns

### Selected/Active States
```css
background: brand-a10
color: brand-600 (light) / brand-500 (dark)
```

### Hover States
```css
/* Light backgrounds */
background: neutral-100

/* Dark backgrounds */
background: neutral-800

/* Brand elements */
background: brand-600
box-shadow: shadow-glow
```

### Alerts/Notifications

| Type | Background | Text/Icon |
|------|------------|-----------|
| Info/Neutral | `neutral-100/800` | `neutral-900/100` |
| Warning/Error | `brand-a10` | `brand-700/500` |
| Success | `success-a10` | `success` |

### Badges

| Type | Background | Text |
|------|------------|------|
| Default | `neutral-100/800` | `neutral-500/400` |
| Brand | `brand-a10` | `brand-600/500` |
| Success | `success-a10` | `success` |

## AI Feature Styling

AI-powered features use a special holographic gradient to distinguish them:

```css
/* Light mode */
background: linear-gradient(135deg, #e0f2fe, #ddd6fe, #fce7f3);

/* Dark mode */
background: linear-gradient(135deg, #1e3a5f, #312e81, #4a1d3d);
```

Only use this for AI features (Quick Edit, AI Generate, etc.).

## Glassmorphism (Selective Use)

Use glass effects only for:
- Floating toolbars
- Overlays and popovers
- Sidebar (optional)

```css
background: rgba(255,255,255,0.8); /* light */
background: rgba(23,23,23,0.8); /* dark */
backdrop-filter: blur(12px);
-webkit-backdrop-filter: blur(12px);
border: 1px solid rgba(255,255,255,0.3);
```

Do NOT use glass for:
- Main content areas
- Cards within content
- Form elements

## Dark Mode

- Uses `prefers-color-scheme` media query by default
- Manual toggle available
- All components must support both modes
- Test both modes before shipping

## Accessibility

- Maintain 4.5:1 contrast ratio for text
- All interactive elements need focus rings
- Use semantic HTML
- Include ARIA labels where needed
- Disabled states must be visually distinct

## Floating Command Center Aesthetics (New)

The application moves towards a "Floating Command Center" aesthetic for primary inputs.

### Core Principles
- **Floating Island**: Inputs are distinct, floating elements rather than flat forms.
- **Glass & Blur**: High usage of `backdrop-blur-md` and semi-transparent backgrounds (`bg-background/80`).
- **Soft Shadows**: Use multi-layered shadows to create depth.
- **Rounded Corners**: Use `rounded-3xl` for main input containers.

### Input Styling
```css
/* Floating Input Container */
border-radius: 1.5rem (24px) / 2rem (32px);
background: bg-background/80;
backdrop-filter: blur(12px);
border: 1px solid rgba(255,255,255,0.2); /* Light/Glass border */
box-shadow:
  0 10px 15px -3px rgba(0, 0, 0, 0.1),
  0 4px 6px -2px rgba(0, 0, 0, 0.05);
```

### Iconography
- **Stroke Width**: STRICTLY `strokeWidth={1.5}` for all general UI icons.
- **Micro-interactions**: Subtle scale (`active:scale-95`) and glow effects on primary actions.

---

## Unified Component Patterns

These patterns ensure visual consistency across the entire application. **All implementations must follow these rules.**

### Primary Action Buttons

**Rule**: All primary action buttons use `bg-primary` (brand color). Never use `bg-success`, `bg-black`, or custom colors.

```tsx
// ✅ CORRECT - All dialogs
<Button variant="default">Create Project</Button>
<Button variant="default">Save Brand</Button>
<Button variant="default">Add Product</Button>
// ✅ CORRECT - Destructive actions
<Button variant="destructive">Delete</Button>
// ❌ WRONG - Don't use these for primary actions
<button className="bg-success">Create</button>
<button className="bg-black dark:bg-white">Save</button>
<button className="bg-brand-500">Custom</button>
```

### Focus Rings

**Rule**: All focusable elements use `focus:ring-ring` (theme token). Never use color-specific rings.

```tsx
// ✅ CORRECT
<Input className="focus:ring-ring" />
<Textarea className="focus:ring-ring focus:ring-2 focus:ring-offset-2" />
// ❌ WRONG
<textarea className="focus:ring-success" />
<input className="focus:ring-brand-500" />
<input className="focus:ring-black/5" />
```

### Selection Indicators (Checkmarks)

**Rule**: Checkmarks in dropdowns/selectors always use `text-primary`. Never use `text-success` or `text-foreground`.

```tsx
// ✅ CORRECT
<Check className="h-4 w-4 text-primary" />
// ❌ WRONG
<Check className="text-success" />
<Check className="text-foreground" />
```

### Toggle / Segmented Controls

**Rule**: All toggles use `rounded-full` (pill shape) for the container. Active state uses `bg-background shadow-sm`.

```tsx
// ✅ CORRECT
<div className="rounded-full bg-muted p-1">
  <button className={cn("rounded-full px-3 py-1",isActive && "bg-background shadow-sm")}>Option</button>
</div>
// ❌ WRONG
<div className="rounded-lg ...">
  <button className="rounded-md ...">Option</button>
</div>
```

### Dialogs and Confirmations

**Rule**: Use `<FormDialog>` for form modals. Use `<ConfirmDialog>` for destructive confirmations. **Never use native `window.confirm()`**.

```tsx
// ✅ CORRECT - Form modal
<FormDialog title="Create Project" onSubmit={handleSubmit}>
  <Input name="name" />
</FormDialog>
// ✅ CORRECT - Destructive confirmation
<ConfirmDialog
  title="Delete Product?"
  description="This cannot be undone."
  confirmText="Delete"
  variant="destructive"
  onConfirm={handleDelete}
/>
// ❌ WRONG - Never use native confirm
if (window.confirm("Are you sure?")) { handleDelete(); }
```

### Loading States

**Rule**: Always use `<Spinner>` component. Never use inline loaders or different icons.

```tsx
// ✅ CORRECT
import {Spinner} from "@/components/ui/spinner"
<Spinner className="h-4 w-4" />
<Spinner className="h-6 w-6" />
// ❌ WRONG
<Loader2 className="animate-spin" />
<Building2 className="animate-pulse" />
<div className="animate-spin rounded-full border-2..." />
```

### Section Headers

**Rule**: All section headers use consistent typography: `text-[11px] font-semibold uppercase tracking-wider text-muted-foreground`.

```tsx
// ✅ CORRECT
<h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
  Projects
</h3>
// ❌ WRONG
<h3 className="text-xs font-medium uppercase tracking-wider">...</h3>
<h3 className="text-sm font-medium">...</h3>
```

### Empty States

**Rule**: All empty states must include action guidance. Never just say "No X yet."

```tsx
// ✅ CORRECT
<p className="text-muted-foreground">No products yet. Click + to add one.</p>
// ❌ WRONG
<p>No projects yet</p>
```

### Icon Stroke Width

**Rule**: Use `strokeWidth={1.5}` for all Lucide icons to match minimal design aesthetic.

```tsx
// ✅ CORRECT
<Plus strokeWidth={1.5} className="h-4 w-4" />
<Settings strokeWidth={1.5} className="h-4 w-4" />
// ❌ WRONG (default strokeWidth=2 is too thick)
<Plus className="h-4 w-4" />
```

### Button Sizes

**Rule**: Standardize icon buttons to three sizes: `sm` (32px), `md` (40px), `lg` (48px).

```tsx
// Icon buttons
<button className="h-8 w-8">...</button>   // sm - toolbars, inline actions
<button className="h-10 w-10">...</button> // md - default
<button className="h-12 w-12">...</button> // lg - prominent actions
```

### Form Field Labels

**Rule**: Always use `htmlFor` with matching `id`. Use `*` for required, `(optional)` for optional.

```tsx
// ✅ CORRECT
<label htmlFor="name" className="text-sm font-medium">
  Name <span className="text-destructive">*</span>
</label>
<Input id="name" required />
<label htmlFor="notes">Notes <span className="text-muted-foreground">(optional)</span></label>
<Textarea id="notes" />
// ❌ WRONG
<label>Name</label>
<Input />
```

---

## Component Reference

### UI Primitives (`components/ui/`)

These are the foundational building blocks. **Always use these instead of custom implementations.**

| Component | File | When to Use |
|-----------|------|-------------|
| `Button` | `button.tsx` | All clickable actions. Variants: default, secondary, outline, ghost, destructive |
| `Dialog` | `dialog.tsx` | Base dialog primitives. Usually use `FormDialog` instead. |
| `FormDialog` | `form-dialog.tsx` | Any modal with form content (create, edit, settings) |
| `Input` | `input.tsx` | Single-line text input |
| `Textarea` | `textarea.tsx` | Multi-line text input |
| `Spinner` | `spinner.tsx` | Loading indicators. Two variants available. |
| `DropdownMenu` | `dropdown-menu.tsx` | Context menus, action menus |
| `Popover` | `popover.tsx` | Floating content triggered by click |
| `Tabs` | `tabs.tsx` | Tab navigation within a panel |
| `Alert` | `alert.tsx` | Inline alert messages |
| `Tooltip` | `tooltip.tsx` | Hover hints for icons/actions |
| `ScrollArea` | `scroll-area.tsx` | Custom scrollbars for overflow content |
| `Label` | `label.tsx` | Form field labels |
| `Separator` | `separator.tsx` | Visual dividers |
| `Switch` | `switch.tsx` | On/off toggles |
| `Checkbox` | `checkbox.tsx` | Multi-select options |
| `Select` | `select.tsx` | Single-select dropdown |

### Feature Components

These implement specific UI patterns for the application.

| Component | Location | Purpose |
|-----------|----------|---------|
| `BrandSelector` | `Sidebar/BrandSelector.tsx` | Brand selection dropdown with create option |
| `ProjectSelector` | `Sidebar/ProjectSelector.tsx` | Project selection dropdown |
| `ProductsSection` | `Sidebar/ProductsSection.tsx` | Product list with add/delete |
| `PanelModeToggle` | `ChatPanel/PanelModeToggle.tsx` | Creative Director / Quick Create toggle |
| `GenerationSettings` | `ChatPanel/GenerationSettings.tsx` | Aspect ratio and style settings |
| `AttachmentChips` | `ChatPanel/AttachmentChips.tsx` | File/reference chips in message input |
| `EmptyState` | `Workstation/EmptyState.tsx` | Branded empty state with illustration |
| `CreateBrandDialog` | `dialogs/CreateBrandDialog.tsx` | Multi-step brand creation wizard |
| `CreateProjectDialog` | `dialogs/CreateProjectDialog.tsx` | Project creation form |
| `CreateProductDialog` | `dialogs/CreateProductDialog.tsx` | Product creation form |
| `DeleteBrandDialog` | `dialogs/DeleteBrandDialog.tsx` | Brand deletion confirmation |
| `SettingsDialog` | `Settings/SettingsDialog.tsx` | App settings modal |

### Pattern: Creating New Dialogs

```tsx
import {FormDialog} from "@/components/ui/form-dialog"
import {Button} from "@/components/ui/button"
import {Input} from "@/components/ui/input"
export function MyDialog({open,onOpenChange,onSubmit}:{open:boolean,onOpenChange:(open:boolean)=>void,onSubmit:(data:FormData)=>void}) {
  return (
    <FormDialog open={open} onOpenChange={onOpenChange} title="Create Thing">
      <form onSubmit={onSubmit}>
        <div className="space-y-4">
          <div>
            <label htmlFor="name" className="text-sm font-medium">Name <span className="text-destructive">*</span></label>
            <Input id="name" name="name" required className="mt-1" />
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={()=>onOpenChange(false)}>Cancel</Button>
          <Button type="submit">Create</Button>
        </div>
      </form>
    </FormDialog>
  )
}
```

### Pattern: Creating Toggle Controls

```tsx
export function MyToggle({value,onChange}:{value:string,onChange:(v:string)=>void}) {
  return (
    <div className="inline-flex rounded-full bg-muted p-1">
      {["option1","option2"].map((opt)=>(
        <button key={opt} onClick={()=>onChange(opt)}
          className={cn("rounded-full px-3 py-1 text-sm transition-all",
            value===opt?"bg-background shadow-sm font-medium":"text-muted-foreground hover:text-foreground"
          )}>
          {opt}
        </button>
      ))}
    </div>
  )
}
```

### Pattern: ConfirmDialog Usage

Until the `ConfirmDialog` component is created, use this pattern with `FormDialog`:

```tsx
<FormDialog open={showConfirm} onOpenChange={setShowConfirm} title="Delete Product?">
  <p className="text-sm text-muted-foreground">This action cannot be undone.</p>
  <div className="mt-6 flex justify-end gap-2">
    <Button variant="ghost" onClick={()=>setShowConfirm(false)}>Cancel</Button>
    <Button variant="destructive" onClick={handleDelete}>Delete</Button>
  </div>
</FormDialog>
```

---

## Checklist for New Components

- [ ] Uses only brand, neutral, and success colors
- [ ] Follows typography scale
- [ ] Has proper hover/focus/active states
- [ ] Supports light and dark modes
- [ ] Uses consistent border radius
- [ ] Has appropriate spacing
- [ ] Accessible (contrast, focus, ARIA)

## Unified Pattern Checklist

- [ ] Primary buttons use `variant="default"` (not custom bg colors)
- [ ] Focus rings use `focus:ring-ring` (not color-specific)
- [ ] Checkmarks use `text-primary` (not success/foreground)
- [ ] Toggles use `rounded-full` pill shape
- [ ] Dialogs use `FormDialog` (not raw Dialog)
- [ ] No native `window.confirm()` usage
- [ ] Loading states use `<Spinner>` component
- [ ] Section headers use 11px/semibold/uppercase/tracking-wider
- [ ] Empty states include action guidance
- [ ] Icons use `strokeWidth={1.5}`
- [ ] Labels have `htmlFor` with matching `id`
