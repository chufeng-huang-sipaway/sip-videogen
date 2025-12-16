import { useState, useEffect } from 'react'
import { FolderKanban, Plus, X, Check, Archive } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from '@/components/ui/context-menu'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useProjects } from '@/context/ProjectContext'
import { useBrand } from '@/context/BrandContext'
import { bridge, waitForPyWebViewReady, type ProjectEntry } from '@/lib/bridge'

interface ProjectCardProps {
  project: ProjectEntry
  isActive: boolean
  onSelect: () => void
  onDeselect: () => void
  onArchive: () => void
  onDelete: () => void
}

function ProjectCard({ project, isActive, onSelect, onDeselect, onArchive, onDelete }: ProjectCardProps) {
  const isArchived = project.status === 'archived'

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>
        <div
          className={`flex items-center gap-2 py-2 px-2 rounded cursor-pointer group transition-colors ${
            isActive
              ? 'bg-green-100/50 dark:bg-green-900/20 ring-1 ring-green-500/30'
              : 'hover:bg-gray-200/50 dark:hover:bg-gray-700/50'
          } ${isArchived ? 'opacity-60' : ''}`}
          onClick={isActive ? onDeselect : onSelect}
          title={isActive ? 'Click to deselect project' : 'Click to set as active project'}
        >
          <FolderKanban
            className={`h-4 w-4 shrink-0 ${
              isActive ? 'text-green-600 dark:text-green-400' : 'text-gray-500'
            }`}
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1">
              <span className="text-sm font-medium truncate">{project.name}</span>
              {isActive && <Check className="h-3 w-3 text-green-600 dark:text-green-400 shrink-0" />}
              {isArchived && <Archive className="h-3 w-3 text-gray-400 shrink-0" />}
            </div>
            <span className="text-xs text-gray-500">
              {project.asset_count} asset{project.asset_count !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
      </ContextMenuTrigger>
      <ContextMenuContent>
        {isActive ? (
          <ContextMenuItem onClick={onDeselect}>
            Clear Active Project
          </ContextMenuItem>
        ) : (
          <ContextMenuItem onClick={onSelect}>
            Set as Active
          </ContextMenuItem>
        )}
        <ContextMenuSeparator />
        {!isArchived && (
          <ContextMenuItem onClick={onArchive}>
            Archive Project
          </ContextMenuItem>
        )}
        <ContextMenuItem onClick={onDelete} className="text-red-600">
          Delete Project
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  )
}

export function ProjectsSection() {
  const { activeBrand } = useBrand()
  const {
    projects,
    activeProject,
    isLoading,
    error,
    refresh,
    setActiveProject,
    updateProject,
    deleteProject,
  } = useProjects()
  const [actionError, setActionError] = useState<string | null>(null)

  useEffect(() => {
    if (actionError) {
      const timer = setTimeout(() => setActionError(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [actionError])

  const handleDelete = async (slug: string) => {
    if (confirm(`Delete project "${slug}"? Generated assets will be kept.`)) {
      try {
        await deleteProject(slug)
      } catch (err) {
        setActionError(err instanceof Error ? err.message : 'Failed to delete project')
      }
    }
  }

  const handleArchive = async (slug: string) => {
    try {
      await updateProject(slug, undefined, undefined, 'archived')
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to archive project')
    }
  }

  const handleCreateProject = async () => {
    const name = prompt('Project name:')
    if (!name) return

    const instructions = prompt('Campaign instructions (optional):') || ''

    try {
      const ready = await waitForPyWebViewReady()
      if (!ready) {
        setActionError('Not running in PyWebView')
        return
      }
      await bridge.createProject(name, instructions)
      await refresh()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to create project')
    }
  }

  const handleSelect = async (slug: string) => {
    try {
      await setActiveProject(slug)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to set active project')
    }
  }

  const handleDeselect = async () => {
    try {
      await setActiveProject(null)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to clear active project')
    }
  }

  if (!activeBrand) {
    return <div className="text-sm text-gray-500">Select a brand</div>
  }

  if (error) {
    return (
      <div className="text-sm text-red-500">
        Error: {error}
        <Button variant="ghost" size="sm" onClick={refresh}>
          Retry
        </Button>
      </div>
    )
  }

  // Sort projects: active projects first, then by name
  const sortedProjects = [...projects].sort((a, b) => {
    if (a.status !== b.status) {
      return a.status === 'active' ? -1 : 1
    }
    return a.name.localeCompare(b.name)
  })

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500">
          {projects.length} project{projects.length !== 1 ? 's' : ''}
          {activeProject && ' (1 active)'}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0"
          onClick={handleCreateProject}
          title="Add project"
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {actionError && (
        <Alert variant="destructive" className="py-2 px-3">
          <AlertDescription className="flex items-center justify-between text-xs">
            <span>{actionError}</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-4 w-4 shrink-0"
              onClick={() => setActionError(null)}
            >
              <X className="h-3 w-3" />
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {sortedProjects.length === 0 ? (
        <p className="text-sm text-gray-400 italic">
          {isLoading ? 'Loading...' : 'No projects yet. Click + to create a campaign.'}
        </p>
      ) : (
        <div className="space-y-1">
          {sortedProjects.map((project) => (
            <ProjectCard
              key={project.slug}
              project={project}
              isActive={activeProject === project.slug}
              onSelect={() => handleSelect(project.slug)}
              onDeselect={handleDeselect}
              onArchive={() => handleArchive(project.slug)}
              onDelete={() => handleDelete(project.slug)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
