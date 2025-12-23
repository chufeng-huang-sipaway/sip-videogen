import { useState } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import {Tooltip,TooltipContent,TooltipProvider,TooltipTrigger,} from '@/components/ui/tooltip'
import {Accordion,AccordionContent,AccordionItem,AccordionTrigger,} from '@/components/ui/accordion'
import { Package, FolderOpen, PanelLeftClose, PanelLeft, Brain, Plus, Settings, Layout } from 'lucide-react'
import { BrandSelector } from './BrandSelector'
import { BrandBrainCard } from './BrandBrainCard'
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
  const { templates } = useTemplates()
  const { projects } = useProjects()
  const [isCreateProductOpen, setIsCreateProductOpen] = useState(false)
  const [isCreateProjectOpen, setIsCreateProjectOpen] = useState(false)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)

  const width = collapsed ? SIDEBAR_COLLAPSED_WIDTH : SIDEBAR_EXPANDED_WIDTH

  // Collapsed view - icon rail
  if (collapsed) {
    return (
      <TooltipProvider delayDuration={0}>
        <aside
          className="h-screen flex flex-col glass-sidebar border-r border-border/50 flex-shrink-0 transition-all duration-300 ease-in-out"
          style={{ width }}
        >
          {/* Icon buttons */}
          <div className="flex-1 flex flex-col items-center pt-4 pb-4 gap-2">
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
                <Button variant="ghost" size="icon" className="w-10 h-10 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/50 relative" disabled={!activeBrand} onClick={()=>{if(activeBrand)onToggleCollapse()}}>
                  <Layout className="w-5 h-5"/>
                  {templates.length>0&&(<span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-primary text-[10px] font-medium text-primary-foreground flex items-center justify-center">{templates.length}</span>)}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right"><p>Templates ({templates.length})</p></TooltipContent>
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

            {/* Spacer to push buttons to bottom */}
            <div className="flex-1" />
            {/* Settings button */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" className="w-10 h-10 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/50" onClick={()=>setIsSettingsOpen(true)}>
                  <Settings className="w-5 h-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right"><p>Settings</p></TooltipContent>
            </Tooltip>
            {/* Expand button */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" className="w-10 h-10 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/50" onClick={onToggleCollapse}>
                  <PanelLeft className="w-5 h-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right"><p>Expand sidebar</p></TooltipContent>
            </Tooltip>
          </div>
          <SettingsDialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen}/>
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
      <div className="px-4 pt-4 pb-4">
        <BrandSelector />
      </div>

      <BrandBrainCard onOpenBrandMemory={onOpenBrandMemory ?? (() => { })} />

      <div className="px-4 py-2">
        <Separator className="bg-border/60" />
      </div>

      <ScrollArea className="flex-1">
        <div className="px-3 py-2">
          <Accordion type="multiple" defaultValue={["products","templates","projects"]} className="space-y-1">
            <AccordionItem value="products" className="border-none mb-1">
              <div className="flex items-center gap-1">
                <AccordionTrigger className="flex-1 px-3 py-2 hover:bg-muted/50 rounded-lg hover:no-underline transition-all [&[data-state=open]>div>svg]:rotate-90 group opacity-80 hover:opacity-100">
                  <div className="flex items-center gap-3 text-left">
                    <Package className="w-4 h-4 text-muted-foreground/70" />
                    <div className="flex flex-col">
                      <span className="font-medium text-sm text-foreground/80 leading-snug">Products</span>
                      <span className="text-[10px] text-muted-foreground/60 font-normal">Context for generation</span>
                    </div>
                  </div>
                </AccordionTrigger>
                <Button variant="ghost" size="sm" className="h-7 w-7 p-0 rounded-md hover:bg-muted/50" onClick={()=>setIsCreateProductOpen(true)} title="Add product"><Plus className="h-4 w-4"/></Button>
              </div>
              <AccordionContent className="px-0 pb-1 pt-0">
                <ProductsSection />
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="templates" className="border-none mb-1">
              <div className="flex items-center gap-1">
                <AccordionTrigger className="flex-1 px-3 py-2 hover:bg-muted/50 rounded-lg hover:no-underline transition-all [&[data-state=open]>div>svg]:rotate-90 group opacity-80 hover:opacity-100">
                  <div className="flex items-center gap-3 text-left">
                    <Layout className="w-4 h-4 text-muted-foreground/70"/>
                    <div className="flex flex-col">
                      <span className="font-medium text-sm text-foreground/80 leading-snug">Templates</span>
                      <span className="text-[10px] text-muted-foreground/60 font-normal">Reusable layouts</span>
                    </div>
                  </div>
                </AccordionTrigger>
              </div>
              <AccordionContent className="px-0 pb-1 pt-0">
                <TemplatesSection/>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="projects" className="border-none mb-1">
              <div className="flex items-center gap-1">
                <AccordionTrigger className="flex-1 px-3 py-2 hover:bg-muted/50 rounded-lg hover:no-underline transition-all [&[data-state=open]>div>svg]:rotate-90 group opacity-80 hover:opacity-100">
                  <div className="flex items-center gap-3 text-left">
                    <FolderOpen className="w-4 h-4 text-muted-foreground/70" />
                    <div className="flex flex-col">
                      <span className="font-medium text-sm text-foreground/80 leading-snug">Projects</span>
                      <span className="text-[10px] text-muted-foreground/60 font-normal">Organize your work</span>
                    </div>
                  </div>
                </AccordionTrigger>
                <Button variant="ghost" size="sm" className="h-7 w-7 p-0 rounded-md hover:bg-muted/50" onClick={()=>setIsCreateProjectOpen(true)} title="Add project"><Plus className="h-4 w-4"/></Button>
              </div>
              <AccordionContent className="px-0 pb-1 pt-0">
                <ProjectsSection />
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      </ScrollArea>

      {/* Bottom buttons */}
      <div className="p-3 border-t border-border/40 flex gap-2">
        <Button variant="ghost" size="sm" className="flex-1 h-10 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/50 gap-2" onClick={onToggleCollapse}>
          <PanelLeftClose className="w-4 h-4" /><span className="text-sm">Collapse</span>
        </Button>
        <Button variant="ghost" size="sm" className="h-10 w-10 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/50" onClick={()=>setIsSettingsOpen(true)} title="Settings">
          <Settings className="w-4 h-4" />
        </Button>
      </div>
      <CreateProductDialog open={isCreateProductOpen} onOpenChange={setIsCreateProductOpen}/>
      <CreateProjectDialog open={isCreateProjectOpen} onOpenChange={setIsCreateProjectOpen}/>
      <SettingsDialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen}/>
    </aside>
  )
}
