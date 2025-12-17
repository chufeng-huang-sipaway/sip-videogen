import { useState, useEffect } from 'react'
import { Package, Plus, X, GripVertical, Star } from 'lucide-react'
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
import { bridge, isPyWebView, type ProductEntry } from '@/lib/bridge'
import { CreateProductDialog } from '../CreateProductDialog'

function ProductThumbnail({ path }: { path: string }) {
  const [src, setSrc] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (!isPyWebView() || !path) return
      try {
        const dataUrl = await bridge.getProductImageThumbnail(path)
        if (!cancelled) setSrc(dataUrl)
      } catch {
        // Ignore thumbnail errors
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [path])

  if (!src) {
    return (
      <div className="h-8 w-8 rounded bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
        <Package className="h-4 w-4 text-gray-400" />
      </div>
    )
  }

  return <img src={src} alt="" className="h-8 w-8 rounded object-cover" />
}

interface ProductCardProps {
  product: ProductEntry
  isAttached: boolean
  onAttach: () => void
  onDetach: () => void
  onDelete: () => void
}

function ProductCard({ product, isAttached, onAttach, onDetach, onDelete }: ProductCardProps) {
  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('application/x-brand-product', product.slug)
    e.dataTransfer.setData('text/plain', product.slug)
    e.dataTransfer.effectAllowed = 'copy'
  }

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>
        <div
          className={`flex items-center gap-2 py-2 px-2 rounded hover:bg-gray-200/50 dark:hover:bg-gray-700/50 cursor-grab active:cursor-grabbing group ${
            isAttached ? 'bg-purple-100/50 dark:bg-purple-900/20 ring-1 ring-purple-500/30' : ''
          }`}
          draggable
          onDragStart={handleDragStart}
          title="Drag to chat to attach, or right-click for options"
        >
          <GripVertical className="h-3 w-3 text-gray-400 opacity-0 group-hover:opacity-100 shrink-0" />
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
        <ContextMenuItem onClick={onDelete} className="text-red-600">
          Delete Product
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
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

  useEffect(() => {
    if (actionError) {
      const timer = setTimeout(() => setActionError(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [actionError])

  const handleDelete = async (slug: string) => {
    if (confirm(`Delete product "${slug}"? This cannot be undone.`)) {
      try {
        await deleteProduct(slug)
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
              onAttach={() => attachProduct(product.slug)}
              onDetach={() => detachProduct(product.slug)}
              onDelete={() => handleDelete(product.slug)}
            />
          ))}
        </div>
      )}

      <CreateProductDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
      />
    </div>
  )
}
