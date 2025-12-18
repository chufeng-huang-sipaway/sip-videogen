import { useState, useEffect, useMemo } from 'react'
import { Search, Package, Check } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { bridge, isPyWebView, type ProductEntry } from '@/lib/bridge'

interface ProductPickerDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  products: ProductEntry[]
  attachedSlugs: string[]
  onSelect: (slug: string) => void
}

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
      <div className="h-10 w-10 rounded-lg bg-muted flex items-center justify-center shrink-0">
        <Package className="h-5 w-5 text-muted-foreground/50" />
      </div>
    )
  }

  return (
    <img
      src={src}
      alt=""
      className="h-10 w-10 rounded-lg object-cover shrink-0 ring-1 ring-border/20"
    />
  )
}

export function ProductPickerDialog({
  open,
  onOpenChange,
  products,
  attachedSlugs,
  onSelect,
}: ProductPickerDialogProps) {
  const [searchQuery, setSearchQuery] = useState('')

  // Reset search when dialog closes
  useEffect(() => {
    if (!open) {
      setSearchQuery('')
    }
  }, [open])

  const filteredProducts = useMemo(() => {
    if (!searchQuery.trim()) return products
    const query = searchQuery.toLowerCase()
    return products.filter(
      (p) =>
        p.name.toLowerCase().includes(query) ||
        p.description?.toLowerCase().includes(query)
    )
  }, [products, searchQuery])

  const handleSelect = (slug: string) => {
    onSelect(slug)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            Select a Product
          </DialogTitle>
        </DialogHeader>

        {/* Search Input */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search products..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-10 pl-10 pr-4 rounded-lg border border-border bg-background text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/50"
            autoFocus
          />
        </div>

        {/* Product List */}
        <div className="max-h-[300px] overflow-y-auto -mx-2">
          {filteredProducts.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground text-sm">
              {searchQuery ? 'No products match your search' : 'No products available'}
            </div>
          ) : (
            <div className="space-y-1 px-2">
              {filteredProducts.map((product) => {
                const isAttached = attachedSlugs.includes(product.slug)
                return (
                  <button
                    key={product.slug}
                    onClick={() => handleSelect(product.slug)}
                    className={`w-full flex items-center gap-3 p-2 rounded-lg text-left transition-colors ${
                      isAttached
                        ? 'bg-primary/10 hover:bg-primary/15'
                        : 'hover:bg-muted'
                    }`}
                  >
                    <ProductThumbnail path={product.primary_image} />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm truncate">
                        {product.name}
                      </div>
                      {product.description && (
                        <div className="text-xs text-muted-foreground truncate">
                          {product.description}
                        </div>
                      )}
                    </div>
                    {isAttached && (
                      <Check className="h-4 w-4 text-primary shrink-0" />
                    )}
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end pt-2 border-t border-border/40">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
