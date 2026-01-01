import { useEffect, useState, useCallback, useRef, useMemo } from 'react'
import { Image, Loader2, RefreshCw, AlertTriangle, Play, Film } from 'lucide-react'
import { useProjects } from '@/context/ProjectContext'
import { useBrand } from '@/context/BrandContext'
import { useWorkstation } from '@/context/WorkstationContext'
import { bridge, isPyWebView } from '@/lib/bridge'
import { buildStatusByAssetPath, normalizeAssetPath } from '@/lib/imageStatus'
import { isHiddenAssetPath } from '@/lib/mediaUtils'
import { VideoViewer } from '@/components/ui/video-viewer'
import { Button } from '@/components/ui/button'

// Thumbnail cache for the session (Map<assetPath, dataUrl>)
const thumbnailCache = new Map<string, string>()
const VIDEO_EXTS = new Set(['.mp4', '.mov', '.webm'])

function isVideoAsset(path: string): boolean {
  const dot = path.lastIndexOf('.')
  if (dot < 0) return false
  return VIDEO_EXTS.has(path.slice(dot).toLowerCase())
}

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

function getErrorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err)
}

function isNotFoundError(message: string): boolean {
  return message.toLowerCase().includes('not found')
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
  const unmountedRef = useRef(false)

  const loadThumbnail = useCallback(async () => {
    // Check cache again
    if (thumbnailCache.has(path)) {
      if (!unmountedRef.current) {
        setSrc(thumbnailCache.get(path)!)
        setLoading(false)
      }
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
      if (!unmountedRef.current) {
        setSrc(dataUrl)
        setHasError(false)
      }
    } catch (err) {
      const message = getErrorMessage(err)
      if (!unmountedRef.current) {
        setHasError(true)
      }
      // Only treat as a "ghost item" if the backend confirms it is missing.
      // PyWebView can throw transient errors during concurrent calls.
      if (isNotFoundError(message)) {
        onLoadError?.(path)
      }
    } finally {
      if (!unmountedRef.current) {
        setLoading(false)
      }
      activeThumbnailLoads--
      runNextInQueue()
    }
  }, [path, onLoadError])

  useEffect(() => {
    unmountedRef.current = false
    return () => {
      unmountedRef.current = true
    }
  }, [])

  // Lazy loading with IntersectionObserver
  useEffect(() => {
    if (!isPyWebView() || loadedRef.current || thumbnailCache.has(path)) {
      setLoading(false)
      return
    }

    const container = containerRef.current
    if (!container) return

    if (typeof IntersectionObserver === 'undefined') {
      loadedRef.current = true
      void loadThumbnail()
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && !loadedRef.current) {
          loadedRef.current = true
          observer.disconnect()
          void loadThumbnail()
        }
      },
      { rootMargin: '50px' }
    )

    observer.observe(container)
    return () => observer.disconnect()
  }, [path, loadThumbnail])

  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('text/plain', path)
    try { e.dataTransfer.setData('text/uri-list', path) } catch { /* ignore */ }
    try { e.dataTransfer.setData('application/x-brand-asset', path) } catch { /* ignore */ }
    e.dataTransfer.effectAllowed = 'copy'
  }

  return (
    <div
      ref={containerRef}
      className="group relative aspect-square rounded-md overflow-hidden bg-neutral-100 dark:bg-neutral-800 border border-transparent hover:border-brand-500/50 hover:shadow-md transition-all duration-200 cursor-pointer"
      onClick={onClick}
      draggable={!!src}
      onDragStart={handleDragStart}
      title="Drag to chat or click to preview"
    >
      {loading ? (
        <div className="absolute inset-0 flex items-center justify-center bg-neutral-100 dark:bg-neutral-800 animate-pulse">
          <Loader2 className="h-4 w-4 text-neutral-400 animate-spin" />
        </div>
      ) : hasError ? (
        <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
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
        <div className="absolute inset-0 flex items-center justify-center text-muted-foreground group-hover:text-muted-foreground">
          <Image className="h-5 w-5" />
        </div>
      )}
    </div>
  )
}

function VideoThumbnail({ path: _path, onClick }: { path: string; onClick?: () => void }) {
  return (
    <div
      className="group relative aspect-square rounded-md overflow-hidden bg-gradient-to-br from-brand-500/20 via-brand-500/15 to-brand-500/10 dark:from-brand-500/30 dark:via-brand-500/20 dark:to-brand-500/15 border-2 border-brand-400/50 hover:border-brand-500 hover:shadow-md transition-all duration-200 cursor-pointer"
      onClick={onClick}
      title="Click to preview video"
    >
      {/* Video icon badge */}
      <div className="absolute top-1 left-1 flex items-center gap-0.5 bg-black/60 text-white px-1.5 py-0.5 rounded text-[9px] font-medium">
        <Film className="h-2.5 w-2.5" />
        <span>MP4</span>
      </div>
      {/* Play button center */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-10 h-10 rounded-full bg-white/90 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
          <Play className="w-5 h-5 text-brand-600 ml-0.5" />
        </div>
      </div>
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
  const { activeBrand } = useBrand()
  const { getProjectAssets, refresh: refreshProjects } = useProjects()
  const { setCurrentBatch, setSelectedIndex } = useWorkstation()
  const [assets, setAssets] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [previewVideo, setPreviewVideo] = useState<{ src: string; path: string } | null>(null)
  const [missingAssetsBanner, setMissingAssetsBanner] = useState(false)
  const [thumbnailReloadNonce, setThumbnailReloadNonce] = useState(0)

  // Refs for polling
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const refreshInFlightRef = useRef(false)
  const errorCountRef = useRef(0)
  const pollIntervalMs = useRef(POLL_INTERVAL_NORMAL)
  const isMountedRef = useRef(true)

  // Track failed asset paths
  const failedAssetsRef = useRef<Set<string>>(new Set())
  const missingAssetsRefreshTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Clear thumbnail cache when switching brands to avoid cross-brand stale thumbnails.
  useEffect(() => {
    thumbnailCache.clear()
    setThumbnailReloadNonce((n) => n + 1)
    failedAssetsRef.current.clear()
  }, [activeBrand])

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

      // Filter out any paths that have previously failed (ghost items) and hidden assets (concept images)
      const validPaths = paths.filter((p) => !failedAssetsRef.current.has(p) && !isHiddenAssetPath(p))
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
    const failedAssets = failedAssetsRef.current
    failedAssets.clear()
    void loadAssets(false)
    return () => {
      failedAssets.clear()
    }
  }, [loadAssets])

  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  const scheduleNextPoll = useCallback((delayMs: number) => {
    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current)
    }

    pollTimeoutRef.current = setTimeout(async () => {
      if (!isMountedRef.current) return

      if (!document.hidden) {
        await loadAssets(true)
      }

      if (!isMountedRef.current) return
      scheduleNextPoll(pollIntervalMs.current)
    }, delayMs)
  }, [loadAssets])

  // Polling while component is mounted (project is expanded)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        if (pollTimeoutRef.current) {
          clearTimeout(pollTimeoutRef.current)
          pollTimeoutRef.current = null
        }
        return
      }

      void loadAssets(true)
      scheduleNextPoll(pollIntervalMs.current)
    }

    scheduleNextPoll(pollIntervalMs.current)
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current)
        pollTimeoutRef.current = null
      }
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [loadAssets, scheduleNextPoll])

  // Clear any pending debounced missing-assets refresh on unmount
  useEffect(() => {
    return () => {
      if (missingAssetsRefreshTimeoutRef.current) {
        clearTimeout(missingAssetsRefreshTimeoutRef.current)
        missingAssetsRefreshTimeoutRef.current = null
      }
    }
  }, [])

  // Handle thumbnail load errors (ghost item detection)
  const handleThumbnailError = useCallback((path: string) => {
    failedAssetsRef.current.add(path)
    setMissingAssetsBanner(true)

    // Remove the failed asset from the list immediately
    setAssets((prev) => prev.filter((p) => p !== path))

    // Trigger a refresh to update the list
    if (missingAssetsRefreshTimeoutRef.current) {
      clearTimeout(missingAssetsRefreshTimeoutRef.current)
    }
    missingAssetsRefreshTimeoutRef.current = setTimeout(() => {
      void loadAssets(true).finally(() => setMissingAssetsBanner(false))
      missingAssetsRefreshTimeoutRef.current = null
    }, 500)
  }, [loadAssets])

  // Memoize sorted assets (newest first based on filename patterns)
  const sortedAssets = useMemo(() => {
    return [...assets].sort((a, b) => {
      const nameA = a.split('/').pop() ?? a
      const nameB = b.split('/').pop() ?? b
      return nameB.localeCompare(nameA)
    })
  }, [assets])

  const handlePreview = useCallback(async (clickedPath: string) => {
    if (!isPyWebView()) return
    try {
      //Filter to images only (exclude videos)
      const imageAssets = sortedAssets.filter(p => !isVideoAsset(p))
      let statusByAssetPath = new Map()
      if (activeBrand) {
        try {
          statusByAssetPath = buildStatusByAssetPath(await bridge.getUnsortedImages(activeBrand))
        } catch (e) {
          console.warn('Failed to load image status for project asset grid:', e)
        }
      }
      //Create batch - clicked image will be loaded lazily via originalPath
      const allImages = imageAssets.map((assetPath) => {
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
      const clickedIndex = imageAssets.findIndex(p => p === clickedPath)
      setCurrentBatch(allImages)
      setSelectedIndex(clickedIndex >= 0 ? clickedIndex : 0)
    } catch (err) {
      console.error('Failed to load image:', err)
    }
  }, [activeBrand, sortedAssets, setCurrentBatch, setSelectedIndex])

  const handlePreviewVideo = useCallback(async (path: string) => {
    if (!isPyWebView()) return
    try {
      const dataUrl = await bridge.getVideoData(path)
      setPreviewVideo({ src: dataUrl, path })
    } catch (err) {
      console.error('Failed to load video preview:', err)
      const message = getErrorMessage(err)
      if (isNotFoundError(message)) {
        handleThumbnailError(path)
      }
    }
  }, [handleThumbnailError])

  const handleManualRefresh = useCallback(() => {
    // Clear failed assets to retry them
    failedAssetsRef.current.clear()
    if (missingAssetsRefreshTimeoutRef.current) {
      clearTimeout(missingAssetsRefreshTimeoutRef.current)
      missingAssetsRefreshTimeoutRef.current = null
    }
    setMissingAssetsBanner(false)
    setThumbnailReloadNonce((n) => n + 1)
    void loadAssets(false)
  }, [loadAssets])

  if (isLoading) {
    return (
      <div className="py-2">
        {/* Skeleton loading state */}
        <div className="grid grid-cols-[repeat(auto-fill,minmax(64px,1fr))] gap-2">
          {Array.from({ length: Math.min(expectedAssetCount ?? 4, 8) }).map((_, i) => (
            <div
              key={i}
              className="aspect-square rounded-lg bg-neutral-100 dark:bg-neutral-800 animate-pulse"
            />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="py-2 px-2 text-xs text-destructive flex items-center gap-2">
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
      <div className="py-4 px-2 text-xs text-center text-muted-foreground italic bg-muted/50 rounded-lg border border-dashed border-border">
        <p>No assets yet</p>
        <p className="mt-1 text-[10px]">Generate images in the chat to see them here</p>
      </div>
    )
  }

  return (
    <>
      {/* Missing assets banner */}
      {missingAssetsBanner && (
        <div className="mb-2 py-1.5 px-2 text-[10px] text-muted-foreground bg-muted rounded flex items-center gap-1.5">
          <AlertTriangle className="h-3 w-3 shrink-0" />
          <span>Some assets were removed. Refreshing...</span>
        </div>
      )}

      {/* Header with refresh indicator */}
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] text-muted-foreground">
          {sortedAssets.length} asset{sortedAssets.length !== 1 ? 's' : ''}
        </span>
        <div className="flex items-center gap-1">
          {isRefreshing && (
            <Loader2 className="h-3 w-3 text-muted-foreground animate-spin" />
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

      <div className="grid grid-cols-[repeat(auto-fill,minmax(60px,1fr))] gap-1.5 py-1">
        {sortedAssets.map((path) => (
          isVideoAsset(path) ? (
            <VideoThumbnail
              key={`${path}:${thumbnailReloadNonce}`}
              path={path}
              onClick={() => handlePreviewVideo(path)}
            />
          ) : (
            <AssetThumbnail
              key={`${path}:${thumbnailReloadNonce}`}
              path={path}
              onClick={() => handlePreview(path)}
              onLoadError={handleThumbnailError}
            />
          )
        ))}
      </div>
      <VideoViewer
        src={previewVideo?.src ?? null}
        filePath={previewVideo?.path}
        onClose={() => setPreviewVideo(null)}
      />
    </>
  )
}
