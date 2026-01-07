/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from 'react'
import { bridge, waitForPyWebViewReady, type ProjectEntry, type ProjectFull, type ProjectStatus } from '@/lib/bridge'
import { useBrand } from './BrandContext'

interface ProjectContextType {
  projects: ProjectEntry[]
  activeProject: string | null // Persisted server-side
  isLoading: boolean
  isRefreshing: boolean // True during background refresh (not initial load)
  error: string | null
  refresh: () => Promise<void>
  setActiveProject: (slug: string | null) => Promise<void>
  createProject: (name: string, instructions?: string) => Promise<string>
  updateProject: (projectSlug: string, name?: string, instructions?: string, status?: ProjectStatus) => Promise<void>
  deleteProject: (slug: string) => Promise<void>
  getProject: (slug: string) => Promise<ProjectFull>
  getProjectAssets: (slug: string) => Promise<string[]>
}

const ProjectContext = createContext<ProjectContextType | null>(null)

export function ProjectProvider({ children }: { children: ReactNode }) {
  const { activeBrand } = useBrand()
  const [projects, setProjects] = useState<ProjectEntry[]>([])
  const [activeProject, setActiveProjectState] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Single-flight guard to prevent concurrent refreshes
  const refreshInFlightRef = useRef(false)
  const hasInitiallyLoadedRef = useRef(false)

  const refresh = useCallback(async () => {
    if (!activeBrand) {
      setProjects([])
      setActiveProjectState(null)
      return
    }

    // Skip if already refreshing (single-flight guard)
    if (refreshInFlightRef.current) {
      return
    }
    refreshInFlightRef.current = true

    // Use isLoading for initial load, isRefreshing for subsequent refreshes
    const isInitialLoad = !hasInitiallyLoadedRef.current
    if (isInitialLoad) {
      setIsLoading(true)
    } else {
      setIsRefreshing(true)
    }
    setError(null)

    try {
      const ready = await waitForPyWebViewReady()
      if (!ready) {
        // Mock data for dev
        setProjects([
          {
            slug: 'christmas-campaign',
            name: 'Christmas Campaign',
            status: 'active' as ProjectStatus,
            asset_count: 5,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ])
        setActiveProjectState('christmas-campaign')
        hasInitiallyLoadedRef.current = true
        return
      }
      const result = await bridge.getProjects()
      setProjects(result.projects)
      setActiveProjectState(result.activeProject)
      hasInitiallyLoadedRef.current = true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load projects')
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
      refreshInFlightRef.current = false
    }
  }, [activeBrand])

  // Refresh when brand changes
  useEffect(() => {
    refresh()
  }, [refresh])

  // Refresh on window focus (user returns from Finder)
  useEffect(() => {
    if (!activeBrand) return

    const handleFocus = () => {
      // Only refresh if app was hidden (not just focus within app)
      if (!document.hidden) {
        refresh()
      }
    }

    const handleVisibilityChange = () => {
      if (!document.hidden) {
        refresh()
      }
    }

    window.addEventListener('focus', handleFocus)
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      window.removeEventListener('focus', handleFocus)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [activeBrand, refresh])

  const setActiveProject = useCallback(async (slug: string | null): Promise<void> => {
    const ready = await waitForPyWebViewReady()
    if (!ready) {
      // Dev mode - just update state
      setActiveProjectState(slug)
      return
    }
    try {
      await bridge.setActiveProject(slug)
      setActiveProjectState(slug)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to set active project')
      throw err
    }
  }, [])

  const createProject = useCallback(async (name: string, instructions?: string): Promise<string> => {
    const ready = await waitForPyWebViewReady()
    if (!ready) {
      throw new Error('Not running in PyWebView')
    }
    const slug = await bridge.createProject(name, instructions)
    await refresh()
    return slug
  }, [refresh])

  const updateProject = useCallback(async (
    projectSlug: string,
    name?: string,
    instructions?: string,
    status?: ProjectStatus
  ): Promise<void> => {
    const ready = await waitForPyWebViewReady()
    if (!ready) {
      throw new Error('Not running in PyWebView')
    }
    await bridge.updateProject(projectSlug, name, instructions, status)
    await refresh()
  }, [refresh])

  const deleteProject = useCallback(async (slug: string): Promise<void> => {
    const ready = await waitForPyWebViewReady()
    if (!ready) {
      throw new Error('Not running in PyWebView')
    }
    await bridge.deleteProject(slug)
    // Clear active project if it was the deleted one
    if (activeProject === slug) {
      setActiveProjectState(null)
    }
    await refresh()
  }, [activeProject, refresh])

  const getProject = useCallback(async (slug: string): Promise<ProjectFull> => {
    const ready = await waitForPyWebViewReady()
    if (!ready) {
      throw new Error('Not running in PyWebView')
    }
    return bridge.getProject(slug)
  }, [])

  const getProjectAssets = useCallback(async (slug: string): Promise<string[]> => {
    const ready = await waitForPyWebViewReady()
    if (!ready) {
      throw new Error('Not running in PyWebView')
    }
    return bridge.getProjectAssets(slug)
  }, [])

  return (
    <ProjectContext.Provider
      value={{
        projects,
        activeProject,
        isLoading,
        isRefreshing,
        error,
        refresh,
        setActiveProject,
        createProject,
        updateProject,
        deleteProject,
        getProject,
        getProjectAssets,
      }}
    >
      {children}
    </ProjectContext.Provider>
  )
}

export function useProjects() {
  const context = useContext(ProjectContext)
  if (!context) {
    throw new Error('useProjects must be used within a ProjectProvider')
  }
  return context
}
