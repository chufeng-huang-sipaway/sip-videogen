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
      <div className="h-8 w-8 rounded bg-gray-200 dark:bg-gray-700 flex items-center justify-center shrink-0">
        <Package className="h-4 w-4 text-gray-400" />
      </div>
    )
  }

  return <img src={src} alt="" className="h-8 w-8 rounded object-cover shrink-0" />
}

export function AttachedProducts({ products, attachedSlugs, onDetach }: AttachedProductsProps) {
  if (attachedSlugs.length === 0) return null

  const attachedProducts = products.filter(p => attachedSlugs.includes(p.slug))

  return (
    <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-800 bg-purple-50/50 dark:bg-purple-900/10">
      <div className="flex items-center gap-2 text-xs text-purple-600 dark:text-purple-400 mb-1">
        <Package className="h-3 w-3" />
        <span>Products attached to chat</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {attachedProducts.map((product) => (
          <div
            key={product.slug}
            className="flex items-center gap-2 rounded-lg border border-purple-200 dark:border-purple-800 bg-white dark:bg-gray-800 px-2 py-1"
          >
            <ProductThumbnail path={product.primary_image} />
            <div className="text-xs max-w-[120px] truncate">{product.name}</div>
            <button
              type="button"
              className="text-purple-400 hover:text-purple-600 dark:hover:text-purple-300"
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
              className="flex items-center gap-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-2 py-1 opacity-50"
            >
              <div className="h-8 w-8 rounded bg-gray-200 dark:bg-gray-700 flex items-center justify-center shrink-0">
                <Package className="h-4 w-4 text-gray-400" />
              </div>
              <div className="text-xs max-w-[120px] truncate">{slug}</div>
              <button
                type="button"
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
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
