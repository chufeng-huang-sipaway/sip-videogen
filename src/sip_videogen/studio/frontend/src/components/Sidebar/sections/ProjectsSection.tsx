import { useState, useEffect, useCallback } from 'react'
import { FolderOpen, X, Archive, Pencil, Inbox } from 'lucide-react'
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
import { useWorkstation } from '@/context/WorkstationContext'
import { bridge, isPyWebView, type ProjectEntry } from '@/lib/bridge'
import { buildStatusByAssetPath, normalizeAssetPath } from '@/lib/imageStatus'
import { EditProjectDialog } from '../EditProjectDialog'
const VIDEO_EXTS = new Set(['.mp4', '.mov', '.webm'])
function isVideoAsset(path: string): boolean { const dot = path.lastIndexOf('.'); return dot >= 0 && VIDEO_EXTS.has(path.slice(dot).toLowerCase()) }

interface ProjectCardProps {
  project: ProjectEntry
  isActive?: boolean
  onClick: () => void
  onEdit: () => void
  onArchive: () => void
  onDelete: () => void
}

function ProjectCard({ project, isActive, onClick, onEdit, onArchive, onDelete }: ProjectCardProps) {
  const isArchived = project.status === 'archived'

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>
        <div
          onClick={onClick}
          className={`
            flex items-center gap-2.5 py-1.5 px-2 rounded-md cursor-pointer group transition-all duration-200 overflow-hidden 
            ${isActive
              ? 'bg-sidebar-accent text-foreground shadow-sm font-medium'
              : 'text-muted-foreground/80 hover:bg-sidebar-accent/50 hover:text-foreground'
            } 
            ${isArchived ? 'opacity-60' : ''}
          `}
          title="View project assets"
        >
          <FolderOpen
            className={`h-4 w-4 shrink-0 transition-colors ${isActive ? 'text-foreground' : 'text-muted-foreground/70 group-hover:text-foreground'}`}
            strokeWidth={1.5}
          />
          <div className="flex-1 min-w-0 overflow-hidden">
            <div className="flex items-center gap-1.5">
              <span className="truncate flex-1">{project.name}</span>
              {isArchived && <Archive className="h-3 w-3 text-muted-foreground shrink-0" />}
            </div>
            {/* Asset count - only show if not archived or active to keep it clean, or always subtle */}
            <span className={`text-[10px] truncate block mt-0.5 ${isActive ? 'text-muted-foreground' : 'text-muted-foreground/60'}`}>
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
        <ContextMenuItem onClick={onDelete} className="text-destructive">
          Delete Project
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  )
}

export function ProjectsSection() {
  const { activeBrand } = useBrand()
  const { projects, activeProject, isLoading, error, refresh, updateProject, deleteProject, getProjectAssets, setActiveProject } = useProjects()
  const { setCurrentBatch, setSelectedIndex, statusVersion } = useWorkstation()
  const [generalCount, setGeneralCount] = useState(0)
  const [actionError, setActionError] = useState<string | null>(null)
  const [editingProjectSlug, setEditingProjectSlug] = useState<string | null>(null)
  //Load general assets count (refresh when statusVersion changes after deletion)
  useEffect(() => {
    if (!activeBrand || !isPyWebView()) { setGeneralCount(0); return }
    bridge.getGeneralAssets(activeBrand).then(r => setGeneralCount(r.count || 0)).catch(() => setGeneralCount(0))
  }, [activeBrand, statusVersion])
  //Refresh project list when assets change (to update asset counts)
  useEffect(() => { if (statusVersion > 0) refresh() }, [statusVersion, refresh])
  useEffect(() => { if (actionError) { const timer = setTimeout(() => setActionError(null), 5000); return () => clearTimeout(timer) } }, [actionError])
  //Load project assets into workstation
  const loadProjectAssets = useCallback(async (slug: string) => {
    if (!isPyWebView()) return
    try {
      const paths = await getProjectAssets(slug)
      let statusByAssetPath = new Map()
      if (activeBrand) {
        try {
          statusByAssetPath = buildStatusByAssetPath(await bridge.getUnsortedImages(activeBrand))
        } catch (e) {
          console.warn('Failed to load image status for project assets:', e)
        }
      }
      const imageAssets = paths.filter(p => !isVideoAsset(p)).sort((a, b) => { const nameA = a.split('/').pop() ?? a; const nameB = b.split('/').pop() ?? b; return nameB.localeCompare(nameA) })
      const batch = imageAssets.map(assetPath => {
        const status = statusByAssetPath.get(normalizeAssetPath(assetPath))
        return {
          id: status?.id ?? assetPath,
          path: '',
          originalPath: assetPath,
          prompt: status?.prompt ?? undefined,
          sourceTemplatePath: status?.sourceTemplatePath ?? undefined,
          timestamp: status?.timestamp ?? new Date().toISOString(),
          viewedAt: status ? (status.viewedAt ?? null) : undefined,
        }
      })
      setCurrentBatch(batch); setSelectedIndex(0)
    } catch (err) { console.error('Failed to load project assets:', err) }
  }, [activeBrand, getProjectAssets, setCurrentBatch, setSelectedIndex])
  //Load general (unsorted) assets into workstation
  const loadGeneralAssets = useCallback(async () => {
    if (!isPyWebView() || !activeBrand) return
    try {
      const result = await bridge.getGeneralAssets(activeBrand)
      const paths: string[] = result.assets || []
      let statusByAssetPath = new Map()
      try {
        statusByAssetPath = buildStatusByAssetPath(await bridge.getUnsortedImages(activeBrand))
      } catch (e) { console.warn('Failed to load image status for general assets:', e) }
      const imageAssets = paths.filter(p => !isVideoAsset(p)).sort((a, b) => { const nameA = a.split('/').pop() ?? a; const nameB = b.split('/').pop() ?? b; return nameB.localeCompare(nameA) })
      const batch = imageAssets.map(assetPath => {
        const status = statusByAssetPath.get(normalizeAssetPath(assetPath))
        return {
          id: status?.id ?? assetPath,
          path: '',
          originalPath: assetPath,
          prompt: status?.prompt ?? undefined,
          sourceTemplatePath: status?.sourceTemplatePath ?? undefined,
          timestamp: status?.timestamp ?? new Date().toISOString(),
          viewedAt: status ? (status.viewedAt ?? null) : undefined,
        }
      })
      setCurrentBatch(batch); setSelectedIndex(0)
    } catch (err) { console.error('Failed to load general assets:', err) }
  }, [activeBrand, setCurrentBatch, setSelectedIndex])
  //Auto-load active project's assets when component mounts or activeProject changes
  useEffect(() => { if (activeProject && isPyWebView()) { loadProjectAssets(activeProject) } }, [activeProject, loadProjectAssets])
  const handleDelete = async (slug: string) => { if (confirm(`Delete project "${slug}"? Generated assets will be kept.`)) { try { await deleteProject(slug) } catch (err) { setActionError(err instanceof Error ? err.message : 'Failed to delete project') } } }

  const handleArchive = async (slug: string) => {
    try {
      await updateProject(slug, undefined, undefined, 'archived')
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to archive project')
    }
  }

  if (!activeBrand) {
    return <div className="text-sm text-muted-foreground">Select a brand</div>
  }

  if (error) {
    return (
      <div className="text-sm text-destructive">
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
    <div className="space-y-2 pl-2 pr-1">
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

      {/* Unsorted (non-project) assets section */}
      <div className="mb-2"><div onClick={async()=>{await setActiveProject(null);loadGeneralAssets()}} className={`flex items-center gap-1.5 py-2 px-1.5 rounded-lg cursor-pointer group transition-all overflow-hidden ${activeProject===null?'bg-sidebar-accent text-foreground shadow-sm':'hover:bg-muted/50 text-muted-foreground hover:text-foreground'}`} title="Assets not associated with any project"><Inbox className={`h-3.5 w-3.5 shrink-0 ${activeProject===null?'text-foreground':'text-muted-foreground/70 group-hover:text-foreground'}`} /><div className="flex-1 min-w-0 overflow-hidden"><div className="flex items-center gap-1"><span className={`text-sm truncate italic ${activeProject===null?'font-medium text-foreground':'font-medium text-foreground/90'}`}>Unsorted</span></div><span className={`text-[10px] truncate block ${activeProject===null?'text-muted-foreground':'text-muted-foreground/60'}`}>{generalCount} asset{generalCount !== 1 ? 's' : ''}</span></div></div></div>

      {sortedProjects.length === 0 ? (<p className="text-sm text-muted-foreground italic">{isLoading ? 'Loading...' : 'No projects yet. Click + to create a campaign.'}</p>) : (<div className="space-y-1">{sortedProjects.map((project) => (<ProjectCard key={project.slug} project={project} isActive={activeProject === project.slug} onClick={async()=>{await setActiveProject(project.slug);loadProjectAssets(project.slug)}} onEdit={() => setEditingProjectSlug(project.slug)} onArchive={() => handleArchive(project.slug)} onDelete={() => handleDelete(project.slug)} />))}</div>)}

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
