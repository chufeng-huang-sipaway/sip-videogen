import { useState, type ReactNode } from 'react'
import { Pencil, X } from 'lucide-react'
import { Button } from '@/components/ui/button'

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
  /** Controlled edit mode (optional). If provided, MemorySection will use this state. */
  isEditing?: boolean
}

/**
 * MemorySection - Content wrapper for Brand Memory sections.
 *
 * Features:
 * - Header with title and Edit button
 * - View mode vs Edit mode toggle
 * - Edit mode shows editContent instead of children
 *
 * Used by BrandMemory to wrap each identity section (core, visual, voice, etc.)
 * Navigation between sections is handled by the parent via vertical tabs.
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
  isEditing: isEditingProp,
}: MemorySectionProps) {
  const [internalEditing, setInternalEditing] = useState(false)
  const isEditing = isEditingProp ?? internalEditing

  const setEditing = (next: boolean) => {
    if (isEditingProp === undefined) {
      setInternalEditing(next)
    }
    onEditModeChange?.(next)
  }

  const handleEditClick = () => {
    setEditing(!isEditing)
  }

  const handleCancelEdit = () => {
    setEditing(false)
  }

  return (
    <div className="h-full flex flex-col" data-section-id={id}>
      {/* Section Header */}
      <div className="flex items-center justify-between pb-4 border-b border-border group">
        <div>
          <h3 className="text-base font-semibold">{title}</h3>
          {subtitle && (
            <p className="text-sm text-muted-foreground mt-0.5">{subtitle}</p>
          )}
        </div>

        {/* Edit button - show on hover when not in edit mode */}
        {editable && !isEditing && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleEditClick}
            className="h-8 px-3 text-sm gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity"
            disabled={isSaving}
          >
            <Pencil className="h-3.5 w-3.5" />
            Edit
          </Button>
        )}

        {/* Cancel button - show when in edit mode */}
        {isEditing && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCancelEdit}
            className="h-8 px-3 text-sm gap-1.5 text-muted-foreground hover:text-foreground"
            disabled={isSaving}
          >
            <X className="h-3.5 w-3.5" />
            Cancel
          </Button>
        )}
      </div>

      {/* Section Content */}
      <div className="flex-1 pt-4 overflow-auto">
        {isEditing && editContent ? editContent : children}
      </div>
    </div>
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
