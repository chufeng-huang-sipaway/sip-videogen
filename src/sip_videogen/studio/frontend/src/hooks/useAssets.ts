import { useState, useCallback, useEffect } from 'react'
import { bridge, isPyWebView, waitForPyWebViewReady, type AssetNode } from '@/lib/bridge'
import { ASSET_CATEGORIES } from '@/lib/constants'

export function useAssets(brandSlug: string | null) {
  const [tree, setTree] = useState<AssetNode[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!brandSlug) {
      setTree([])
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const ready = await waitForPyWebViewReady()
      if (!ready) {
        //Mock data for dev
        setTree(ASSET_CATEGORIES.map(cat=>({
          name:cat,type:'folder'as const,path:cat,
          children:cat==='logo'?[{name:'primary.png',type:'image'as const,path:'logo/primary.png',size:24000}]:[]
        })))
        return
      }

      const assets = await bridge.getAssets(brandSlug)
      setTree(assets)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load assets')
    } finally {
      setIsLoading(false)
    }
  }, [brandSlug])

  const getThumbnail = useCallback(async (path: string) => {
    if (!isPyWebView()) return null
    try {
      return await bridge.getAssetThumbnail(path)
    } catch {
      return null
    }
  }, [])

  const openInFinder = useCallback(async (path: string) => {
    if (!isPyWebView()) return
    await bridge.openAssetInFinder(path)
  }, [])

  const deleteAsset = useCallback(async (path: string) => {
    if (!isPyWebView()) return
    await bridge.deleteAsset(path)
    await refresh()
  }, [refresh])

  const renameAsset = useCallback(async (path: string, newName: string) => {
    if (!isPyWebView()) return
    await bridge.renameAsset(path, newName)
    await refresh()
  }, [refresh])

  const uploadAsset = useCallback(async (file: File, category: string) => {
    if (!isPyWebView()) return

    const reader = new FileReader()
    return new Promise<void>((resolve, reject) => {
      reader.onload = async () => {
        try {
          const base64 = (reader.result as string).split(',')[1]
          await bridge.uploadAsset(file.name, base64, category)
          await refresh()
          resolve()
        } catch (err) {
          reject(err)
        }
      }
      reader.onerror = () => reject(reader.error)
      reader.readAsDataURL(file)
    })
  }, [refresh])

  const refreshMemory = useCallback(async () => {
    if (!isPyWebView()) return
    await bridge.refreshBrandMemory()
  }, [])

  // Load on mount and when brand changes
  useEffect(() => {
    refresh()
  }, [refresh])

  // Auto-refresh when window gains focus (user switches back to app)
  useEffect(() => {
    const handleFocus = () => {
      refresh()
    }
    window.addEventListener('focus', handleFocus)
    return () => window.removeEventListener('focus', handleFocus)
  }, [refresh])

  return {
    tree,
    isLoading,
    error,
    refresh,
    getThumbnail,
    openInFinder,
    deleteAsset,
    renameAsset,
    uploadAsset,
    refreshMemory,
  }
}
