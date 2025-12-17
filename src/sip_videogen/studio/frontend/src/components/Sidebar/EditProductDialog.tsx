import { useState, useEffect, useCallback } from 'react'
import { Package, Upload, X, Star, Loader2 } from 'lucide-react'
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
import { bridge, isPyWebView } from '@/lib/bridge'
import type { ProductFull } from '@/lib/bridge'

const ALLOWED_IMAGE_EXTS = ['.png', '.jpg', '.jpeg', '.gif', '.webp']

interface ExistingImage {
  path: string // brand-relative path like "products/slug/images/main.png"
  filename: string // just the filename
  thumbnailUrl: string | null
  isPrimary: boolean
}

interface NewImage {
  file: File
  dataUrl: string
}

interface EditProductDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  productSlug: string
}

export function EditProductDialog({
  open,
  onOpenChange,
  productSlug,
}: EditProductDialogProps) {
  const {
    getProduct,
    getProductImages,
    updateProduct,
    uploadProductImage,
    deleteProductImage,
    setPrimaryProductImage,
    refresh,
  } = useProducts()

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [existingImages, setExistingImages] = useState<ExistingImage[]>([])
  const [newImages, setNewImages] = useState<NewImage[]>([])
  const [imagesToDelete, setImagesToDelete] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [originalProduct, setOriginalProduct] = useState<ProductFull | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  // Load product data and images when dialog opens
  useEffect(() => {
    if (!open || !productSlug) return

    let cancelled = false

    async function load() {
      setIsLoading(true)
      setError(null)
      setNewImages([])
      setImagesToDelete([])

      try {
        const [product, imagePaths] = await Promise.all([
          getProduct(productSlug),
          getProductImages(productSlug),
        ])

        if (cancelled) return

        setOriginalProduct(product)
        setName(product.name)
        setDescription(product.description)

        // Load thumbnails for existing images
        const images: ExistingImage[] = []
        for (const path of imagePaths) {
          const filename = path.split('/').pop() || path
          let thumbnailUrl: string | null = null

          if (isPyWebView()) {
            try {
              thumbnailUrl = await bridge.getProductImageThumbnail(path)
            } catch {
              // Ignore thumbnail errors
            }
          }

          images.push({
            path,
            filename,
            thumbnailUrl,
            isPrimary: path === product.primary_image,
          })
        }

        if (!cancelled) {
          // Sort so primary image is first
          images.sort((a, b) => (b.isPrimary ? 1 : 0) - (a.isPrimary ? 1 : 0))
          setExistingImages(images)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load product')
        }
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [open, productSlug, getProduct, getProductImages])

  const handleFileAdd = useCallback(async (newFiles: FileList | File[]) => {
    const fileArray = Array.from(newFiles)
    const processed: NewImage[] = []

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

    setNewImages(prev => [...prev, ...processed])
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

  const handleDeleteExisting = (path: string) => {
    setImagesToDelete(prev => [...prev, path])
    setExistingImages(prev => prev.filter(img => img.path !== path))
  }

  const handleDeleteNew = (index: number) => {
    setNewImages(prev => prev.filter((_, i) => i !== index))
  }

  const handleSetPrimary = async (path: string) => {
    // Update UI immediately
    setExistingImages(prev =>
      prev.map(img => ({ ...img, isPrimary: img.path === path }))
        .sort((a, b) => (b.isPrimary ? 1 : 0) - (a.isPrimary ? 1 : 0))
    )
  }

  const handleSave = async () => {
    setError(null)

    if (!name.trim()) {
      setError('Please enter a product name.')
      return
    }

    // Check if at least one image remains
    const remainingExisting = existingImages.filter(img => !imagesToDelete.includes(img.path))
    if (remainingExisting.length === 0 && newImages.length === 0) {
      setError('Product must have at least one image.')
      return
    }

    setIsSaving(true)

    try {
      // 1. Update name and description
      await updateProduct(
        productSlug,
        name.trim(),
        description.trim(),
        originalProduct?.attributes
      )

      // 2. Delete marked images
      for (const path of imagesToDelete) {
        const filename = path.split('/').pop() || ''
        await deleteProductImage(productSlug, filename)
      }

      // 3. Upload new images
      for (const { file } of newImages) {
        const data = await new Promise<string>((resolve) => {
          const reader = new FileReader()
          reader.onload = () => {
            const result = reader.result as string
            const base64 = result.split(',')[1] || result
            resolve(base64)
          }
          reader.readAsDataURL(file)
        })
        await uploadProductImage(productSlug, file.name, data)
      }

      // 4. Set primary image if changed
      const newPrimary = existingImages.find(img => img.isPrimary && !imagesToDelete.includes(img.path))
      if (newPrimary && originalProduct && newPrimary.path !== originalProduct.primary_image) {
        const filename = newPrimary.path.split('/').pop() || ''
        await setPrimaryProductImage(productSlug, filename)
      }

      await refresh()
      onOpenChange(false)
    } catch (err) {
      console.error('[EditProduct] ERROR:', err)
      setError(err instanceof Error ? err.message : 'Failed to update product')
    } finally {
      setIsSaving(false)
    }
  }

  const handleClose = () => {
    if (!isSaving) {
      onOpenChange(false)
      setError(null)
    }
  }

  const hasChanges = originalProduct && (
    name.trim() !== originalProduct.name ||
    description.trim() !== originalProduct.description ||
    newImages.length > 0 ||
    imagesToDelete.length > 0 ||
    existingImages.some(img => img.isPrimary && img.path !== originalProduct.primary_image)
  )

  const visibleExistingImages = existingImages.filter(img => !imagesToDelete.includes(img.path))

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="h-5 w-5 text-purple-500" />
            Edit Product
          </DialogTitle>
          <DialogDescription>
            Update product details and images.
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="py-8 flex flex-col items-center gap-3">
            <Spinner className="h-6 w-6 text-purple-500" />
            <p className="text-sm text-muted-foreground">Loading product...</p>
          </div>
        ) : isSaving ? (
          <div className="py-8 flex flex-col items-center gap-3">
            <Spinner className="h-6 w-6 text-purple-500" />
            <p className="text-sm text-muted-foreground">Saving changes...</p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Name Input */}
            <div className="space-y-2">
              <label htmlFor="edit-product-name" className="text-sm font-medium">
                Name <span className="text-red-500">*</span>
              </label>
              <Input
                id="edit-product-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Night Cream 50ml"
                autoFocus
              />
            </div>

            {/* Description Input */}
            <div className="space-y-2">
              <label htmlFor="edit-product-description" className="text-sm font-medium">
                Description
              </label>
              <textarea
                id="edit-product-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the product (size, texture, use cases, etc.)"
                rows={3}
                className="w-full px-3 py-2 text-sm border rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
              />
            </div>

            {/* Product Images */}
            <div className="space-y-2">
              <label className="text-sm font-medium">
                Product Images <span className="text-red-500">*</span>
              </label>

              {/* Existing Images */}
              {visibleExistingImages.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2">
                  {visibleExistingImages.map((img) => (
                    <div
                      key={img.path}
                      className={`relative group ${
                        img.isPrimary ? 'ring-2 ring-purple-500 ring-offset-2' : ''
                      }`}
                    >
                      {img.thumbnailUrl ? (
                        <img
                          src={img.thumbnailUrl}
                          alt={img.filename}
                          className="h-20 w-20 rounded object-cover border"
                        />
                      ) : (
                        <div className="h-20 w-20 rounded border bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                          <Loader2 className="h-4 w-4 text-gray-400 animate-spin" />
                        </div>
                      )}

                      {/* Primary indicator */}
                      {img.isPrimary && (
                        <div className="absolute top-1 left-1 bg-purple-500 text-white rounded-full p-0.5">
                          <Star className="h-3 w-3 fill-current" />
                        </div>
                      )}

                      {/* Actions overlay */}
                      <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity rounded flex items-center justify-center gap-1">
                        {!img.isPrimary && (
                          <button
                            type="button"
                            onClick={() => handleSetPrimary(img.path)}
                            className="h-6 w-6 bg-purple-500 text-white rounded-full flex items-center justify-center hover:bg-purple-600"
                            title="Set as primary"
                          >
                            <Star className="h-3 w-3" />
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => handleDeleteExisting(img.path)}
                          className="h-6 w-6 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600"
                          title="Delete image"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </div>

                      {/* Filename */}
                      <span className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 truncate rounded-b">
                        {img.filename}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* New Images to upload */}
              {newImages.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2">
                  {newImages.map((item, index) => (
                    <div key={index} className="relative group">
                      <img
                        src={item.dataUrl}
                        alt={item.file.name}
                        className="h-20 w-20 rounded object-cover border border-dashed border-green-500"
                      />
                      <div className="absolute top-1 right-1 bg-green-500 text-white text-[10px] px-1 rounded">
                        NEW
                      </div>
                      <button
                        type="button"
                        onClick={() => handleDeleteNew(index)}
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

              {/* Dropzone for new images */}
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
                <Upload className="h-5 w-5 mx-auto mb-1 text-gray-400" />
                <p className="text-xs mb-1">Drop images to add</p>
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

              <p className="text-xs text-muted-foreground">
                Click the star to set the primary image. The primary image is used as reference for AI generation.
              </p>
            </div>

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
            disabled={isSaving}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={isLoading || isSaving || !name.trim() || !hasChanges}
            className="bg-purple-600 hover:bg-purple-700"
          >
            {isSaving ? 'Saving...' : 'Save Changes'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
