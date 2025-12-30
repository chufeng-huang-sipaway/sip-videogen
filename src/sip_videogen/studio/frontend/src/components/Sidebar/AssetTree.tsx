import { useEffect, useState, useCallback } from 'react'
import { ChevronRight, ChevronDown, Folder, Image, Film, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from '@/components/ui/context-menu'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useBrand } from '@/context/BrandContext'
import { useAssets } from '@/hooks/useAssets'
import { bridge, isPyWebView, type AssetNode } from '@/lib/bridge'
import { getAllowedImageExts } from '@/lib/constants'
import { ImageViewer } from '../ui/image-viewer'
import { VideoViewer } from '../ui/video-viewer'

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function AssetThumbnail({ path }: { path: string }) {
  const [src, setSrc] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (!isPyWebView()) return
      try {
        const dataUrl = await bridge.getAssetThumbnail(path)
        if (!cancelled) setSrc(dataUrl)
      } catch {
        // Ignore thumbnail errors and fall back to icon
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [path])

  if (!src) {
    return <div className="h-5 w-5 rounded bg-neutral-200 dark:bg-neutral-700" />
  }

  return <img src={src} alt="" className="h-5 w-5 rounded object-cover" />
}

interface TreeItemProps {
  node: AssetNode
  depth?: number
  onDelete: (path: string) => void
  onRename: (path: string) => void
  onPreview: (path: string) => void
  onPreviewVideo: (path: string) => void
  onReveal: (path: string) => void
}

function TreeItem({ node, depth = 0, onDelete, onRename, onPreview, onPreviewVideo, onReveal }: TreeItemProps) {
  const [isOpen, setIsOpen] = useState(depth === 0)
  const hasChildren = node.type === 'folder' && node.children && node.children.length > 0

  const handleClick = () => {
    if (node.type === 'folder') {
      setIsOpen(!isOpen)
    } else if (node.type === 'image') {
      onPreview(node.path)
    } else if (node.type === 'video') {
      onPreviewVideo(node.path)
    }
  }

  const handleDragStart = (e: React.DragEvent) => {
    if (node.type !== 'image') return
    e.dataTransfer.setData('text/plain', node.path)
    try { e.dataTransfer.setData('text/uri-list', node.path) } catch { /* ignore */ }
    try { e.dataTransfer.setData('application/x-brand-asset', node.path) } catch { /* ignore */ }
    e.dataTransfer.effectAllowed = 'copy'
    // Set a custom drag image for better feedback
    const dragEl = e.currentTarget as HTMLElement
    if (dragEl) {
      e.dataTransfer.setDragImage(dragEl, 20, 20)
    }
  }

  return (
    <div>
      <ContextMenu>
        <ContextMenuTrigger asChild>
          <div
            className={`flex items-center gap-1 py-1 px-2 rounded hover:bg-gray-200/50 dark:hover:bg-gray-700/50 group ${
              node.type === 'image' ? 'cursor-grab active:cursor-grabbing' : 'cursor-pointer'
            }`}
            style={{ paddingLeft: `${depth * 12 + 8}px` }}
            onClick={handleClick}
            draggable={node.type === 'image'}
            onDragStart={handleDragStart}
            title={node.type === 'image' ? 'Drag to chat or click to preview' : undefined}
          >
            {node.type === 'folder' ? (
              hasChildren ? (
                isOpen ? <ChevronDown className="h-4 w-4 shrink-0" /> : <ChevronRight className="h-4 w-4 shrink-0" />
              ) : (
                <span className="w-4" />
              )
            ) : (
              <span className="w-4" />
            )}
            {node.type === 'folder' ? (
              <Folder className="h-4 w-4 text-muted-foreground shrink-0" />
            ) : node.type === 'image' && isPyWebView() ? (
              <AssetThumbnail path={node.path} />
            ) : node.type === 'video' ? (
              <Film className="h-4 w-4 text-muted-foreground shrink-0" />
            ) : (
              <Image className="h-4 w-4 text-muted-foreground shrink-0" />
            )}
            <span className="text-sm truncate flex-1">{node.name}</span>
            {node.size && (
              <span className="text-xs text-muted-foreground opacity-0 group-hover:opacity-100">
                {formatSize(node.size)}
              </span>
            )}
          </div>
        </ContextMenuTrigger>
        <ContextMenuContent>
          {node.type !== 'folder' && (
            <>
              <ContextMenuItem onClick={() => onReveal(node.path)}>
                Reveal in Finder
              </ContextMenuItem>
              <ContextMenuSeparator />
            </>
          )}
          {node.type !== 'folder' && (
            <>
              <ContextMenuItem onClick={() => onRename(node.path)}>
                Rename
              </ContextMenuItem>
              <ContextMenuItem onClick={() => onDelete(node.path)} className="text-destructive">
                Delete
              </ContextMenuItem>
            </>
          )}
        </ContextMenuContent>
      </ContextMenu>

      {isOpen && node.children?.map((child) => (
        <TreeItem
          key={child.path}
          node={child}
          depth={depth + 1}
          onDelete={onDelete}
          onRename={onRename}
          onPreview={onPreview}
          onPreviewVideo={onPreviewVideo}
          onReveal={onReveal}
        />
      ))}
    </div>
  )
}

export function AssetTree() {
  const { activeBrand } = useBrand()
  const { tree, isLoading, error, refresh, deleteAsset, renameAsset, uploadAsset } = useAssets(activeBrand)
  const [isDragging, setIsDragging] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [previewImage, setPreviewImage] = useState<{ src: string; path: string } | null>(null)
  const [previewVideo, setPreviewVideo] = useState<{ src: string; path: string } | null>(null)

  // Auto-clear upload error after 5 seconds
  useEffect(() => {
    if (uploadError) {
      const timer = setTimeout(() => setUploadError(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [uploadError])

  const handlePreview = useCallback(async (path: string) => {
    if (!isPyWebView()) return
    try {
      const dataUrl = await bridge.getAssetFull(path)
      setPreviewImage({ src: dataUrl, path })
    } catch (err) {
      console.error('Failed to load preview:', err)
    }
  }, [])

  const handlePreviewVideo = useCallback(async (path: string) => {
    if (!isPyWebView()) return
    try {
      const fileUrl = await bridge.getVideoPath(path)
      setPreviewVideo({ src: fileUrl, path })
    } catch (err) {
      console.error('Failed to load video preview:', err)
    }
  }, [])

  const handleReveal = useCallback(async (path: string) => {
    if (isPyWebView()) {
      await bridge.openAssetInFinder(path)
    }
  }, [])

  const handleDelete = useCallback(async (path: string) => {
    if (confirm(`Delete ${path}?`)) {
      await deleteAsset(path)
    }
  }, [deleteAsset])

  const handleRename = useCallback(async (path: string) => {
    const newName = prompt('New name:', path.split('/').pop())
    if (!newName) return
    await renameAsset(path, newName)
  }, [renameAsset])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    if (!isPyWebView()) return

    const files = Array.from(e.dataTransfer.files)
    const rejectedFiles: string[] = []
    const allowedImageExts = getAllowedImageExts()
    const allowedImageExtsSet = new Set(allowedImageExts)

    for (const file of files) {
      const lower = file.name.toLowerCase()
      const dot = lower.lastIndexOf('.')
      const ext = dot >= 0 ? lower.slice(dot) : ''

      // Check both MIME type and extension for better validation
      const isValidMime = file.type.startsWith('image/')
      const isValidExt = allowedImageExtsSet.has(ext)

      if (!isValidMime && !isValidExt) {
        console.warn(`[AssetTree] Rejected file "${file.name}": not a valid image. Type: "${file.type}", Extension: "${ext}"`)
        rejectedFiles.push(file.name)
        continue
      }

      try {
        await uploadAsset(file, 'generated')
      } catch (err) {
        console.error(`[AssetTree] Failed to upload "${file.name}":`, err)
        rejectedFiles.push(file.name)
      }
    }

    if (rejectedFiles.length > 0) {
      const allowedList = allowedImageExts.join(', ')
      setUploadError(`Unsupported file(s): ${rejectedFiles.join(', ')}. Allowed types: ${allowedList}`)
    }
  }, [uploadAsset])

  if (!activeBrand) {
    return <div className="text-sm text-muted-foreground">Select a brand</div>
  }

  if (error) {
    return (
      <div className="text-sm text-destructive">
        Error: {error}
        <Button variant="ghost" size="sm" onClick={refresh}>Retry</Button>
      </div>
    )
  }

  return (
    <div
      className={`space-y-2 ${isDragging ? 'bg-brand-a10 dark:bg-brand-a10 ring-2 ring-brand-500 rounded' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        Assets
      </h3>

      {uploadError && (
        <Alert variant="destructive" className="py-2 px-3">
          <AlertDescription className="flex items-center justify-between text-xs">
            <span>{uploadError}</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-4 w-4 shrink-0"
              onClick={() => setUploadError(null)}
            >
              <X className="h-3 w-3" />
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {tree.length === 0 ? (
        <p className="text-sm text-muted-foreground italic">
          {isLoading ? 'Loading...' : 'No assets yet. Drag images here to upload.'}
        </p>
      ) : (
        <div className="space-y-1">
          {tree.map((node) => (
            <TreeItem
              key={node.path}
              node={node}
              onDelete={handleDelete}
              onRename={handleRename}
              onPreview={handlePreview}
              onPreviewVideo={handlePreviewVideo}
              onReveal={handleReveal}
            />
          ))}
        </div>
      )}
      <ImageViewer
        src={previewImage?.src ?? null}
        filePath={previewImage?.path}
        fileType="asset"
        onClose={() => setPreviewImage(null)}
      />
      <VideoViewer
        src={previewVideo?.src ?? null}
        filePath={previewVideo?.path}
        onClose={() => setPreviewVideo(null)}
      />
    </div>
  )
}
