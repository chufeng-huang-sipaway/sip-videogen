import { useEffect, useState, useCallback } from 'react'
import { Image, Loader2 } from 'lucide-react'
import { useProjects } from '@/context/ProjectContext'
import { bridge, isPyWebView } from '@/lib/bridge'
import { ImageViewer } from '@/components/ui/image-viewer'

interface AssetThumbnailProps {
  path: string
  onClick?: () => void
}

function AssetThumbnail({ path, onClick }: AssetThumbnailProps) {
  const [src, setSrc] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (!isPyWebView()) {
        setLoading(false)
        return
      }
      try {
        const dataUrl = await bridge.getAssetThumbnail(path)
        if (!cancelled) setSrc(dataUrl)
      } catch {
        // Ignore thumbnail errors
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [path])

  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('application/x-brand-asset', path)
    e.dataTransfer.setData('text/plain', path)
    e.dataTransfer.effectAllowed = 'copy'
  }

  if (loading) {
    return (
      <div className="aspect-square rounded bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
        <Loader2 className="h-4 w-4 text-gray-400 animate-spin" />
      </div>
    )
  }

  if (!src) {
    return (
      <div
        className="aspect-square rounded bg-gray-100 dark:bg-gray-800 flex items-center justify-center cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
        onClick={onClick}
        draggable
        onDragStart={handleDragStart}
        title="Drag to chat or click to preview"
      >
        <Image className="h-4 w-4 text-gray-400" />
      </div>
    )
  }

  return (
    <img
      src={src}
      alt=""
      className="aspect-square rounded object-cover cursor-pointer hover:opacity-80 transition-opacity"
      onClick={onClick}
      draggable
      onDragStart={handleDragStart}
      title="Drag to chat or click to preview"
    />
  )
}

interface ProjectAssetGridProps {
  projectSlug: string
  expectedAssetCount?: number // Used to detect when assets have changed
}

export function ProjectAssetGrid({ projectSlug, expectedAssetCount }: ProjectAssetGridProps) {
  const { getProjectAssets, refresh: refreshProjects } = useProjects()
  const [assets, setAssets] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [previewImage, setPreviewImage] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setIsLoading(true)
      setError(null)
      try {
        const paths = await getProjectAssets(projectSlug)
        if (!cancelled) {
          setAssets(paths)
          // If actual count differs from expected, refresh projects list to update the count
          if (expectedAssetCount !== undefined && paths.length !== expectedAssetCount) {
            refreshProjects()
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load assets')
        }
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [projectSlug, getProjectAssets, expectedAssetCount, refreshProjects])

  const handlePreview = useCallback(async (path: string) => {
    if (!isPyWebView()) return
    try {
      const dataUrl = await bridge.getAssetFull(path)
      setPreviewImage(dataUrl)
    } catch (err) {
      console.error('Failed to load preview:', err)
    }
  }, [])

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-2 text-xs text-gray-400">
        <Loader2 className="h-3 w-3 animate-spin" />
        <span>Loading assets...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="py-2 text-xs text-red-500">
        {error}
      </div>
    )
  }

  if (assets.length === 0) {
    return (
      <div className="py-2 text-xs text-gray-400 italic">
        No assets generated yet
      </div>
    )
  }

  return (
    <>
      <div className="grid grid-cols-3 gap-1.5 py-2">
        {assets.map((path) => (
          <AssetThumbnail
            key={path}
            path={path}
            onClick={() => handlePreview(path)}
          />
        ))}
      </div>
      <ImageViewer src={previewImage} onClose={() => setPreviewImage(null)} />
    </>
  )
}
