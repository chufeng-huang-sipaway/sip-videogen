import { useState, useEffect } from 'react'
import { Package, X, Star, Pencil, ChevronRight, ChevronDown, Loader2 } from 'lucide-react'
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
      <div className={`${sizeClasses} rounded bg-gray-200 dark:bg-gray-700 flex items-center justify-center shrink-0`}>
        {size === 'lg' ? (
          <Loader2 className="h-4 w-4 text-gray-400 animate-spin" />
        ) : (
          <Package className="h-4 w-4 text-gray-400" />
        )}
      </div>
    )
  }

  return <img src={src} alt="" className={`${sizeClasses} rounded object-cover shrink-0`} />
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
              className={`relative rounded-md overflow-hidden ${path === product.primary_image ? 'ring-2 ring-primary ring-offset-2' : 'ring-1 ring-border/50'}`}
            >
              <ProductThumbnail path={path} size="lg" />
              {path === product.primary_image && (
                <div className="absolute top-1 left-1 bg-primary text-primary-foreground rounded-full p-0.5 shadow-sm">
                  <Star className="h-2.5 w-2.5 fill-current" />
                </div>
              )}
              {index === 0 && images.length > 1 && (
                <span className="absolute bottom-1 right-1 bg-black/60 text-white text-[10px] px-1.5 py-0.5 rounded backdrop-blur-sm">
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

      {/* Quick Stats */}
      <div className="flex items-center gap-3 text-[10px] text-gray-400 pt-1 border-t border-gray-200 dark:border-gray-700">
        <span>{images.length} image{images.length !== 1 ? 's' : ''}</span>
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
    e.dataTransfer.setData('text/plain', product.slug)
    try { e.dataTransfer.setData('application/x-brand-product', product.slug) } catch { /* ignore */ }
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
            className={`flex items-center gap-2.5 py-2 px-2.5 rounded-lg border border-transparent hover:bg-accent/50 cursor-pointer group overflow-hidden transition-all duration-200 ${isAttached
              ? 'bg-secondary/50 border-input shadow-sm'
              : ''
              }`}
            draggable
            onDragStart={handleDragStart}
            onClick={handleClick}
            title="Click to preview, drag to attach to chat"
          >
            {/* Expand/collapse chevron */}
            {isExpanded ? (
              <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70 group-hover:text-foreground/80 transition-colors" />
            )}
            <ProductThumbnail path={product.primary_image} />
            <div className="flex-1 min-w-0 overflow-hidden">
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-medium truncate text-foreground/90">{product.name}</span>
              </div>
              <span className="text-xs text-muted-foreground truncate block">
                {product.description.length > 40
                  ? product.description.slice(0, 40) + '...'
                  : product.description}
              </span>
            </div>
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
        <div className="pl-6 pr-2 border-l-2 border-border/50 ml-[11px] mt-1 relative">
          {/* Connecting line dot */}
          <div className="absolute top-0 -left-[5px] w-2 h-2 rounded-full bg-border/50"></div>
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
    <div className="space-y-2 pl-2 pr-1">
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
