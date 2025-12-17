import { useState, useEffect } from 'react'
import { FolderKanban, Plus, X, Archive, ChevronRight, ChevronDown, Pencil } from 'lucide-react'
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
import { ProjectAssetGrid } from './ProjectAssetGrid'
import { EditProjectDialog } from '../EditProjectDialog'

interface ProjectCardProps {
  project: ProjectEntry
  isActive?: boolean
  isExpanded: boolean
  onToggleExpand: () => void
  onEdit: () => void
  onArchive: () => void
  onDelete: () => void
}

function ProjectCard({
  project,
  isActive,
  isExpanded,
  onToggleExpand,
  onEdit,
  onArchive,
  onDelete,
}: ProjectCardProps) {
  const isArchived = project.status === 'archived'

  return (
    <div>
      <ContextMenu>
        <ContextMenuTrigger asChild>
          <div
            className={`flex items-center gap-1.5 py-2 px-1.5 rounded-lg cursor-pointer group transition-all overflow-hidden
              ${isActive
                ? 'bg-foreground text-background shadow-sm hover:bg-foreground/90'
                : 'hover:bg-muted/50 text-muted-foreground hover:text-foreground'}
              ${isArchived ? 'opacity-60' : ''}`}
            onClick={onToggleExpand}
            title="Click to view project assets"
          >
            {/* Expand/collapse chevron */}
            {isExpanded ? (
              <ChevronDown className={`h-3.5 w-3.5 shrink-0 ${isActive ? 'text-background/70' : 'text-muted-foreground/60'}`} />
            ) : (
              <ChevronRight className={`h-3.5 w-3.5 shrink-0 ${isActive ? 'text-background/70' : 'text-muted-foreground/60'}`} />
            )}
            <FolderKanban className={`h-3.5 w-3.5 shrink-0 ${isActive ? 'text-background/70' : 'text-muted-foreground/70'}`} />
            <div className="flex-1 min-w-0 overflow-hidden">
              <div className="flex items-center gap-1">
                <span className={`text-sm font-medium truncate ${isActive ? 'text-background' : 'text-foreground/90'}`}>{project.name}</span>
                {isArchived && <Archive className="h-3 w-3 text-muted-foreground shrink-0" />}
              </div>
              <span className={`text-[10px] truncate block ${isActive ? 'text-background/60' : 'text-muted-foreground/60'}`}>
                {project.asset_count} asset{project.asset_count !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
        </ContextMenuTrigger>
        <ContextMenuContent>
          <ContextMenuItem onClick={onEdit}>
            <Pencil className="h-4 w-4 mr-2" />
            Edit Project
          </ContextMenuItem>
          {!isArchived && (
            <>
              <ContextMenuSeparator />
              <ContextMenuItem onClick={onArchive}>
                <Archive className="h-4 w-4 mr-2" />
                Archive Project
              </ContextMenuItem>
            </>
          )}
          <ContextMenuSeparator />
          <ContextMenuItem onClick={onDelete} className="text-red-600">
            Delete Project
          </ContextMenuItem>
        </ContextMenuContent>
      </ContextMenu>

      {/* Expanded asset grid */}
      {isExpanded && (
        <div className="pl-8 pr-2">
          <ProjectAssetGrid projectSlug={project.slug} expectedAssetCount={project.asset_count} />
        </div>
      )}
    </div>
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
    updateProject,
    deleteProject,
  } = useProjects()
  const [expandedProject, setExpandedProject] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [editingProjectSlug, setEditingProjectSlug] = useState<string | null>(null)

  useEffect(() => {
    if (actionError) {
      const timer = setTimeout(() => setActionError(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [actionError])

  const handleToggleExpand = (slug: string) => {
    setExpandedProject((prev) => (prev === slug ? null : slug))
  }

  const handleDelete = async (slug: string) => {
    if (confirm(`Delete project "${slug}"? Generated assets will be kept.`)) {
      try {
        await deleteProject(slug)
        // Close expanded view if deleting expanded project
        if (expandedProject === slug) {
          setExpandedProject(null)
        }
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
              isExpanded={expandedProject === project.slug}
              onToggleExpand={() => handleToggleExpand(project.slug)}
              onEdit={() => setEditingProjectSlug(project.slug)}
              onArchive={() => handleArchive(project.slug)}
              onDelete={() => handleDelete(project.slug)}
            />
          ))}
        </div>
      )}

      {editingProjectSlug && (
        <EditProjectDialog
          open={!!editingProjectSlug}
          onOpenChange={(open) => {
            if (!open) setEditingProjectSlug(null)
          }}
          projectSlug={editingProjectSlug}
        />
      )}
    </div>
  )
}
