import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { bridge, waitForPyWebViewReady, type BrandEntry } from '@/lib/bridge'

interface BrandContextType {
  brands: BrandEntry[]
  activeBrand: string | null
  isLoading: boolean
  error: string | null
  selectBrand: (slug: string) => Promise<void>
  refresh: () => Promise<void>
}

const BrandContext = createContext<BrandContextType | null>(null)

export function BrandProvider({ children }: { children: ReactNode }) {
  const [brands, setBrands] = useState<BrandEntry[]>([])
  const [activeBrand, setActiveBrand] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const ready = await waitForPyWebViewReady()
      if (!ready) {
        // Mock data for dev
        setBrands([
          { slug: 'summit-coffee', name: 'Summit Coffee', category: 'Coffee' },
          { slug: 'acme-corp', name: 'Acme Corp', category: 'Technology' },
        ])
        setActiveBrand('summit-coffee')
        return
      }
      const result = await bridge.getBrands()
      setBrands(result.brands)
      setActiveBrand(result.active)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load brands')
    } finally {
      setIsLoading(false)
    }
  }, [])

  const selectBrand = useCallback(async (slug: string) => {
    setError(null)
    try {
      const ready = await waitForPyWebViewReady()
      if (ready) {
        await bridge.setBrand(slug)
      }
      setActiveBrand(slug)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to select brand')
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return (
    <BrandContext.Provider value={{ brands, activeBrand, isLoading, error, selectBrand, refresh }}>
      {children}
    </BrandContext.Provider>
  )
}

export function useBrand() {
  const context = useContext(BrandContext)
  if (!context) {
    throw new Error('useBrand must be used within a BrandProvider')
  }
  return context
}
