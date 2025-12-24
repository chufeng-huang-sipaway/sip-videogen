import { useState } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Package, FolderOpen, PanelLeftClose, Brain, Plus, Settings, Layout, ChevronRight, Heart, Trash2 } from 'lucide-react'
import { BrandSelector } from './BrandSelector'
import { ProductsSection } from './sections/ProductsSection'
import { TemplatesSection } from './sections/TemplatesSection'
import { ProjectsSection } from './sections/ProjectsSection'
import { KeptSection } from './sections/KeptSection'
import { CreateProductDialog } from './CreateProductDialog'
import { CreateProjectDialog } from './CreateProjectDialog'
import { SettingsDialog } from '@/components/Settings/SettingsDialog'
import { useBrand } from '@/context/BrandContext'
import { useProducts } from '@/context/ProductContext'
import { useTemplates } from '@/context/TemplateContext'
import { useProjects } from '@/context/ProjectContext'
import { useWorkstation } from '@/context/WorkstationContext'
import { cn } from '@/lib/utils'
import { bridge, isPyWebView, type ImageStatusEntry } from '@/lib/bridge'

const SIDEBAR_EXPANDED_WIDTH = 280 // Reduced from 320 for tighter feel
const SIDEBAR_COLLAPSED_WIDTH = 68

interface SidebarProps {
  collapsed: boolean
  onToggleCollapse: () => void
  onOpenBrandMemory?: () => void
}

type NavSection = 'products' | 'templates' | 'projects' | 'kept' | null

export function Sidebar({ collapsed, onToggleCollapse, onOpenBrandMemory }: SidebarProps) {
  const { activeBrand } = useBrand()
  const { products } = useProducts()
  const { templates } = useTemplates()
  const { projects } = useProjects()
  const { setCurrentBatch, setSelectedIndex } = useWorkstation()

  const [activeSection, setActiveSection] = useState<NavSection>('projects')
  const [keptCount, setKeptCount] = useState(0)

  //Load kept count when brand changes
  useState(() => {
    if (!activeBrand || !isPyWebView()) return
    bridge.getImagesByStatus(activeBrand, 'kept').then(imgs => setKeptCount(imgs.length)).catch(() => {})
  })

  //Handle viewing trash in workstation
  const handleOpenTrash = async () => {
    if (!activeBrand || !isPyWebView()) return
    try {
      const trashedImages = await bridge.getImagesByStatus(activeBrand, 'trashed')
      const batch = trashedImages.map((img: ImageStatusEntry) => ({
        id: img.id,
        path: img.currentPath,
        prompt: img.prompt || undefined,
        sourceTemplatePath: img.sourceTemplatePath || undefined,
        timestamp: img.timestamp
      }))
      setCurrentBatch(batch)
      setSelectedIndex(0)
    } catch (err) {
      console.error('Failed to load trash:', err)
    }
  }

  const [isCreateProductOpen, setIsCreateProductOpen] = useState(false)
  const [isCreateTemplateOpen, setIsCreateTemplateOpen] = useState(false)
  const [isCreateProjectOpen, setIsCreateProjectOpen] = useState(false)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)

  const width = collapsed ? SIDEBAR_COLLAPSED_WIDTH : SIDEBAR_EXPANDED_WIDTH

  // Shared function to toggle sections
  const toggleSection = (section: NavSection) => {
    setActiveSection(current => current === section ? null : section)
  }

  // Collapsed view - Icon Rail
  if (collapsed) {
    return (
      <TooltipProvider delayDuration={0}>
        <aside
          className="h-screen flex flex-col glass-sidebar border-r border-border/40 flex-shrink-0 transition-all duration-300 ease-in-out z-20"
          style={{ width }}
        >
          <div className="flex-1 flex flex-col items-center py-6 gap-4">
            {/* Brand Memory Icon */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="w-10 h-10 rounded-xl bg-background/50 text-foreground hover:bg-background shadow-sm hover:shadow-soft transition-all"
                  onClick={onOpenBrandMemory}
                  disabled={!activeBrand}
                >
                  <Brain className="w-5 h-5" strokeWidth={1.5} />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right" className="bg-foreground text-background">
                <p>Brand Memory</p>
              </TooltipContent>
            </Tooltip>

            <Separator className="w-8 bg-border/40" />

            {/* Nav Icons */}
            <div className="flex flex-col gap-2">
              <NavIcon
                icon={<Package className="w-5 h-5" strokeWidth={1.5} />}
                label={`Products (${products.length})`}
                isActive={activeSection === 'products'}
                onClick={() => { if (activeBrand) onToggleCollapse(); setActiveSection('products'); }}
                count={products.length}
                disabled={!activeBrand}
              />
              <NavIcon
                icon={<Layout className="w-5 h-5" strokeWidth={1.5} />}
                label={`Templates (${templates.length})`}
                isActive={activeSection === 'templates'}
                onClick={() => { if (activeBrand) onToggleCollapse(); setActiveSection('templates'); }}
                count={templates.length}
                disabled={!activeBrand}
              />
              <NavIcon
                icon={<FolderOpen className="w-5 h-5" strokeWidth={1.5} />}
                label={`Projects (${projects.length})`}
                isActive={activeSection === 'projects'}
                onClick={() => { if (activeBrand) onToggleCollapse(); setActiveSection('projects'); }}
                count={projects.length}
                disabled={!activeBrand}
              />
              <NavIcon
                icon={<Heart className="w-5 h-5" strokeWidth={1.5} />}
                label={`Kept (${keptCount})`}
                isActive={activeSection === 'kept'}
                onClick={() => { if (activeBrand) onToggleCollapse(); setActiveSection('kept'); }}
                count={keptCount}
                disabled={!activeBrand}
              />
            </div>

            <div className="flex-1" />

            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" className="w-10 h-10 rounded-xl text-muted-foreground hover:text-foreground" onClick={onToggleCollapse}>
                  <PanelLeftClose className="w-5 h-5 rotate-180" strokeWidth={1.5} />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">Expand</TooltipContent>
            </Tooltip>
          </div>
        </aside>
      </TooltipProvider>
    )
  }

  // Expanded View
  return (
    <aside
      className="h-screen flex flex-col glass-sidebar border-r border-border/40 flex-shrink-0 transition-all duration-300 ease-in-out z-20 relative"
      style={{ width }}
    >
      {/* Header Area */}
      <div className="px-5 pt-6 pb-2 space-y-4">
        <BrandSelector />

        {/* Minimalist Brand Memory Card */}
        <div
          onClick={activeBrand ? onOpenBrandMemory : undefined}
          className={cn(
            "group flex items-center gap-3 p-3 rounded-xl border border-transparent bg-background/40 hover:bg-background hover:border-border/30 hover:shadow-soft transition-all cursor-pointer",
            !activeBrand && "opacity-50 pointer-events-none"
          )}
        >
          <div className="w-8 h-8 rounded-lg bg-background flex items-center justify-center shadow-sm border border-border/20 text-foreground group-hover:scale-105 transition-transform">
            <Brain className="w-4 h-4" strokeWidth={1.5} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-foreground/90">Brand Memory</div>
            <div className="text-[10px] text-muted-foreground truncate">Active & Learning</div>
          </div>
          <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/40 group-hover:text-muted-foreground transition-colors" />
        </div>
      </div>

      <div className="px-5 py-2">
        <Separator className="bg-border/30" />
      </div>

      {/* Main Navigation */}
      <ScrollArea className="flex-1 px-3">
        <div className="space-y-1 py-2">

          {/* Projects Section - Default Open often */}
          <NavGroup
            title="Projects"
            icon={<FolderOpen className="w-4 h-4" />}
            isOpen={activeSection === 'projects'}
            onToggle={() => toggleSection('projects')}
            onAdd={() => setIsCreateProjectOpen(true)}
          >
            <ProjectsSection />
          </NavGroup>

          {/* Products Section */}
          <NavGroup
            title="Products"
            icon={<Package className="w-4 h-4" />}
            isOpen={activeSection === 'products'}
            onToggle={() => toggleSection('products')}
            onAdd={() => setIsCreateProductOpen(true)}
          >
            <ProductsSection />
          </NavGroup>

          {/* Templates Section */}
          <NavGroup
            title="Templates"
            icon={<Layout className="w-4 h-4" />}
            isOpen={activeSection === 'templates'}
            onToggle={() => toggleSection('templates')}
            onAdd={() => setIsCreateTemplateOpen(true)}
          >
            <TemplatesSection createDialogOpen={isCreateTemplateOpen} onCreateDialogChange={setIsCreateTemplateOpen} />
          </NavGroup>

          {/* Kept Images Section */}
          <NavGroup
            title="Kept"
            icon={<Heart className="w-4 h-4" />}
            isOpen={activeSection === 'kept'}
            onToggle={() => toggleSection('kept')}
          >
            <KeptSection />
          </NavGroup>

        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="p-4 border-t border-border/30 flex items-center justify-between gap-2 bg-gradient-to-t from-background/50 to-transparent">
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-background/60 p-2 h-auto gap-2 rounded-lg"
            onClick={() => setIsSettingsOpen(true)}
          >
            <Settings className="w-3.5 h-3.5" strokeWidth={1.5} />
            <span>Settings</span>
          </Button>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="w-8 h-8 rounded-lg text-muted-foreground hover:text-foreground"
                onClick={handleOpenTrash}
                disabled={!activeBrand}
              >
                <Trash2 className="w-3.5 h-3.5" strokeWidth={1.5} />
              </Button>
            </TooltipTrigger>
            <TooltipContent>View Trash</TooltipContent>
          </Tooltip>
        </div>

        <Button
          variant="ghost"
          size="icon"
          className="w-8 h-8 rounded-lg text-muted-foreground hover:text-foreground"
          onClick={onToggleCollapse}
        >
          <PanelLeftClose className="w-4 h-4" strokeWidth={1.5} />
        </Button>
      </div>

      <CreateProductDialog open={isCreateProductOpen} onOpenChange={setIsCreateProductOpen} />
      <CreateProjectDialog open={isCreateProjectOpen} onOpenChange={setIsCreateProjectOpen} />
      <SettingsDialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen} />
    </aside>
  )
}

// Helper Components

function NavIcon({ icon, label, isActive, onClick, count, disabled }: any) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            "w-10 h-10 rounded-xl relative transition-all",
            isActive ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground hover:bg-background/60"
          )}
          onClick={onClick}
          disabled={disabled}
        >
          {icon}
          {count > 0 && (
            <span className="absolute top-2 right-2 w-1.5 h-1.5 bg-primary rounded-full" />
          )}
        </Button>
      </TooltipTrigger>
      <TooltipContent side="right" className="bg-foreground text-background">
        <p>{label}</p>
      </TooltipContent>
    </Tooltip>
  )
}

function NavGroup({ title, icon, isOpen, onToggle, onAdd, children }: any) {
  return (
    <div className="mb-2">
      <div className="flex items-center gap-1 group mb-1 px-2">
        <button
          onClick={onToggle}
          className={cn(
            "flex-1 flex items-center gap-3 px-2 py-1.5 rounded-lg text-sm font-medium transition-all duration-200",
            isOpen ? "text-foreground bg-secondary/50" : "text-muted-foreground/80 hover:text-foreground hover:bg-secondary/30"
          )}
        >
          <div className={cn("transition-colors", isOpen ? "text-foreground" : "text-muted-foreground")}>
            {icon}
          </div>
          <span className="flex-1 text-left">{title}</span>
          <ChevronRight className={cn("w-3.5 h-3.5 transition-transform duration-200 opacity-0 group-hover:opacity-50", isOpen && "rotate-90 opacity-100")} />
        </button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 rounded-md opacity-0 group-hover:opacity-100 transition-opacity hover:bg-secondary"
          onClick={(e) => { e.stopPropagation(); onAdd?.(); }}
        >
          <Plus className="w-3.5 h-3.5 text-muted-foreground" />
        </Button>
      </div>

      <div className={cn(
        "grid transition-all duration-200 ease-in-out pl-2",
        isOpen ? "grid-rows-[1fr] opacity-100 mb-4" : "grid-rows-[0fr] opacity-0"
      )}>
        <div className="overflow-hidden">
          {children}
        </div>
      </div>
    </div>
  )
}
