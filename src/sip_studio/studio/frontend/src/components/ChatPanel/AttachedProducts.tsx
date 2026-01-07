import { useState, useEffect } from 'react'
import { Package, X } from 'lucide-react'
import { bridge, isPyWebView, type ProductEntry } from '@/lib/bridge'

interface AttachedProductsProps {
  products: ProductEntry[]
  attachedSlugs: string[]
  onDetach: (slug: string) => void
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
      <div className="h-8 w-8 rounded bg-muted flex items-center justify-center shrink-0">
        <Package className="h-4 w-4 text-muted-foreground" />
      </div>
    )
  }

  return <img src={src} alt="" className="h-8 w-8 rounded object-cover shrink-0" />
}

export function AttachedProducts({ products, attachedSlugs, onDetach }: AttachedProductsProps) {
  if (attachedSlugs.length === 0) return null

  const attachedProducts = products.filter(p => attachedSlugs.includes(p.slug))

  return (
    <div className="px-4 py-2 border-t border-border/40 bg-muted/40 backdrop-blur-sm">
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground mb-2">
        <Package className="h-3 w-3" />
        <span>Products</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {attachedProducts.map((product) => (
          <div
            key={product.slug}
            className="flex items-center gap-2 rounded-lg border border-border/60 bg-background/80 px-2 py-1 shadow-sm transition-all hover:shadow-md hover:border-border"
          >
            <ProductThumbnail path={product.primary_image} />
            <div className="text-xs max-w-[120px] truncate font-medium">{product.name}</div>
            <button
              type="button"
              className="text-muted-foreground/60 hover:text-destructive transition-colors"
              onClick={() => onDetach(product.slug)}
              title="Remove from chat"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
        {/* Show placeholders for products not found */}
        {attachedSlugs
          .filter(slug => !products.find(p => p.slug === slug))
          .map((slug) => (
            <div
              key={slug}
              className="flex items-center gap-2 rounded-lg border border-dashed border-border/60 bg-muted/50 px-2 py-1"
            >
              <div className="h-8 w-8 rounded bg-muted flex items-center justify-center shrink-0">
                <Package className="h-4 w-4 text-muted-foreground/50" />
              </div>
              <div className="text-xs max-w-[120px] truncate text-muted-foreground">{slug}</div>
              <button
                type="button"
                className="text-muted-foreground/60 hover:text-muted-foreground"
                onClick={() => onDetach(slug)}
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
      </div>
    </div>
  )
}
