import { useState, useEffect } from 'react'
import { FolderKanban } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Spinner } from '@/components/ui/spinner'
import { Input } from '@/components/ui/input'
import { useProjects } from '@/context/ProjectContext'
import type { ProjectFull } from '@/lib/bridge'

interface EditProjectDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  projectSlug: string
}

export function EditProjectDialog({
  open,
  onOpenChange,
  projectSlug,
}: EditProjectDialogProps) {
  const { getProject, updateProject, refresh } = useProjects()
  const [name, setName] = useState('')
  const [instructions, setInstructions] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [originalProject, setOriginalProject] = useState<ProjectFull | null>(null)

  // Load project data when dialog opens
  useEffect(() => {
    if (!open || !projectSlug) return

    let cancelled = false

    async function load() {
      setIsLoading(true)
      setError(null)
      try {
        const project = await getProject(projectSlug)
        if (!cancelled) {
          setOriginalProject(project)
          setName(project.name)
          setInstructions(project.instructions || '')
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load project')
        }
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [open, projectSlug, getProject])

  const handleSave = async () => {
    setError(null)

    if (!name.trim()) {
      setError('Please enter a project name.')
      return
    }

    setIsSaving(true)

    try {
      await updateProject(
        projectSlug,
        name.trim(),
        instructions.trim() || undefined,
        undefined // Keep existing status
      )
      await refresh()
      onOpenChange(false)
    } catch (err) {
      console.error('[EditProject] ERROR:', err)
      setError(err instanceof Error ? err.message : 'Failed to update project')
    } finally {
      setIsSaving(false)
    }
  }

  const handleClose = () => {
    if (!isSaving) {
      onOpenChange(false)
      setError(null)
    }
  }

  const hasChanges = originalProject && (
    name.trim() !== originalProject.name ||
    (instructions.trim() || '') !== (originalProject.instructions || '')
  )

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FolderKanban className="h-5 w-5 text-green-600" />
            Edit Project
          </DialogTitle>
          <DialogDescription>
            Update project name and campaign instructions.
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="py-8 flex flex-col items-center gap-3">
            <Spinner className="h-6 w-6 text-green-600" />
            <p className="text-sm text-muted-foreground">Loading project...</p>
          </div>
        ) : isSaving ? (
          <div className="py-8 flex flex-col items-center gap-3">
            <Spinner className="h-6 w-6 text-green-600" />
            <p className="text-sm text-muted-foreground">Saving changes...</p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Name Input */}
            <div className="space-y-2">
              <label htmlFor="edit-project-name" className="text-sm font-medium">
                Name <span className="text-red-500">*</span>
              </label>
              <Input
                id="edit-project-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Christmas Campaign"
                autoFocus
              />
            </div>

            {/* Instructions Input */}
            <div className="space-y-2">
              <label htmlFor="edit-project-instructions" className="text-sm font-medium">
                Campaign Instructions
              </label>
              <textarea
                id="edit-project-instructions"
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="Instructions for the AI when generating content for this campaign..."
                rows={5}
                className="w-full px-3 py-2 text-sm border rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-green-500 resize-none"
              />
              <p className="text-xs text-muted-foreground">
                These instructions will guide the AI when creating images for this project.
              </p>
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
          </div>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={isSaving}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={isLoading || isSaving || !name.trim() || !hasChanges}
            className="bg-green-600 hover:bg-green-700"
          >
            {isSaving ? 'Saving...' : 'Save Changes'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
