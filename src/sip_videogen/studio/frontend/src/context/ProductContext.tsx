/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { bridge, waitForPyWebViewReady, type ProductEntry, type ProductFull, type ProductAttribute } from '@/lib/bridge'
import { useBrand } from './BrandContext'

export interface CreateProductInput {
  name: string
  description: string
  images?: Array<{ filename: string; data: string }>
  attributes?: ProductAttribute[]
}

interface ProductContextType {
  products: ProductEntry[]
  attachedProducts: string[] // Frontend-only state - passed to bridge.chat() each call
  isLoading: boolean
  error: string | null
  refresh: () => Promise<void>
  attachProduct: (slug: string) => void
  detachProduct: (slug: string) => void
  clearAttachments: () => void // Called on New Chat
  createProduct: (data: CreateProductInput) => Promise<string>
  updateProduct: (
    productSlug: string,
    name?: string,
    description?: string,
    attributes?: ProductAttribute[]
  ) => Promise<void>
  deleteProduct: (slug: string) => Promise<void>
  getProduct: (slug: string) => Promise<ProductFull>
  getProductImages: (slug: string) => Promise<string[]>
  uploadProductImage: (slug: string, filename: string, dataBase64: string) => Promise<string>
  deleteProductImage: (slug: string, filename: string) => Promise<void>
  setPrimaryProductImage: (slug: string, filename: string) => Promise<void>
}

const ProductContext = createContext<ProductContextType | null>(null)

export function ProductProvider({ children }: { children: ReactNode }) {
  const { activeBrand } = useBrand()
  const [products, setProducts] = useState<ProductEntry[]>([])
  const [attachedProducts, setAttachedProducts] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!activeBrand) {
      setProducts([])
      return
    }

    setIsLoading(true)
    setError(null)
    try {
      const ready = await waitForPyWebViewReady()
      if (!ready) {
        // Mock data for dev
        setProducts([
          {
            slug: 'night-cream',
            name: 'Night Cream',
            description: 'Revitalizing night cream for all skin types',
            primary_image: 'products/night-cream/images/main.png',
            attribute_count: 3,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ])
        return
      }
      const result = await bridge.getProducts()
      setProducts(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load products')
    } finally {
      setIsLoading(false)
    }
  }, [activeBrand])

  // Refresh when brand changes
  useEffect(() => {
    refresh()
    // Clear attachments when brand changes
    setAttachedProducts([])
  }, [refresh])

  const attachProduct = useCallback((slug: string) => {
    setAttachedProducts(prev => {
      if (prev.includes(slug)) return prev
      return [...prev, slug]
    })
  }, [])

  const detachProduct = useCallback((slug: string) => {
    setAttachedProducts(prev => prev.filter(s => s !== slug))
  }, [])

  const clearAttachments = useCallback(() => {
    setAttachedProducts([])
  }, [])

  const createProduct = useCallback(async (data: CreateProductInput): Promise<string> => {
    const ready = await waitForPyWebViewReady()
    if (!ready) {
      throw new Error('Not running in PyWebView')
    }
    const slug = await bridge.createProduct(data.name, data.description, data.images, data.attributes)
    await refresh()
    return slug
  }, [refresh])

  const updateProduct = useCallback(async (
    productSlug: string,
    name?: string,
    description?: string,
    attributes?: ProductAttribute[]
  ): Promise<void> => {
    const ready = await waitForPyWebViewReady()
    if (!ready) {
      throw new Error('Not running in PyWebView')
    }
    await bridge.updateProduct(productSlug, name, description, attributes)
    await refresh()
  }, [refresh])

  const deleteProduct = useCallback(async (slug: string): Promise<void> => {
    const ready = await waitForPyWebViewReady()
    if (!ready) {
      throw new Error('Not running in PyWebView')
    }
    await bridge.deleteProduct(slug)
    // Remove from attachments if attached
    setAttachedProducts(prev => prev.filter(s => s !== slug))
    await refresh()
  }, [refresh])

  const getProduct = useCallback(async (slug: string): Promise<ProductFull> => {
    const ready = await waitForPyWebViewReady()
    if (!ready) {
      throw new Error('Not running in PyWebView')
    }
    return bridge.getProduct(slug)
  }, [])

  const getProductImages = useCallback(async (slug: string): Promise<string[]> => {
    const ready = await waitForPyWebViewReady()
    if (!ready) {
      throw new Error('Not running in PyWebView')
    }
    return bridge.getProductImages(slug)
  }, [])

  const uploadProductImage = useCallback(async (slug: string, filename: string, dataBase64: string): Promise<string> => {
    const ready = await waitForPyWebViewReady()
    if (!ready) {
      throw new Error('Not running in PyWebView')
    }
    const path = await bridge.uploadProductImage(slug, filename, dataBase64)
    await refresh()
    return path
  }, [refresh])

  const deleteProductImage = useCallback(async (slug: string, filename: string): Promise<void> => {
    const ready = await waitForPyWebViewReady()
    if (!ready) {
      throw new Error('Not running in PyWebView')
    }
    await bridge.deleteProductImage(slug, filename)
    await refresh()
  }, [refresh])

  const setPrimaryProductImage = useCallback(async (slug: string, filename: string): Promise<void> => {
    const ready = await waitForPyWebViewReady()
    if (!ready) {
      throw new Error('Not running in PyWebView')
    }
    await bridge.setPrimaryProductImage(slug, filename)
    await refresh()
  }, [refresh])

  return (
    <ProductContext.Provider
      value={{
        products,
        attachedProducts,
        isLoading,
        error,
        refresh,
        attachProduct,
        detachProduct,
        clearAttachments,
        createProduct,
        updateProduct,
        deleteProduct,
        getProduct,
        getProductImages,
        uploadProductImage,
        deleteProductImage,
        setPrimaryProductImage,
      }}
    >
      {children}
    </ProductContext.Provider>
  )
}

export function useProducts() {
  const context = useContext(ProductContext)
  if (!context) {
    throw new Error('useProducts must be used within a ProductProvider')
  }
  return context
}
