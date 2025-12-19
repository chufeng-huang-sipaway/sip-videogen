import { useState } from 'react'
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

interface CreateProjectDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CreateProjectDialog({
  open,
  onOpenChange,
}: CreateProjectDialogProps) {
  const { createProject } = useProjects()
  const [name, setName] = useState('')
  const [instructions, setInstructions] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleCreate = async () => {
    setError(null)

    if (!name.trim()) {
      setError('Please enter a project name.')
      return
    }

    setIsCreating(true)

    try {
      await createProject(name.trim(), instructions.trim() || undefined)
      // Reset form and close
      setName('')
      setInstructions('')
      onOpenChange(false)
    } catch (err) {
      console.error('[CreateProject] ERROR:', err)
      setError(err instanceof Error ? err.message : 'Failed to create project')
    } finally {
      setIsCreating(false)
    }
  }

  const handleClose = () => {
    if (!isCreating) {
      onOpenChange(false)
      setError(null)
      setName('')
      setInstructions('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && name.trim()) {
      e.preventDefault()
      handleCreate()
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FolderKanban className="h-5 w-5 text-green-600" />
            New Project
          </DialogTitle>
          <DialogDescription>
            Create a new campaign project to organize generated assets.
          </DialogDescription>
        </DialogHeader>

        {isCreating ? (
          <div className="py-8 flex flex-col items-center gap-3">
            <Spinner className="h-6 w-6 text-green-600" />
            <p className="text-sm text-muted-foreground">Creating project...</p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Name Input */}
            <div className="space-y-2">
              <label htmlFor="create-project-name" className="text-sm font-medium">
                Name <span className="text-red-500">*</span>
              </label>
              <Input
                id="create-project-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="e.g., Christmas Campaign"
                autoFocus
              />
            </div>

            {/* Instructions Input */}
            <div className="space-y-2">
              <label htmlFor="create-project-instructions" className="text-sm font-medium">
                Campaign Instructions <span className="text-muted-foreground text-xs">(optional)</span>
              </label>
              <textarea
                id="create-project-instructions"
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="Instructions for the AI when generating content for this campaign..."
                rows={4}
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
            disabled={isCreating}
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreate}
            disabled={isCreating || !name.trim()}
            className="bg-green-600 hover:bg-green-700"
          >
            {isCreating ? 'Creating...' : 'Create Project'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
