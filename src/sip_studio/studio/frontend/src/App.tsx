import { useCallback, useEffect, useState } from 'react'
import { Sidebar } from '@/components/Sidebar'
import { Workstation } from '@/components/Workstation'
import { ChatPanel } from '@/components/ChatPanel'
import { ApiKeySetup } from '@/components/Setup/ApiKeySetup'
import { UpdateModal } from '@/components/Update'
import { BrandMemory } from '@/components/BrandMemory'
import { CommandPalette } from '@/components/CommandPalette'
import { SettingsDialog } from '@/components/Settings/SettingsDialog'
import { CreateProjectDialog } from '@/components/Sidebar/CreateProjectDialog'
import { Toaster, toast } from '@/components/ui/toaster'
import { TooltipProvider } from '@/components/ui/tooltip'
import { useBrand } from '@/context/BrandContext'
import { DragProvider } from '@/context/DragContext'
import { ViewerProvider } from '@/context/ViewerContext'
import { bridge, waitForPyWebViewReady, fetchAndInitConstants } from '@/lib/bridge'
import type { UpdateCheckResult } from '@/lib/bridge'
import { useTheme } from '@/hooks/useTheme'
import { useWindowFocus } from '@/hooks/useWindowFocus'
import { useWindowResize } from '@/hooks/useWindowResize'

const SIDEBAR_COLLAPSED_KEY = 'sip-studio-sidebar-collapsed'

function App() {
  useTheme()
  useWindowFocus()
  useWindowResize()
  const { activeBrand } = useBrand()
  const [needsSetup, setNeedsSetup] = useState<boolean | null>(null)
  const [updateInfo, setUpdateInfo] = useState<UpdateCheckResult | null>(null)
  const [brandMemoryOpen, setBrandMemoryOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [createProjectOpen, setCreateProjectOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try { const s = localStorage.getItem(SIDEBAR_COLLAPSED_KEY); return s===null?true:s==='true' }
    catch { return true }
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
      //Fetch constants from Python (single source of truth)
      await fetchAndInitConstants()
      //Fetch platform info and set vibrancy attribute
      try{const p=await bridge.getPlatformInfo();document.documentElement.dataset.vibrancy=String(p.vibrancy_enabled)}catch{}
      const status = await bridge.checkApiKeys()
      setNeedsSetup(!status.all_configured)
      //Check for pending research from previous session
      try{
        const jobs=await bridge.getPendingResearch()
        if(jobs.length>0){
          //Notify user about pending research - they can check in chat for status
          toast.info(`${jobs.length} deep research job${jobs.length>1?'s':''} still in progress`,{description:'Open chat to view status',duration:8000})
        }
      }catch{}
    }
    run().catch(() => setNeedsSetup(false))
  }, [])

  if (needsSetup === null) {
    return <div className="min-h-screen flex items-center justify-center">Loading…</div>
  }

  if (needsSetup) {
    return <ApiKeySetup onComplete={() => setNeedsSetup(false)} />
  }

  return (<TooltipProvider><DragProvider><ViewerProvider>
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggleCollapse={toggleSidebar}
        onOpenBrandMemory={() => setBrandMemoryOpen(true)}
      />
      <Workstation />
      <div className="flex-1 max-w-[480px] min-w-[320px] flex-shrink-0"><ChatPanel brandSlug={activeBrand} /></div>
      <BrandMemory open={brandMemoryOpen} onOpenChange={setBrandMemoryOpen} />
      <CommandPalette onNewProject={()=>setCreateProjectOpen(true)} onOpenSettings={()=>setSettingsOpen(true)}/>
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen}/>
      <CreateProjectDialog open={createProjectOpen} onOpenChange={setCreateProjectOpen}/>
      {updateInfo && (<UpdateModal updateInfo={updateInfo} onClose={() => setUpdateInfo(null)} onSkipVersion={handleSkipVersion} />)}
      <Toaster />
    </div></ViewerProvider></DragProvider></TooltipProvider>)
}

export default App
