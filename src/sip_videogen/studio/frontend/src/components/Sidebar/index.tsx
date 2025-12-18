import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Package, FolderOpen, Sparkles, PanelLeftClose, PanelLeft, Brain } from 'lucide-react'
import { BrandSelector } from './BrandSelector'
import { BrandBrainCard } from './BrandBrainCard'
import { ProductsSection } from './sections/ProductsSection'
import { ProjectsSection } from './sections/ProjectsSection'
import { useBrand } from '@/context/BrandContext'
import { useProducts } from '@/context/ProductContext'
import { useProjects } from '@/context/ProjectContext'

const SIDEBAR_EXPANDED_WIDTH = 320
const SIDEBAR_COLLAPSED_WIDTH = 64

interface SidebarProps {
  collapsed: boolean
  onToggleCollapse: () => void
  onOpenBrandMemory?: () => void
}

export function Sidebar({ collapsed, onToggleCollapse, onOpenBrandMemory }: SidebarProps) {
  const { activeBrand } = useBrand()
  const { products } = useProducts()
  const { projects } = useProjects()

  const width = collapsed ? SIDEBAR_COLLAPSED_WIDTH : SIDEBAR_EXPANDED_WIDTH

  // Collapsed view - icon rail
  if (collapsed) {
    return (
      <TooltipProvider delayDuration={0}>
        <aside
          className="h-screen flex flex-col glass-sidebar border-r border-border/50 flex-shrink-0 transition-all duration-300 ease-in-out"
          style={{ width }}
        >
          {/* Logo */}
          <div className="p-3 flex justify-center">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 ring-1 ring-white/20">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
          </div>

          <Separator className="mx-3 bg-border/40" />

          {/* Icon buttons */}
          <div className="flex-1 flex flex-col items-center py-4 gap-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="w-10 h-10 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  onClick={onOpenBrandMemory}
                  disabled={!activeBrand}
                >
                  <Brain className="w-5 h-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">
                <p>Brand Memory</p>
              </TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="w-10 h-10 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/50 relative"
                  disabled={!activeBrand}
                  onClick={() => {
                    if (activeBrand) onToggleCollapse()
                  }}
                >
                  <Package className="w-5 h-5" />
                  {products.length > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-primary text-[10px] font-medium text-primary-foreground flex items-center justify-center">
                      {products.length}
                    </span>
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">
                <p>Products ({products.length})</p>
              </TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="w-10 h-10 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/50 relative"
                  disabled={!activeBrand}
                  onClick={() => {
                    if (activeBrand) onToggleCollapse()
                  }}
                >
                  <FolderOpen className="w-5 h-5" />
                  {projects.length > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-primary text-[10px] font-medium text-primary-foreground flex items-center justify-center">
                      {projects.length}
                    </span>
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">
                <p>Projects ({projects.length})</p>
              </TooltipContent>
            </Tooltip>

            {/* Spacer to push expand button to bottom */}
            <div className="flex-1" />

            {/* Expand button */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="w-10 h-10 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  onClick={onToggleCollapse}
                >
                  <PanelLeft className="w-5 h-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">
                <p>Expand sidebar</p>
              </TooltipContent>
            </Tooltip>
          </div>
        </aside>
      </TooltipProvider>
    )
  }

  // Expanded view - full sidebar
  return (
    <aside
      className="h-screen flex flex-col glass-sidebar border-r border-border/50 flex-shrink-0 transition-all duration-300 ease-in-out"
      style={{ width }}
    >
      {/* Header */}
      <div className="p-5 flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 ring-1 ring-white/20">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-base font-bold tracking-tight text-foreground">Brand Studio</h1>
          <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">AI Workspace</p>
        </div>
      </div>

      <div className="px-4 pb-4">
        <BrandSelector />
      </div>

      <BrandBrainCard onOpenBrandMemory={onOpenBrandMemory ?? (() => { })} />

      <div className="px-4 py-2">
        <Separator className="bg-border/60" />
      </div>

      <ScrollArea className="flex-1">
        <div className="px-3 py-2">
          <Accordion type="multiple" defaultValue={["products", "projects"]} className="space-y-1">
            <AccordionItem value="products" className="border-none mb-1">
              <AccordionTrigger className="px-3 py-2 hover:bg-muted/50 rounded-lg hover:no-underline transition-all [&[data-state=open]>div>svg]:rotate-90 group opacity-80 hover:opacity-100">
                <div className="flex items-center gap-3 text-left">
                  <Package className="w-4 h-4 text-muted-foreground/70" />
                  <div className="flex flex-col">
                    <span className="font-medium text-sm text-foreground/80 leading-snug">Products</span>
                    <span className="text-[10px] text-muted-foreground/60 font-normal">Context for generation</span>
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-3 pb-2 pt-1 ml-2 mt-1">
                <ProductsSection />
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="projects" className="border-none mb-1">
              <AccordionTrigger className="px-3 py-2 hover:bg-muted/50 rounded-lg hover:no-underline transition-all [&[data-state=open]>div>svg]:rotate-90 group opacity-80 hover:opacity-100">
                <div className="flex items-center gap-3 text-left">
                  <FolderOpen className="w-4 h-4 text-muted-foreground/70" />
                  <div className="flex flex-col">
                    <span className="font-medium text-sm text-foreground/80 leading-snug">Projects</span>
                    <span className="text-[10px] text-muted-foreground/60 font-normal">Organize your work</span>
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-3 pb-2 pt-1 ml-2 mt-1">
                <ProjectsSection />
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      </ScrollArea>

      {/* Collapse button at bottom */}
      <div className="p-3 border-t border-border/40">
        <Button
          variant="ghost"
          size="sm"
          className="w-full h-10 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/50 gap-2"
          onClick={onToggleCollapse}
        >
          <PanelLeftClose className="w-4 h-4" />
          <span className="text-sm">Collapse</span>
        </Button>
      </div>
    </aside>
  )
}
