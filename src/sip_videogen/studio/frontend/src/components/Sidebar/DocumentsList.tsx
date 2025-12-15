import { useCallback, useEffect, useState } from 'react'
import { FileText, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from '@/components/ui/context-menu'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useBrand } from '@/context/BrandContext'
import { useDocuments } from '@/hooks/useDocuments'
import { isPyWebView } from '@/lib/bridge'
import { MarkdownContent } from '../ChatPanel/MarkdownContent'

const ALLOWED_DOC_EXTS = new Set(['.md', '.txt', '.json', '.yaml', '.yml'])

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function DocumentsList() {
  const { activeBrand } = useBrand()
  const { documents, isLoading, error, refresh, openInFinder, readDocument, deleteDocument, renameDocument, uploadDocument } =
    useDocuments(activeBrand)

  const [isDragging, setIsDragging] = useState(false)
  const [previewPath, setPreviewPath] = useState<string | null>(null)
  const [previewContent, setPreviewContent] = useState<string>('')
  const [isPreviewOpen, setIsPreviewOpen] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)

  // Auto-clear upload error after 5 seconds
  useEffect(() => {
    if (uploadError) {
      const timer = setTimeout(() => setUploadError(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [uploadError])

  const openPreview = useCallback(async (path: string) => {
    setPreviewPath(path)
    setPreviewContent('')
    setIsPreviewOpen(true)
    try {
      const content = await readDocument(path)
      setPreviewContent(content)
    } catch (err) {
      setPreviewContent(err instanceof Error ? err.message : 'Failed to load document')
    }
  }, [readDocument])

  const onDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (!activeBrand || !isPyWebView()) return

    const files = Array.from(e.dataTransfer.files)
    const rejectedFiles: string[] = []

    for (const file of files) {
      const lower = file.name.toLowerCase()
      const dot = lower.lastIndexOf('.')
      const ext = dot >= 0 ? lower.slice(dot) : ''
      if (!ALLOWED_DOC_EXTS.has(ext)) {
        console.warn(`[DocumentsList] Rejected file "${file.name}": unsupported extension "${ext}". Allowed: ${Array.from(ALLOWED_DOC_EXTS).join(', ')}`)
        rejectedFiles.push(file.name)
        continue
      }
      try {
        await uploadDocument(file)
      } catch (err) {
        console.error(`[DocumentsList] Failed to upload "${file.name}":`, err)
        rejectedFiles.push(file.name)
      }
    }

    if (rejectedFiles.length > 0) {
      const allowedList = Array.from(ALLOWED_DOC_EXTS).join(', ')
      setUploadError(`Unsupported file(s): ${rejectedFiles.join(', ')}. Allowed types: ${allowedList}`)
    }
  }, [activeBrand, uploadDocument])

  if (!activeBrand) {
    return <div className="text-sm text-gray-500">Select a brand</div>
  }

  if (error) {
    return (
      <div className="text-sm text-red-500">
        Error: {error}
        <Button variant="ghost" size="sm" onClick={refresh}>Retry</Button>
      </div>
    )
  }

  return (
    <div
      className={`space-y-2 ${isDragging ? 'bg-blue-50 dark:bg-blue-900/20 ring-2 ring-blue-500 rounded' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={onDrop}
    >
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
        Documents
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

      {documents.length === 0 ? (
        <p className="text-sm text-gray-400 italic">
          {isLoading ? 'Loading…' : 'No documents yet. Drag text files here to upload.'}
        </p>
      ) : (
        <div className="space-y-1">
          {documents.map((doc) => (
            <ContextMenu key={doc.path}>
              <ContextMenuTrigger asChild>
                <div
                  className="flex items-center gap-2 py-1 px-2 rounded hover:bg-gray-200/50 dark:hover:bg-gray-700/50 cursor-pointer group"
                  onClick={() => openPreview(doc.path)}
                >
                  <FileText className="h-4 w-4 text-gray-500 shrink-0" />
                  <span className="text-sm truncate flex-1">{doc.name}</span>
                  <span className="text-xs text-gray-400 opacity-0 group-hover:opacity-100">
                    {formatSize(doc.size)}
                  </span>
                </div>
              </ContextMenuTrigger>
              <ContextMenuContent>
                <ContextMenuItem onClick={() => openPreview(doc.path)}>Preview</ContextMenuItem>
                <ContextMenuItem onClick={() => openInFinder(doc.path)}>Reveal in Finder</ContextMenuItem>
                <ContextMenuSeparator />
                <ContextMenuItem
                  onClick={async () => {
                    const newName = prompt('New name:', doc.name)
                    if (newName) await renameDocument(doc.path, newName)
                  }}
                >
                  Rename
                </ContextMenuItem>
                <ContextMenuItem
                  onClick={async () => {
                    if (confirm(`Delete ${doc.name}?`)) await deleteDocument(doc.path)
                  }}
                  className="text-red-600"
                >
                  Delete
                </ContextMenuItem>
              </ContextMenuContent>
            </ContextMenu>
          ))}
        </div>
      )}

      <Dialog open={isPreviewOpen} onOpenChange={setIsPreviewOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>{previewPath || 'Document Preview'}</DialogTitle>
          </DialogHeader>
          <div className="max-h-[70vh] overflow-auto">
            {previewContent ? (
              previewPath?.endsWith('.md') ? (
                <MarkdownContent content={previewContent} />
              ) : (
                <pre className="text-xs whitespace-pre-wrap">{previewContent}</pre>
              )
            ) : (
              <p className="text-gray-500">Loading…</p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
