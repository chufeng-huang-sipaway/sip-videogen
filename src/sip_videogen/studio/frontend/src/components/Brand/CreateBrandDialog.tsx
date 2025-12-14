import { useState, useCallback } from 'react'
import { Plus, Upload, X, FileText, Image } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Spinner } from '@/components/ui/spinner'
import { bridge, isPyWebView } from '@/lib/bridge'

const ALLOWED_IMAGE_EXTS = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg']
const ALLOWED_DOC_EXTS = ['.md', '.txt']
const MAX_DOC_SIZE = 50 * 1024 // 50KB

interface UploadedFile {
  file: File
  type: 'image' | 'document'
  dataUrl?: string
}

interface CreateBrandDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: (slug: string) => void
}

export function CreateBrandDialog({
  open,
  onOpenChange,
  onCreated,
}: CreateBrandDialogProps) {
  const [description, setDescription] = useState('')
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  const handleFileAdd = useCallback(async (newFiles: FileList | File[]) => {
    const fileArray = Array.from(newFiles)
    const processed: UploadedFile[] = []

    for (const file of fileArray) {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase()

      if (ALLOWED_IMAGE_EXTS.includes(ext)) {
        // Read image as data URL for preview
        const dataUrl = await new Promise<string>((resolve) => {
          const reader = new FileReader()
          reader.onload = () => resolve(reader.result as string)
          reader.readAsDataURL(file)
        })
        processed.push({ file, type: 'image', dataUrl })
      } else if (ALLOWED_DOC_EXTS.includes(ext)) {
        if (file.size > MAX_DOC_SIZE) {
          setError(`"${file.name}" is too large (max 50KB). Please use a shorter document.`)
          continue
        }
        processed.push({ file, type: 'document' })
      } else {
        setError(`Unsupported file type: ${file.name}. Use images (PNG, JPG, SVG) or text (MD, TXT).`)
      }
    }

    setFiles(prev => [...prev, ...processed])
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    handleFileAdd(e.dataTransfer.files)
  }, [handleFileAdd])

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFileAdd(e.target.files)
    }
  }

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleCreate = async () => {
    setError(null)

    if (!description.trim() && files.length === 0) {
      setError('Please provide a description or upload files to describe your brand.')
      return
    }

    setIsCreating(true)

    try {
      // Convert files to base64
      const images: Array<{ filename: string; data: string }> = []
      const documents: Array<{ filename: string; data: string }> = []

      for (const { file, type } of files) {
        const data = await new Promise<string>((resolve) => {
          const reader = new FileReader()
          reader.onload = () => {
            const result = reader.result as string
            // Extract base64 part from data URL
            const base64 = result.split(',')[1] || result
            resolve(base64)
          }
          reader.readAsDataURL(file)
        })

        if (type === 'image') {
          images.push({ filename: file.name, data })
        } else {
          documents.push({ filename: file.name, data })
        }
      }

      if (isPyWebView()) {
        const result = await bridge.createBrandFromMaterials(description, images, documents)
        onCreated(result.slug)
        onOpenChange(false)
        // Reset state
        setDescription('')
        setFiles([])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create brand')
    } finally {
      setIsCreating(false)
    }
  }

  const handleClose = () => {
    if (!isCreating) {
      onOpenChange(false)
      setDescription('')
      setFiles([])
      setError(null)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="h-5 w-5 text-purple-500" />
            Create New Brand
          </DialogTitle>
          <DialogDescription>
            Upload brand materials and describe your vision. Our AI will create a complete brand identity.
          </DialogDescription>
        </DialogHeader>

        {isCreating ? (
          <div className="py-12 flex flex-col items-center gap-4">
            <Spinner className="h-8 w-8 text-purple-500" />
            <p className="text-sm text-muted-foreground">Creating your brand identity...</p>
            <p className="text-xs text-muted-foreground">This may take a minute as our AI team analyzes your materials.</p>
          </div>
        ) : (
          <>
            {/* Dropzone */}
            <div
              className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                isDragging
                  ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
                  : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
              }`}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
            >
              <Upload className="h-8 w-8 mx-auto mb-2 text-gray-400" />
              <p className="text-sm font-medium mb-1">Drag & drop images or documents</p>
              <p className="text-xs text-muted-foreground mb-3">
                PNG, JPG, SVG, MD, TXT
              </p>
              <label>
                <input
                  type="file"
                  multiple
                  accept={[...ALLOWED_IMAGE_EXTS, ...ALLOWED_DOC_EXTS].join(',')}
                  onChange={handleFileInputChange}
                  className="hidden"
                />
                <Button variant="outline" size="sm" asChild>
                  <span>Browse Files</span>
                </Button>
              </label>
            </div>

            {/* File List */}
            {files.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {files.map((item, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-2 px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded text-sm"
                  >
                    {item.type === 'image' ? (
                      item.dataUrl ? (
                        <img src={item.dataUrl} alt="" className="h-5 w-5 rounded object-cover" />
                      ) : (
                        <Image className="h-4 w-4 text-gray-500" />
                      )
                    ) : (
                      <FileText className="h-4 w-4 text-gray-500" />
                    )}
                    <span className="max-w-[120px] truncate">{item.file.name}</span>
                    <button
                      type="button"
                      onClick={() => removeFile(index)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Description Textarea */}
            <div>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Tell us about your brand... (describe your concept, target audience, values, style preferences)"
                rows={4}
                className="w-full px-3 py-2 text-sm border rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
              />
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
          </>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={isCreating}
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreate}
            disabled={isCreating || (!description.trim() && files.length === 0)}
            className="bg-purple-600 hover:bg-purple-700"
          >
            {isCreating ? 'Creating...' : 'Create Brand'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
