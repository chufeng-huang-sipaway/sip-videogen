import { useState, useEffect } from 'react'
import { Package, Plus, X, GripVertical, Star, Pencil, ChevronRight, ChevronDown, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from '@/components/ui/context-menu'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useProducts } from '@/context/ProductContext'
import { useBrand } from '@/context/BrandContext'
import { bridge, isPyWebView, type ProductEntry, type ProductFull } from '@/lib/bridge'
import { CreateProductDialog } from '../CreateProductDialog'
import { EditProductDialog } from '../EditProductDialog'

function ProductThumbnail({ path, size = 'sm' }: { path: string; size?: 'sm' | 'lg' }) {
  const [src, setSrc] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (!isPyWebView() || !path) return
      try {
        const dataUrl = size === 'lg'
          ? await bridge.getProductImageFull(path)
          : await bridge.getProductImageThumbnail(path)
        if (!cancelled) setSrc(dataUrl)
      } catch {
        // Ignore thumbnail errors
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [path, size])

  const sizeClasses = size === 'lg' ? 'h-24 w-24' : 'h-8 w-8'

  if (!src) {
    return (
      <div className={`${sizeClasses} rounded bg-gray-200 dark:bg-gray-700 flex items-center justify-center`}>
        {size === 'lg' ? (
          <Loader2 className="h-4 w-4 text-gray-400 animate-spin" />
        ) : (
          <Package className="h-4 w-4 text-gray-400" />
        )}
      </div>
    )
  }

  return <img src={src} alt="" className={`${sizeClasses} rounded object-cover`} />
}

interface ProductPreviewProps {
  productSlug: string
}

function ProductPreview({ productSlug }: ProductPreviewProps) {
  const { getProduct, getProductImages } = useProducts()
  const [product, setProduct] = useState<ProductFull | null>(null)
  const [images, setImages] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setIsLoading(true)
      try {
        const [productData, imagePaths] = await Promise.all([
          getProduct(productSlug),
          getProductImages(productSlug),
        ])
        if (!cancelled) {
          setProduct(productData)
          setImages(imagePaths)
        }
      } catch (err) {
        console.error('Failed to load product preview:', err)
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [productSlug, getProduct, getProductImages])

  if (isLoading) {
    return (
      <div className="py-3 flex items-center gap-2 text-xs text-gray-400">
        <Loader2 className="h-3 w-3 animate-spin" />
        Loading...
      </div>
    )
  }

  if (!product) {
    return (
      <div className="py-2 text-xs text-red-500">
        Failed to load product
      </div>
    )
  }

  return (
    <div className="py-3 space-y-3">
      {/* Image Gallery */}
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {images.map((path, index) => (
            <div
              key={path}
              className={`relative ${path === product.primary_image ? 'ring-2 ring-purple-500 ring-offset-1' : ''}`}
            >
              <ProductThumbnail path={path} size="lg" />
              {path === product.primary_image && (
                <div className="absolute top-1 left-1 bg-purple-500 text-white rounded-full p-0.5">
                  <Star className="h-2.5 w-2.5 fill-current" />
                </div>
              )}
              {index === 0 && images.length > 1 && (
                <span className="absolute bottom-1 right-1 bg-black/60 text-white text-[10px] px-1 rounded">
                  1/{images.length}
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Description */}
      {product.description && (
        <div className="space-y-1">
          <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wide">Description</span>
          <p className="text-xs text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
            {product.description}
          </p>
        </div>
      )}

      {/* Attributes */}
      {product.attributes && product.attributes.length > 0 && (
        <div className="space-y-1">
          <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wide">Attributes</span>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1">
            {product.attributes.map((attr, i) => (
              <div key={i} className="text-xs">
                <span className="text-gray-500">{attr.key}:</span>{' '}
                <span className="text-gray-700 dark:text-gray-200">{attr.value}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Stats */}
      <div className="flex items-center gap-3 text-[10px] text-gray-400 pt-1 border-t border-gray-200 dark:border-gray-700">
        <span>{images.length} image{images.length !== 1 ? 's' : ''}</span>
        {product.attributes && product.attributes.length > 0 && (
          <span>{product.attributes.length} attribute{product.attributes.length !== 1 ? 's' : ''}</span>
        )}
      </div>
    </div>
  )
}

interface ProductCardProps {
  product: ProductEntry
  isAttached: boolean
  isExpanded: boolean
  onToggleExpand: () => void
  onAttach: () => void
  onDetach: () => void
  onEdit: () => void
  onDelete: () => void
}

function ProductCard({
  product,
  isAttached,
  isExpanded,
  onToggleExpand,
  onAttach,
  onDetach,
  onEdit,
  onDelete
}: ProductCardProps) {
  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('application/x-brand-product', product.slug)
    e.dataTransfer.setData('text/plain', product.slug)
    e.dataTransfer.effectAllowed = 'copy'
  }

  const handleClick = (e: React.MouseEvent) => {
    // Don't toggle if dragging
    if (e.defaultPrevented) return
    onToggleExpand()
  }

  return (
    <div>
      <ContextMenu>
        <ContextMenuTrigger asChild>
          <div
            className={`flex items-center gap-2 py-2 px-2 rounded hover:bg-gray-200/50 dark:hover:bg-gray-700/50 cursor-pointer group ${
              isAttached ? 'bg-purple-100/50 dark:bg-purple-900/20 ring-1 ring-purple-500/30' : ''
            }`}
            draggable
            onDragStart={handleDragStart}
            onClick={handleClick}
            title="Click to preview, drag to attach to chat"
          >
            {/* Expand/collapse chevron */}
            {isExpanded ? (
              <ChevronDown className="h-3.5 w-3.5 shrink-0 text-gray-400" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 shrink-0 text-gray-400" />
            )}
            <ProductThumbnail path={product.primary_image} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1">
                <span className="text-sm font-medium truncate">{product.name}</span>
                {isAttached && <Star className="h-3 w-3 text-purple-500 fill-purple-500 shrink-0" />}
              </div>
              <span className="text-xs text-gray-500 truncate block">
                {product.description.length > 40
                  ? product.description.slice(0, 40) + '...'
                  : product.description}
              </span>
            </div>
            <GripVertical className="h-3 w-3 text-gray-400 opacity-0 group-hover:opacity-100 shrink-0" />
          </div>
        </ContextMenuTrigger>
        <ContextMenuContent>
          {isAttached ? (
            <ContextMenuItem onClick={onDetach}>
              Detach from Chat
            </ContextMenuItem>
          ) : (
            <ContextMenuItem onClick={onAttach}>
              Attach to Chat
            </ContextMenuItem>
          )}
          <ContextMenuSeparator />
          <ContextMenuItem onClick={onEdit}>
            <Pencil className="h-4 w-4 mr-2" />
            Edit Product
          </ContextMenuItem>
          <ContextMenuSeparator />
          <ContextMenuItem onClick={onDelete} className="text-red-600">
            Delete Product
          </ContextMenuItem>
        </ContextMenuContent>
      </ContextMenu>

      {/* Expanded preview */}
      {isExpanded && (
        <div className="pl-6 pr-2 border-l-2 border-purple-200 dark:border-purple-800 ml-[7px]">
          <ProductPreview productSlug={product.slug} />
        </div>
      )}
    </div>
  )
}

export function ProductsSection() {
  const { activeBrand } = useBrand()
  const {
    products,
    attachedProducts,
    isLoading,
    error,
    refresh,
    attachProduct,
    detachProduct,
    deleteProduct,
  } = useProducts()
  const [actionError, setActionError] = useState<string | null>(null)
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [editingProductSlug, setEditingProductSlug] = useState<string | null>(null)
  const [expandedProduct, setExpandedProduct] = useState<string | null>(null)

  useEffect(() => {
    if (actionError) {
      const timer = setTimeout(() => setActionError(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [actionError])

  const handleToggleExpand = (slug: string) => {
    setExpandedProduct(prev => prev === slug ? null : slug)
  }

  const handleDelete = async (slug: string) => {
    if (confirm(`Delete product "${slug}"? This cannot be undone.`)) {
      try {
        await deleteProduct(slug)
        // Close expanded view if deleting expanded product
        if (expandedProduct === slug) {
          setExpandedProduct(null)
        }
      } catch (err) {
        setActionError(err instanceof Error ? err.message : 'Failed to delete product')
      }
    }
  }

  if (!activeBrand) {
    return <div className="text-sm text-gray-500">Select a brand</div>
  }

  if (error) {
    return (
      <div className="text-sm text-red-500">
        Error: {error}
        <Button variant="ghost" size="sm" onClick={refresh}>
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500">
          {products.length} product{products.length !== 1 ? 's' : ''}
          {attachedProducts.length > 0 && ` (${attachedProducts.length} attached)`}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0"
          onClick={() => setIsCreateDialogOpen(true)}
          title="Add product"
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {actionError && (
        <Alert variant="destructive" className="py-2 px-3">
          <AlertDescription className="flex items-center justify-between text-xs">
            <span>{actionError}</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-4 w-4 shrink-0"
              onClick={() => setActionError(null)}
            >
              <X className="h-3 w-3" />
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {products.length === 0 ? (
        <p className="text-sm text-gray-400 italic">
          {isLoading ? 'Loading...' : 'No products yet. Click + to add one.'}
        </p>
      ) : (
        <div className="space-y-1">
          {products.map((product) => (
            <ProductCard
              key={product.slug}
              product={product}
              isAttached={attachedProducts.includes(product.slug)}
              isExpanded={expandedProduct === product.slug}
              onToggleExpand={() => handleToggleExpand(product.slug)}
              onAttach={() => attachProduct(product.slug)}
              onDetach={() => detachProduct(product.slug)}
              onEdit={() => setEditingProductSlug(product.slug)}
              onDelete={() => handleDelete(product.slug)}
            />
          ))}
        </div>
      )}

      <CreateProductDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
      />

      {editingProductSlug && (
        <EditProductDialog
          open={!!editingProductSlug}
          onOpenChange={(open) => {
            if (!open) setEditingProductSlug(null)
          }}
          productSlug={editingProductSlug}
        />
      )}
    </div>
  )
}
