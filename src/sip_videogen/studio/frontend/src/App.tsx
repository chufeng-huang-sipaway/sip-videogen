import { useEffect, useState } from 'react'
import { Sidebar } from '@/components/Sidebar'
import { ChatPanel } from '@/components/ChatPanel'
import { ApiKeySetup } from '@/components/Setup/ApiKeySetup'
import { useBrand } from '@/context/BrandContext'
import { bridge, waitForPyWebViewReady } from '@/lib/bridge'
import { useTheme } from '@/hooks/useTheme'

function App() {
  useTheme()
  const { activeBrand } = useBrand()
  const [needsSetup, setNeedsSetup] = useState<boolean | null>(null)

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
      <Sidebar />
      <ChatPanel brandSlug={activeBrand} />
    </div>
  )
}

export default App
