import { useState } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Package, FolderOpen, PanelLeftClose, Brain, Plus, Settings, Palette, ChevronRight } from 'lucide-react'
import { BrandSelector } from './BrandSelector'
import { ProductsSection } from './sections/ProductsSection'
import { TemplatesSection } from './sections/TemplatesSection'
import { ProjectsSection } from './sections/ProjectsSection'
import { CreateProductDialog } from './CreateProductDialog'
import { CreateProjectDialog } from './CreateProjectDialog'
import { SettingsDialog } from '@/components/Settings/SettingsDialog'
import { useBrand } from '@/context/BrandContext'
import { useProducts } from '@/context/ProductContext'
import { useTemplates } from '@/context/TemplateContext'
import { useProjects } from '@/context/ProjectContext'
import { cn } from '@/lib/utils'

const SIDEBAR_EXPANDED_WIDTH = 280 // Reduced from 320 for tighter feel
const SIDEBAR_COLLAPSED_WIDTH = 68

interface SidebarProps {
  collapsed: boolean
  onToggleCollapse: () => void
  onOpenBrandMemory?: () => void
}

type NavSection = 'products' | 'templates' | 'projects' | null

export function Sidebar({ collapsed, onToggleCollapse, onOpenBrandMemory }: SidebarProps) {
  const { activeBrand } = useBrand()
  const { products } = useProducts()
  const { templates } = useTemplates()
  const { projects } = useProjects()

  const [activeSection, setActiveSection] = useState<NavSection>('projects')
  const [isCreateProductOpen, setIsCreateProductOpen] = useState(false)
  const [isCreateTemplateOpen, setIsCreateTemplateOpen] = useState(false)
  const [isCreateProjectOpen, setIsCreateProjectOpen] = useState(false)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)

  const width = collapsed ? SIDEBAR_COLLAPSED_WIDTH : SIDEBAR_EXPANDED_WIDTH

  // Shared function to toggle sections
  const toggleSection = (section: NavSection) => {
    setActiveSection(current => current === section ? null : section)
  }

  const content = collapsed ? (
    <aside
      className="h-screen flex flex-col glass-sidebar flex-shrink-0 transition-all duration-300 ease-in-out z-20"
      style={{ width }}
    >
      <div className="flex-1 flex flex-col items-center py-6 gap-4">
        {/* Compact Brand Selector */}
        <BrandSelector compact />

        {/* Brand Profile Icon */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="w-10 h-10 rounded-2xl bg-white/40 dark:bg-white/10 text-foreground hover:bg-white dark:hover:bg-white/20 hover:shadow-soft transition-all"
              onClick={onOpenBrandMemory}
              disabled={!activeBrand}
            >
              <Brain className="w-5 h-5" strokeWidth={1.5} />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right" className="bg-foreground text-background">
            <p>Brand Profile</p>
          </TooltipContent>
        </Tooltip>

        <Separator className="w-8 bg-black/5 dark:bg-white/5" />

        {/* Nav Icons - same order as expanded: Projects, Products, Style Guides */}
        <div className="flex flex-col gap-3">
          <NavIcon
            icon={<FolderOpen className="w-5 h-5" strokeWidth={1.5} />}
            label={`Projects (${projects.length})`}
            isActive={activeSection === 'projects'}
            onClick={() => { if (activeBrand) onToggleCollapse(); setActiveSection('projects'); }}
            disabled={!activeBrand}
          />
          <NavIcon
            icon={<Package className="w-5 h-5" strokeWidth={1.5} />}
            label={`Products (${products.length})`}
            isActive={activeSection === 'products'}
            onClick={() => { if (activeBrand) onToggleCollapse(); setActiveSection('products'); }}
            disabled={!activeBrand}
          />
          <NavIcon
            icon={<Palette className="w-5 h-5" strokeWidth={1.5} />}
            label={`Style Guides (${templates.length})`}
            isActive={activeSection === 'templates'}
            onClick={() => { if (activeBrand) onToggleCollapse(); setActiveSection('templates'); }}
            disabled={!activeBrand}
          />
        </div>

        <div className="flex-1" />

        {/* Settings Icon */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="w-10 h-10 rounded-2xl text-muted-foreground hover:text-foreground"
              onClick={() => setIsSettingsOpen(true)}
            >
              <Settings className="w-5 h-5" strokeWidth={1.5} />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">Settings</TooltipContent>
        </Tooltip>

        {/* Expand Button */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" className="w-10 h-10 rounded-2xl text-muted-foreground hover:text-foreground" onClick={onToggleCollapse}>
              <PanelLeftClose className="w-5 h-5 rotate-180" strokeWidth={1.5} />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">Expand</TooltipContent>
        </Tooltip>
      </div>

      {/* Settings Dialog for collapsed mode */}
      <SettingsDialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen} />
    </aside>
  ) : (
    <aside
      className="h-screen flex flex-col glass-sidebar flex-shrink-0 transition-all duration-300 ease-in-out z-20 relative"
      style={{ width }}
    >
      {/* Header Area */}
      <div className="px-5 pt-8 pb-4 space-y-4">
        <BrandSelector />

        {/* Minimalist Brand Memory Card */}
        <div
          onClick={activeBrand ? onOpenBrandMemory : undefined}
          className={cn(
            "group flex items-center gap-3 p-3 rounded-2xl border border-transparent bg-white/40 dark:bg-white/10 hover:bg-white/80 dark:hover:bg-white/20 hover:shadow-soft transition-all cursor-pointer",
            !activeBrand && "opacity-50 pointer-events-none"
          )}
        >
          <div className="w-9 h-9 rounded-xl bg-white dark:bg-white/10 flex items-center justify-center shadow-sm border border-black/5 dark:border-white/10 text-foreground group-hover:scale-105 transition-transform">
            <Brain className="w-4.5 h-4.5" strokeWidth={1.5} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-foreground/90">Brand Profile</div>
          </div>
          <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/40 group-hover:text-muted-foreground transition-colors" />
        </div>
      </div>

      <div className="px-6 py-2">
        <Separator className="bg-black/5 dark:bg-white/5" />
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

          {/* Style Guides Section */}
          <NavGroup
            title="Style Guides"
            icon={<Palette className="w-4 h-4" />}
            isOpen={activeSection === 'templates'}
            onToggle={() => toggleSection('templates')}
            onAdd={() => setIsCreateTemplateOpen(true)}
          >
            <TemplatesSection createDialogOpen={isCreateTemplateOpen} onCreateDialogChange={setIsCreateTemplateOpen} />
          </NavGroup>

        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="p-4 border-t border-border/30 flex items-center justify-between gap-2 bg-gradient-to-t from-background/50 to-transparent">
        <Button
          variant="ghost"
          size="sm"
          className="text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-background/60 p-2 h-auto gap-2 rounded-lg"
          onClick={() => setIsSettingsOpen(true)}
        >
          <Settings className="w-3.5 h-3.5" strokeWidth={1.5} />
          <span>Settings</span>
        </Button>
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

  return (
    <TooltipProvider delayDuration={0}>
      {content}
    </TooltipProvider>
  )
}

// Helper Components

function NavIcon({ icon, label, isActive, onClick, disabled }: any) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            "w-10 h-10 rounded-xl transition-all",
            isActive ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground hover:bg-background/60"
          )}
          onClick={onClick}
          disabled={disabled}
        >
          {icon}
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
        <div className="overflow-hidden pb-1">
          {children}
        </div>
      </div>
    </div>
  )
}
