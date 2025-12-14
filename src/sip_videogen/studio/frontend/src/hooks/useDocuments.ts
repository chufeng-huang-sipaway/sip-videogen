import { useCallback, useEffect, useState } from 'react'
import { bridge, isPyWebView, waitForPyWebViewReady, type DocumentEntry } from '@/lib/bridge'

export function useDocuments(brandSlug: string | null) {
  const [documents, setDocuments] = useState<DocumentEntry[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!brandSlug) {
      setDocuments([])
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const ready = await waitForPyWebViewReady()
      if (!ready) {
        setDocuments([
          { name: 'brand-guidelines.md', path: 'brand-guidelines.md', size: 1200 },
          { name: 'tone-of-voice.txt', path: 'tone-of-voice.txt', size: 800 },
        ])
        return
      }

      const docs = await bridge.getDocuments(brandSlug)
      setDocuments(docs)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents')
    } finally {
      setIsLoading(false)
    }
  }, [brandSlug])

  const openInFinder = useCallback(async (path: string) => {
    if (!isPyWebView()) return
    await bridge.openDocumentInFinder(path)
  }, [])

  const readDocument = useCallback(async (path: string) => {
    if (!isPyWebView()) return `[Dev] Preview for ${path} is available in PyWebView only.`
    return bridge.readDocument(path)
  }, [])

  const deleteDocument = useCallback(async (path: string) => {
    if (!isPyWebView()) return
    await bridge.deleteDocument(path)
    await refresh()
  }, [refresh])

  const renameDocument = useCallback(async (path: string, newName: string) => {
    if (!isPyWebView()) return
    await bridge.renameDocument(path, newName)
    await refresh()
  }, [refresh])

  const uploadDocument = useCallback(async (file: File) => {
    if (!isPyWebView()) return

    const reader = new FileReader()
    return new Promise<void>((resolve, reject) => {
      reader.onload = async () => {
        try {
          const base64 = (reader.result as string).split(',')[1]
          await bridge.uploadDocument(file.name, base64)
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

  useEffect(() => {
    refresh()
  }, [refresh])

  return {
    documents,
    isLoading,
    error,
    refresh,
    openInFinder,
    readDocument,
    deleteDocument,
    renameDocument,
    uploadDocument,
  }
}
