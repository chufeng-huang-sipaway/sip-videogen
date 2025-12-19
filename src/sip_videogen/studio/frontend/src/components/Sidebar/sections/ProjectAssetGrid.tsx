import { useEffect, useState, useCallback, useRef, useMemo } from 'react'
import { Image, Loader2, RefreshCw, AlertTriangle } from 'lucide-react'
import { useProjects } from '@/context/ProjectContext'
import { bridge, isPyWebView } from '@/lib/bridge'
import { ImageViewer } from '@/components/ui/image-viewer'
import { Button } from '@/components/ui/button'

// Thumbnail cache for the session (Map<assetPath, dataUrl>)
const thumbnailCache = new Map<string, string>()

// Concurrency limiter for thumbnail loading
const MAX_CONCURRENT_THUMBNAILS = 4
let activeThumbnailLoads = 0
const thumbnailQueue: Array<() => void> = []

function runNextInQueue() {
  if (thumbnailQueue.length > 0 && activeThumbnailLoads < MAX_CONCURRENT_THUMBNAILS) {
    const next = thumbnailQueue.shift()
    if (next) next()
  }
}

interface AssetThumbnailProps {
  path: string
  onClick?: () => void
  onLoadError?: (path: string) => void
}

function AssetThumbnail({ path, onClick, onLoadError }: AssetThumbnailProps) {
  const [src, setSrc] = useState<string | null>(() => thumbnailCache.get(path) ?? null)
  const [loading, setLoading] = useState(!thumbnailCache.has(path))
  const [hasError, setHasError] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const loadedRef = useRef(false)

  // Lazy loading with IntersectionObserver
  useEffect(() => {
    if (!isPyWebView() || loadedRef.current || thumbnailCache.has(path)) {
      setLoading(false)
      return
    }

    const container = containerRef.current
    if (!container) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && !loadedRef.current) {
          loadedRef.current = true
          observer.disconnect()
          loadThumbnail()
        }
      },
      { rootMargin: '50px' }
    )

    observer.observe(container)
    return () => observer.disconnect()
  }, [path])

  const loadThumbnail = useCallback(async () => {
    // Check cache again
    if (thumbnailCache.has(path)) {
      setSrc(thumbnailCache.get(path)!)
      setLoading(false)
      return
    }

    // Queue if too many concurrent loads
    if (activeThumbnailLoads >= MAX_CONCURRENT_THUMBNAILS) {
      await new Promise<void>((resolve) => {
        thumbnailQueue.push(resolve)
      })
    }

    activeThumbnailLoads++
    try {
      const dataUrl = await bridge.getAssetThumbnail(path)
      thumbnailCache.set(path, dataUrl)
      setSrc(dataUrl)
      setHasError(false)
    } catch {
      setHasError(true)
      onLoadError?.(path)
    } finally {
      setLoading(false)
      activeThumbnailLoads--
      runNextInQueue()
    }
  }, [path, onLoadError])

  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('application/x-brand-asset', path)
    e.dataTransfer.setData('text/plain', path)
    e.dataTransfer.effectAllowed = 'copy'
  }

  return (
    <div
      ref={containerRef}
      className="group relative aspect-square rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-800 border border-transparent hover:border-blue-500/50 hover:shadow-md transition-all duration-200 cursor-pointer"
      onClick={onClick}
      draggable={!!src}
      onDragStart={handleDragStart}
      title="Drag to chat or click to preview"
    >
      {loading ? (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100 dark:bg-gray-800 animate-pulse">
          <Loader2 className="h-4 w-4 text-gray-400 animate-spin" />
        </div>
      ) : hasError ? (
        <div className="absolute inset-0 flex items-center justify-center text-amber-500">
          <AlertTriangle className="h-4 w-4" />
        </div>
      ) : src ? (
        <>
          <img
            src={src}
            alt=""
            className="w-full h-full object-cover object-center transition-transform duration-300 group-hover:scale-105"
          />
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors duration-200" />
        </>
      ) : (
        <div className="absolute inset-0 flex items-center justify-center text-gray-400 group-hover:text-gray-500">
          <Image className="h-5 w-5" />
        </div>
      )}
    </div>
  )
}

interface ProjectAssetGridProps {
  projectSlug: string
  expectedAssetCount?: number // Used to detect when assets have changed
}

// Polling configuration
const POLL_INTERVAL_NORMAL = 2000 // 2 seconds
const POLL_INTERVAL_BACKOFF = 5000 // 5 seconds after errors

export function ProjectAssetGrid({ projectSlug, expectedAssetCount }: ProjectAssetGridProps) {
  const { getProjectAssets, refresh: refreshProjects } = useProjects()
  const [assets, setAssets] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [previewImage, setPreviewImage] = useState<{ src: string; path: string } | null>(null)
  const [missingAssetsBanner, setMissingAssetsBanner] = useState(false)

  // Refs for polling
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const refreshInFlightRef = useRef(false)
  const errorCountRef = useRef(0)
  const pollIntervalMs = useRef(POLL_INTERVAL_NORMAL)

  // Track failed asset paths
  const failedAssetsRef = useRef<Set<string>>(new Set())

  const loadAssets = useCallback(async (isBackgroundRefresh = false) => {
    if (refreshInFlightRef.current) return
    refreshInFlightRef.current = true

    if (!isBackgroundRefresh) {
      setIsLoading(true)
    } else {
      setIsRefreshing(true)
    }
    setError(null)

    try {
      const paths = await getProjectAssets(projectSlug)

      // Filter out any paths that have previously failed (ghost items)
      const validPaths = paths.filter((p) => !failedAssetsRef.current.has(p))
      setAssets(validPaths)

      // If actual count differs from expected, refresh projects list
      if (expectedAssetCount !== undefined && validPaths.length !== expectedAssetCount) {
        refreshProjects()
      }

      // Reset error count on success
      errorCountRef.current = 0
      pollIntervalMs.current = POLL_INTERVAL_NORMAL
    } catch (err) {
      if (!isBackgroundRefresh) {
        setError(err instanceof Error ? err.message : 'Failed to load assets')
      }
      // Backoff after repeated errors
      errorCountRef.current++
      if (errorCountRef.current >= 2) {
        pollIntervalMs.current = POLL_INTERVAL_BACKOFF
      }
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
      refreshInFlightRef.current = false
    }
  }, [projectSlug, getProjectAssets, expectedAssetCount, refreshProjects])

  // Initial load
  useEffect(() => {
    loadAssets(false)
    // Reset failed assets when project changes
    failedAssetsRef.current.clear()
    return () => {
      failedAssetsRef.current.clear()
    }
  }, [loadAssets])

  // Polling while component is mounted (project is expanded)
  useEffect(() => {
    const startPolling = () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
      pollIntervalRef.current = setInterval(() => {
        // Skip if document is hidden
        if (document.hidden) return
        loadAssets(true)
      }, pollIntervalMs.current)
    }

    const handleVisibilityChange = () => {
      if (document.hidden) {
        // Pause polling when hidden
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
        }
      } else {
        // Resume polling when visible, and do an immediate refresh
        loadAssets(true)
        startPolling()
      }
    }

    // Start polling
    startPolling()
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [loadAssets])

  // Handle thumbnail load errors (ghost item detection)
  const handleThumbnailError = useCallback((path: string) => {
    failedAssetsRef.current.add(path)
    setMissingAssetsBanner(true)

    // Remove the failed asset from the list immediately
    setAssets((prev) => prev.filter((p) => p !== path))

    // Trigger a refresh to update the list
    setTimeout(() => {
      loadAssets(true)
      setMissingAssetsBanner(false)
    }, 2000)
  }, [loadAssets])

  const handlePreview = useCallback(async (path: string) => {
    if (!isPyWebView()) return
    try {
      const dataUrl = await bridge.getAssetFull(path)
      setPreviewImage({ src: dataUrl, path })
    } catch (err) {
      console.error('Failed to load preview:', err)
      // This might be a ghost item
      handleThumbnailError(path)
    }
  }, [handleThumbnailError])

  const handleManualRefresh = useCallback(() => {
    // Clear failed assets to retry them
    failedAssetsRef.current.clear()
    loadAssets(false)
  }, [loadAssets])

  // Memoize sorted assets (newest first based on filename patterns)
  const sortedAssets = useMemo(() => {
    return [...assets].sort((a, b) => {
      // Sort by filename descending (assuming timestamp-based or sequential naming)
      const nameA = a.split('/').pop() ?? a
      const nameB = b.split('/').pop() ?? b
      return nameB.localeCompare(nameA)
    })
  }, [assets])

  if (isLoading) {
    return (
      <div className="py-2">
        {/* Skeleton loading state */}
        <div className="grid grid-cols-[repeat(auto-fill,minmax(80px,1fr))] gap-2">
          {Array.from({ length: Math.min(expectedAssetCount ?? 4, 8) }).map((_, i) => (
            <div
              key={i}
              className="aspect-square rounded-lg bg-gray-100 dark:bg-gray-800 animate-pulse"
            />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="py-2 px-2 text-xs text-red-500 flex items-center gap-2">
        <span>{error}</span>
        <Button
          variant="ghost"
          size="sm"
          className="h-5 px-1.5"
          onClick={handleManualRefresh}
        >
          <RefreshCw className="h-3 w-3" />
        </Button>
      </div>
    )
  }

  if (sortedAssets.length === 0) {
    return (
      <div className="py-4 px-2 text-xs text-center text-gray-400 italic bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-dashed border-gray-200 dark:border-gray-800">
        <p>No assets yet</p>
        <p className="mt-1 text-[10px]">Generate images in the chat to see them here</p>
      </div>
    )
  }

  return (
    <>
      {/* Missing assets banner */}
      {missingAssetsBanner && (
        <div className="mb-2 py-1.5 px-2 text-[10px] text-amber-600 bg-amber-50 dark:bg-amber-950/30 rounded flex items-center gap-1.5">
          <AlertTriangle className="h-3 w-3 shrink-0" />
          <span>Some assets were removed. Refreshing...</span>
        </div>
      )}

      {/* Header with refresh indicator */}
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] text-gray-400">
          {sortedAssets.length} asset{sortedAssets.length !== 1 ? 's' : ''}
        </span>
        <div className="flex items-center gap-1">
          {isRefreshing && (
            <Loader2 className="h-3 w-3 text-gray-400 animate-spin" />
          )}
          <Button
            variant="ghost"
            size="sm"
            className="h-5 w-5 p-0"
            onClick={handleManualRefresh}
            title="Refresh assets"
          >
            <RefreshCw className="h-3 w-3" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-[repeat(auto-fill,minmax(80px,1fr))] gap-2 py-1">
        {sortedAssets.map((path) => (
          <AssetThumbnail
            key={path}
            path={path}
            onClick={() => handlePreview(path)}
            onLoadError={handleThumbnailError}
          />
        ))}
      </div>
      <ImageViewer
        src={previewImage?.src ?? null}
        filePath={previewImage?.path}
        fileType="asset"
        onClose={() => setPreviewImage(null)}
      />
    </>
  )
}
