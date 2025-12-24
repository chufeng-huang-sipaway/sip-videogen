import{useCallback,useEffect,useState}from'react'
import{Sidebar}from'@/components/Sidebar'
import{Workstation}from'@/components/Workstation'
import{ChatPanel}from'@/components/ChatPanel'
import{ApiKeySetup}from'@/components/Setup/ApiKeySetup'
import{UpdateModal}from'@/components/Update'
import{BrandMemory}from'@/components/BrandMemory'
import{Toaster}from'@/components/ui/toaster'
import{useBrand}from'@/context/BrandContext'
import{bridge,waitForPyWebViewReady}from'@/lib/bridge'
import type{UpdateCheckResult}from'@/lib/bridge'
import{useTheme}from'@/hooks/useTheme'

const SIDEBAR_COLLAPSED_KEY = 'brand-studio-sidebar-collapsed'

function App() {
  useTheme()
  const { activeBrand } = useBrand()
  const [needsSetup, setNeedsSetup] = useState<boolean | null>(null)
  const [updateInfo, setUpdateInfo] = useState<UpdateCheckResult | null>(null)
  const [brandMemoryOpen, setBrandMemoryOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const saved = localStorage.getItem(SIDEBAR_COLLAPSED_KEY)
    return saved === 'true'
  })

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed(prev => {
      const newValue = !prev
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(newValue))
      return newValue
    })
  }, [])

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
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggleCollapse={toggleSidebar}
        onOpenBrandMemory={() => setBrandMemoryOpen(true)}
      />
      <Workstation />
      <div className="w-[320px] flex-shrink-0"><ChatPanel brandSlug={activeBrand} /></div>

      {/* Brand Memory modal - keeps ChatPanel mounted underneath */}
      <BrandMemory open={brandMemoryOpen} onOpenChange={setBrandMemoryOpen} />

{/* Update notification modal */}
{updateInfo&&(<UpdateModal updateInfo={updateInfo} onClose={()=>setUpdateInfo(null)} onSkipVersion={handleSkipVersion}/>)}
<Toaster/>
</div>)
}

export default App
