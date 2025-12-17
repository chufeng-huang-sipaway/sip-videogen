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
    <div className="border-b border-gray-200 dark:border-gray-700 bg-green-50/50 dark:bg-green-900/10">
      <div className="px-4 py-2">
        <button
          type="button"
          className="flex items-center gap-2 text-xs text-green-600 dark:text-green-400 hover:text-green-700 dark:hover:text-green-300"
          onClick={handleToggle}
          disabled={loading}
        >
          <FolderOpen className="h-3 w-3" />
          <span className="font-medium">Project: {project.name}</span>
          {loading ? (
            <span className="text-gray-400">...</span>
          ) : expanded ? (
            <ChevronUp className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )}
        </button>
      </div>
      {expanded && projectFull && (
        <div className="px-4 pb-3 text-xs">
          {projectFull.instructions ? (
            <div className="bg-white dark:bg-gray-800 rounded border border-green-200 dark:border-green-800 p-2 max-h-32 overflow-y-auto">
              <div className="text-gray-500 dark:text-gray-400 mb-1 font-medium">Instructions:</div>
              <div className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                {projectFull.instructions}
              </div>
            </div>
          ) : (
            <div className="text-gray-400 italic">No instructions set for this project.</div>
          )}
          {projectFull.asset_count > 0 && (
            <div className="text-gray-500 dark:text-gray-400 mt-2">
              {projectFull.asset_count} asset{projectFull.asset_count !== 1 ? 's' : ''} generated
            </div>
          )}
        </div>
      )}
    </div>
  )
}
