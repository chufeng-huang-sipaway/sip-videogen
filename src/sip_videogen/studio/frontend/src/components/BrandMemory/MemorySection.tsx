import { useState, type ReactNode } from 'react'
import * as AccordionPrimitive from '@radix-ui/react-accordion'
import { ChevronDown, Pencil, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export interface MemorySectionProps {
  /** Unique identifier for this section */
  id: string
  /** Section title displayed in the header */
  title: string
  /** Optional subtitle or description */
  subtitle?: string
  /** Whether the section can be edited */
  editable?: boolean
  /** Content to display in view mode */
  children: ReactNode
  /** Content to display in edit mode (if editable) */
  editContent?: ReactNode
  /** Whether the section is currently saving */
  isSaving?: boolean
  /** Called when the edit mode changes */
  onEditModeChange?: (isEditing: boolean) => void
  /** Whether to start in expanded state */
  defaultExpanded?: boolean
}

/**
 * MemorySection - Reusable expandable section wrapper for Brand Memory.
 *
 * Features:
 * - Collapsible/expandable via accordion
 * - Header with title and Edit button
 * - View mode vs Edit mode toggle
 * - Edit mode shows editContent instead of children
 *
 * Used by BrandMemory to wrap each identity section (core, visual, voice, etc.)
 */
export function MemorySection({
  id,
  title,
  subtitle,
  editable = true,
  children,
  editContent,
  isSaving = false,
  onEditModeChange,
  defaultExpanded = true,
}: MemorySectionProps) {
  const [isEditing, setIsEditing] = useState(false)

  const handleEditClick = (e: React.MouseEvent) => {
    // Prevent accordion toggle when clicking edit button
    e.stopPropagation()
    const newEditState = !isEditing
    setIsEditing(newEditState)
    onEditModeChange?.(newEditState)
  }

  const handleCancelEdit = () => {
    setIsEditing(false)
    onEditModeChange?.(false)
  }

  return (
    <AccordionPrimitive.Root
      type="single"
      collapsible
      defaultValue={defaultExpanded ? id : undefined}
      className="border border-border rounded-lg overflow-hidden"
    >
      <AccordionPrimitive.Item value={id}>
        {/* Section Header */}
        <AccordionPrimitive.Header className="flex">
          <AccordionPrimitive.Trigger
            className={cn(
              'flex flex-1 items-center justify-between px-4 py-3',
              'text-sm font-medium transition-colors',
              'hover:bg-muted/50',
              '[&[data-state=open]>div>.chevron]:rotate-180'
            )}
          >
            <div className="flex items-center gap-2">
              <ChevronDown className="chevron h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200" />
              <div className="text-left">
                <span className="font-medium">{title}</span>
                {subtitle && (
                  <span className="ml-2 text-xs text-muted-foreground">{subtitle}</span>
                )}
              </div>
            </div>

            {/* Edit button - only show when not in edit mode and section is editable */}
            {editable && !isEditing && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleEditClick}
                className="h-7 px-2 text-xs gap-1 opacity-70 hover:opacity-100"
                disabled={isSaving}
              >
                <Pencil className="h-3 w-3" />
                Edit
              </Button>
            )}

            {/* Cancel button - show when in edit mode */}
            {isEditing && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCancelEdit}
                className="h-7 px-2 text-xs gap-1 text-muted-foreground hover:text-foreground"
                disabled={isSaving}
              >
                <X className="h-3 w-3" />
                Cancel
              </Button>
            )}
          </AccordionPrimitive.Trigger>
        </AccordionPrimitive.Header>

        {/* Section Content */}
        <AccordionPrimitive.Content
          className={cn(
            'overflow-hidden text-sm',
            'data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down'
          )}
        >
          <div className="px-4 pb-4 pt-0">
            {isEditing && editContent ? editContent : children}
          </div>
        </AccordionPrimitive.Content>
      </AccordionPrimitive.Item>
    </AccordionPrimitive.Root>
  )
}

/**
 * MemorySectionGroup - Wrapper for multiple MemorySection components.
 *
 * Use this to group multiple sections that can be independently expanded/collapsed.
 */
export function MemorySectionGroup({ children }: { children: ReactNode }) {
  return <div className="space-y-3">{children}</div>
}
