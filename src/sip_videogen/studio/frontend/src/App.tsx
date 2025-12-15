import { useCallback, useEffect, useState } from 'react'
import { Sidebar } from '@/components/Sidebar'
import { ChatPanel } from '@/components/ChatPanel'
import { ApiKeySetup } from '@/components/Setup/ApiKeySetup'
import { UpdateModal } from '@/components/Update'
import { ResizeHandle } from '@/components/ui/resize-handle'
import { useBrand } from '@/context/BrandContext'
import { bridge, waitForPyWebViewReady } from '@/lib/bridge'
import type { UpdateCheckResult } from '@/lib/bridge'
import { useTheme } from '@/hooks/useTheme'

const SIDEBAR_MIN_WIDTH = 200
const SIDEBAR_MAX_WIDTH = 500
const SIDEBAR_DEFAULT_WIDTH = 288
const SIDEBAR_WIDTH_KEY = 'brand-studio-sidebar-width'

function App() {
  useTheme()
  const { activeBrand } = useBrand()
  const [needsSetup, setNeedsSetup] = useState<boolean | null>(null)
  const [updateInfo, setUpdateInfo] = useState<UpdateCheckResult | null>(null)
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = localStorage.getItem(SIDEBAR_WIDTH_KEY)
    return saved ? parseInt(saved, 10) : SIDEBAR_DEFAULT_WIDTH
  })

  const handleResize = useCallback((delta: number) => {
    setSidebarWidth(prev => {
      const newWidth = Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, prev + delta))
      return newWidth
    })
  }, [])

  const handleResizeEnd = useCallback(() => {
    localStorage.setItem(SIDEBAR_WIDTH_KEY, String(sidebarWidth))
  }, [sidebarWidth])

  const handleSkipVersion = useCallback(async (version: string) => {
    try {
      await bridge.skipUpdateVersion(version)
    } catch {
      // Ignore errors
    }
  }, [])

  // Check for updates on startup
  useEffect(() => {
    async function checkUpdates() {
      try {
        const ready = await waitForPyWebViewReady()
        if (!ready) return

        // Get settings to check if we should check for updates
        const settings = await bridge.getUpdateSettings()
        if (!settings.check_on_startup) return

        // Check for updates
        const result = await bridge.checkForUpdates()
        if (result.has_update && result.new_version && result.download_url) {
          // Don't show if user skipped this version
          if (settings.skipped_version === result.new_version) return

          setUpdateInfo(result)
        }
      } catch {
        // Silently ignore update check errors
      }
    }

    // Delay update check slightly to not block initial load
    const timer = setTimeout(checkUpdates, 2000)
    return () => clearTimeout(timer)
  }, [])

  useEffect(() => {
    async function run() {
      const ready = await waitForPyWebViewReady()
      if (!ready) {
        setNeedsSetup(false) // Browser dev mode (no PyWebView)
        return
      }
      const status = await bridge.checkApiKeys()
      setNeedsSetup(!status.all_configured)
    }
    run().catch(() => setNeedsSetup(false))
  }, [])

  if (needsSetup === null) {
    return <div className="min-h-screen flex items-center justify-center">Loading…</div>
  }

  if (needsSetup) {
    return <ApiKeySetup onComplete={() => setNeedsSetup(false)} />
  }

  return (
    <div className="flex h-screen bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <Sidebar width={sidebarWidth} />
      <ResizeHandle onResize={handleResize} onResizeEnd={handleResizeEnd} />
      <ChatPanel brandSlug={activeBrand} />

      {/* Update notification modal */}
      {updateInfo && (
        <UpdateModal
          updateInfo={updateInfo}
          onClose={() => setUpdateInfo(null)}
          onSkipVersion={handleSkipVersion}
        />
      )}
    </div>
  )
}

export default App
