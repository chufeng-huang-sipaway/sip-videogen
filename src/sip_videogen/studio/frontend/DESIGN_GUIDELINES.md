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

## Checklist for New Components

- [ ] Uses only brand, neutral, and success colors
- [ ] Follows typography scale
- [ ] Has proper hover/focus/active states
- [ ] Supports light and dark modes
- [ ] Uses consistent border radius
- [ ] Has appropriate spacing
- [ ] Accessible (contrast, focus, ARIA)
