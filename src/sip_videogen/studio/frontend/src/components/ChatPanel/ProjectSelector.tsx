import { ChevronDown, Check, FolderKanban } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type { ProjectEntry } from '@/lib/bridge'

interface ProjectSelectorProps {
  projects: ProjectEntry[]
  activeProject: string | null
  onSelect: (slug: string | null) => Promise<void>
  disabled?: boolean
}

export function ProjectSelector({
  projects,
  activeProject,
  onSelect,
  disabled = false,
}: ProjectSelectorProps) {
  // Only show active (non-archived) projects in the selector
  const activeProjects = projects.filter(p => p.status === 'active')
  const currentProject = projects.find(p => p.slug === activeProject)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          disabled={disabled}
          className="gap-1.5 text-xs h-7 px-2"
        >
          <FolderKanban className="h-3.5 w-3.5 text-green-600" />
          <span className="truncate max-w-[100px]">
            {currentProject?.name || 'No Project'}
          </span>
          <ChevronDown className="h-3 w-3 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-48">
        <DropdownMenuItem
          onClick={() => onSelect(null)}
          className="text-gray-500"
        >
          <span className="flex-1">No Project</span>
          {!activeProject && <Check className="h-4 w-4 text-green-500" />}
        </DropdownMenuItem>
        {activeProjects.length > 0 && (
          <>
            <DropdownMenuSeparator />
            {activeProjects.map((project) => (
              <DropdownMenuItem
                key={project.slug}
                onClick={() => onSelect(project.slug)}
              >
                <span className="flex-1 truncate">{project.name}</span>
                {project.slug === activeProject && (
                  <Check className="h-4 w-4 text-green-500" />
                )}
              </DropdownMenuItem>
            ))}
          </>
        )}
        {activeProjects.length === 0 && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem disabled className="text-xs text-gray-400 italic">
              No projects yet
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
