import { useState } from 'react'
import { FolderOpen, ChevronDown, ChevronUp } from 'lucide-react'
import type { ProjectEntry, ProjectFull } from '@/lib/bridge'

interface ProjectBannerProps {
  project: ProjectEntry | null
  projectFull: ProjectFull | null
  onLoadProjectDetails: (slug: string) => Promise<ProjectFull>
}

export function ProjectBanner({
  project,
  projectFull,
  onLoadProjectDetails,
}: ProjectBannerProps) {
  const [expanded, setExpanded] = useState(false)
  const [loading, setLoading] = useState(false)

  if (!project) return null

  const handleToggle = async () => {
    if (!expanded && !projectFull) {
      setLoading(true)
      try {
        await onLoadProjectDetails(project.slug)
      } catch {
        // Ignore errors - just don't expand
      } finally {
        setLoading(false)
      }
    }
    setExpanded(!expanded)
  }

  return (
    <div className="border-b border-border/40 bg-muted/20 backdrop-blur-sm">
      <div className="px-4 py-2">
        <button
          type="button"
          className="flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-primary transition-colors"
          onClick={handleToggle}
          disabled={loading}
        >
          <FolderOpen className="h-3.5 w-3.5" />
          <span>Project: {project.name}</span>
          {loading ? (
            <span className="text-muted-foreground/50">...</span>
          ) : expanded ? (
            <ChevronUp className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )}
        </button>
      </div>
      {expanded && projectFull && (
        <div className="px-4 pb-3 text-xs animate-in slide-in-from-top-1 duration-200">
          {projectFull.instructions ? (
            <div className="bg-background rounded-lg border border-border/60 p-3 max-h-32 overflow-y-auto shadow-sm">
              <div className="text-muted-foreground mb-1 font-medium text-[10px] uppercase tracking-wider">Instructions</div>
              <div className="text-foreground/90 whitespace-pre-wrap leading-relaxed">
                {projectFull.instructions}
              </div>
            </div>
          ) : (
            <div className="text-muted-foreground italic px-1">No instructions set for this project.</div>
          )}
          {projectFull.asset_count > 0 && (
            <div className="text-muted-foreground mt-2 px-1">
              {projectFull.asset_count} asset{projectFull.asset_count !== 1 ? 's' : ''} generated
            </div>
          )}
        </div>
      )}
    </div>
  )
}
