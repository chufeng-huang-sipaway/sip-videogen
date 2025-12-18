/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { bridge, waitForPyWebViewReady, type BrandEntry } from '@/lib/bridge'
import type { BrandIdentityFull } from '@/types/brand-identity'

interface BrandContextType {
  brands: BrandEntry[]
  activeBrand: string | null
  isLoading: boolean
  error: string | null
  selectBrand: (slug: string) => Promise<void>
  refresh: () => Promise<void>
  // Identity state
  identity: BrandIdentityFull | null
  isIdentityLoading: boolean
  identityError: string | null
  refreshIdentity: () => Promise<void>
  setIdentity: (identity: BrandIdentityFull | null) => void
  // AI advisor context
  refreshAdvisorContext: () => Promise<{ success: boolean; message?: string; error?: string }>
}

const BrandContext = createContext<BrandContextType | null>(null)

export function BrandProvider({ children }: { children: ReactNode }) {
  const [brands, setBrands] = useState<BrandEntry[]>([])
  const [activeBrand, setActiveBrand] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Identity state
  const [identity, setIdentity] = useState<BrandIdentityFull | null>(null)
  const [isIdentityLoading, setIsIdentityLoading] = useState(false)
  const [identityError, setIdentityError] = useState<string | null>(null)

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

  // Fetch identity for active brand
  const refreshIdentity = useCallback(async () => {
    const ready = await waitForPyWebViewReady()
    if (!ready) {
      // No identity in dev mode
      setIdentity(null)
      return
    }

    setIsIdentityLoading(true)
    setIdentityError(null)
    try {
      const result = await bridge.getBrandIdentity()
      setIdentity(result)
    } catch (err) {
      setIdentityError(err instanceof Error ? err.message : 'Failed to load brand identity')
      setIdentity(null)
    } finally {
      setIsIdentityLoading(false)
    }
  }, [])

  const selectBrand = useCallback(async (slug: string) => {
    setError(null)
    // Clear identity when switching brands
    setIdentity(null)
    setIdentityError(null)
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

  // Refresh AI advisor context (wraps bridge.refreshBrandMemory)
  // Used by sidebar "Refresh AI Memory" button and Brand Memory UI
  const refreshAdvisorContext = useCallback(async () => {
    try {
      const ready = await waitForPyWebViewReady()
      if (!ready) {
        return { success: false, error: 'Not running in PyWebView' }
      }
      const result = await bridge.refreshBrandMemory()
      return { success: true, message: result.message }
    } catch (err) {
      return { success: false, error: err instanceof Error ? err.message : 'Failed to refresh AI context' }
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return (
    <BrandContext.Provider
      value={{
        brands,
        activeBrand,
        isLoading,
        error,
        selectBrand,
        refresh,
        // Identity state
        identity,
        isIdentityLoading,
        identityError,
        refreshIdentity,
        setIdentity,
        // AI advisor context
        refreshAdvisorContext,
      }}
    >
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
