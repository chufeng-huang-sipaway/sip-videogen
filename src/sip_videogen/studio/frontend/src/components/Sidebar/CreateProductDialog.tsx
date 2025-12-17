import { useState, useCallback } from 'react'
import { Package, Upload, X } from 'lucide-react'
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
import { Input } from '@/components/ui/input'
import { useProducts } from '@/context/ProductContext'

const ALLOWED_IMAGE_EXTS = ['.png', '.jpg', '.jpeg', '.gif', '.webp']

interface UploadedImage {
  file: File
  dataUrl: string
}

interface CreateProductDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated?: (slug: string) => void
}

export function CreateProductDialog({
  open,
  onOpenChange,
  onCreated,
}: CreateProductDialogProps) {
  const { createProduct, refresh } = useProducts()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [images, setImages] = useState<UploadedImage[]>([])
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  const handleFileAdd = useCallback(async (newFiles: FileList | File[]) => {
    const fileArray = Array.from(newFiles)
    const processed: UploadedImage[] = []

    for (const file of fileArray) {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase()

      if (ALLOWED_IMAGE_EXTS.includes(ext)) {
        const dataUrl = await new Promise<string>((resolve) => {
          const reader = new FileReader()
          reader.onload = () => resolve(reader.result as string)
          reader.readAsDataURL(file)
        })
        processed.push({ file, dataUrl })
      } else {
        setError(`Unsupported file type: ${file.name}. Use images (PNG, JPG, GIF, WebP).`)
      }
    }

    setImages(prev => [...prev, ...processed])
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

  const removeImage = (index: number) => {
    setImages(prev => prev.filter((_, i) => i !== index))
  }

  const handleCreate = async () => {
    setError(null)

    if (!name.trim()) {
      setError('Please enter a product name.')
      return
    }

    setIsCreating(true)

    try {
      // Convert images to base64
      const imageData: Array<{ filename: string; data: string }> = []

      for (const { file } of images) {
        const data = await new Promise<string>((resolve) => {
          const reader = new FileReader()
          reader.onload = () => {
            const result = reader.result as string
            const base64 = result.split(',')[1] || result
            resolve(base64)
          }
          reader.readAsDataURL(file)
        })
        imageData.push({ filename: file.name, data })
      }

      const slug = await createProduct({
        name: name.trim(),
        description: description.trim(),
        images: imageData.length > 0 ? imageData : undefined,
      })

      await refresh()
      onCreated?.(slug)
      onOpenChange(false)

      // Reset state
      setName('')
      setDescription('')
      setImages([])
    } catch (err) {
      console.error('[CreateProduct] ERROR:', err)
      setError(err instanceof Error ? err.message : 'Failed to create product')
    } finally {
      setIsCreating(false)
    }
  }

  const handleClose = () => {
    if (!isCreating) {
      onOpenChange(false)
      setName('')
      setDescription('')
      setImages([])
      setError(null)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="h-5 w-5 text-purple-500" />
            Add New Product
          </DialogTitle>
          <DialogDescription>
            Add a product with reference images for AI-powered generation.
          </DialogDescription>
        </DialogHeader>

        {isCreating ? (
          <div className="py-8 flex flex-col items-center gap-3">
            <Spinner className="h-6 w-6 text-purple-500" />
            <p className="text-sm text-muted-foreground">Creating product...</p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Name Input */}
            <div className="space-y-2">
              <label htmlFor="product-name" className="text-sm font-medium">
                Name <span className="text-red-500">*</span>
              </label>
              <Input
                id="product-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Night Cream 50ml"
                autoFocus
              />
            </div>

            {/* Description Input */}
            <div className="space-y-2">
              <label htmlFor="product-description" className="text-sm font-medium">
                Description
              </label>
              <textarea
                id="product-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the product (size, texture, use cases, etc.)"
                rows={3}
                className="w-full px-3 py-2 text-sm border rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
              />
            </div>

            {/* Image Dropzone */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Product Images</label>
              <div
                className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors ${
                  isDragging
                    ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
                    : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
                }`}
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
              >
                <Upload className="h-6 w-6 mx-auto mb-2 text-gray-400" />
                <p className="text-sm mb-2">Drag & drop product images</p>
                <p className="text-xs text-muted-foreground mb-2">
                  PNG, JPG, GIF, WebP
                </p>
                <label>
                  <input
                    type="file"
                    multiple
                    accept={ALLOWED_IMAGE_EXTS.join(',')}
                    onChange={handleFileInputChange}
                    className="hidden"
                  />
                  <Button variant="outline" size="sm" asChild>
                    <span>Browse Files</span>
                  </Button>
                </label>
              </div>
            </div>

            {/* Image Preview List */}
            {images.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {images.map((item, index) => (
                  <div
                    key={index}
                    className="relative group"
                  >
                    <img
                      src={item.dataUrl}
                      alt={item.file.name}
                      className="h-16 w-16 rounded object-cover border"
                    />
                    <button
                      type="button"
                      onClick={() => removeImage(index)}
                      className="absolute -top-1 -right-1 h-5 w-5 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X className="h-3 w-3" />
                    </button>
                    <span className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 truncate rounded-b">
                      {item.file.name}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {images.length === 0 && (
              <p className="text-xs text-muted-foreground">
                Tip: Upload product photos so the AI can use them as reference when generating images.
              </p>
            )}

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
          </div>
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
            disabled={isCreating || !name.trim()}
            className="bg-purple-600 hover:bg-purple-700"
          >
            {isCreating ? 'Creating...' : 'Add Product'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
