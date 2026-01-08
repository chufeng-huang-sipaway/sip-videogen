import { useState, useRef, useEffect } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { PanelLeftClose, Brain, Plus, Settings, Package, Palette, ChevronRight, ChevronDown } from 'lucide-react'
import { BrandSelector } from './BrandSelector'
import { ProjectsSection } from './sections/ProjectsSection'
import { ProductsSection } from './sections/ProductsSection'
import { StyleReferencesSection } from './sections/StyleReferencesSection'
import { CreateProductDialog } from './CreateProductDialog'
import { CreateProjectDialog } from './CreateProjectDialog'
import { SettingsDialog } from '@/components/Settings/SettingsDialog'
import { useBrand } from '@/context/BrandContext'
import { useProducts } from '@/context/ProductContext'
import { useStyleReferences } from '@/context/StyleReferenceContext'
import { useProjects } from '@/context/ProjectContext'
import { cn } from '@/lib/utils'

const SIDEBAR_COLLAPSED_WIDTH = 72

interface SidebarProps { collapsed: boolean; onToggleCollapse: () => void; onOpenBrandMemory?: () => void }

export function Sidebar({ collapsed, onToggleCollapse, onOpenBrandMemory }: SidebarProps) {
  //Hover + focus state for floating sidebar behavior
  const [isHovering, setIsHovering] = useState(false)
  const [isFocusWithin, setIsFocusWithin] = useState(false)
  const collapseTimeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined)
  //Expanded = not collapsed OR hovering OR focus-within (keyboard accessibility)
  const isExpanded = !collapsed || isHovering || isFocusWithin
  const handleMouseEnter = () => { if(collapseTimeoutRef.current) clearTimeout(collapseTimeoutRef.current); setIsHovering(true) }
  const handleMouseLeave = () => { collapseTimeoutRef.current = setTimeout(()=>setIsHovering(false), 200) }
  const handleFocusIn = () => setIsFocusWithin(true)
  const handleFocusOut = (e: React.FocusEvent) => { if(!e.relatedTarget || !e.currentTarget.contains(e.relatedTarget as Node)) setIsFocusWithin(false) }
  useEffect(() => () => { if(collapseTimeoutRef.current) clearTimeout(collapseTimeoutRef.current) }, [])
  const { activeBrand } = useBrand()
  const { products } = useProducts()
  const { styleReferences } = useStyleReferences()
  const { projects } = useProjects()

  // Independent states for sections
  const [projectsOpen, setProjectsOpen] = useState(true)
  const [libraryOpen, setLibraryOpen] = useState(true)

  // Subsection states
  const [productsOpen, setProductsOpen] = useState(true)
  const [styleRefsOpen, setStyleRefsOpen] = useState(true)

  const [isCreateProductOpen, setIsCreateProductOpen] = useState(false)
  const [isCreateStyleRefOpen, setIsCreateStyleRefOpen] = useState(false)
  const [isCreateProjectOpen, setIsCreateProjectOpen] = useState(false)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)

  //Wrapper approach: outer div fixed at 72px, inner aside absolute positioned for overlay
  return (
    <TooltipProvider delayDuration={300}>
      <div className="relative flex-shrink-0 h-full" style={{width: SIDEBAR_COLLAPSED_WIDTH}} onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
        <aside onFocus={handleFocusIn} onBlur={handleFocusOut} className={cn("absolute left-0 top-0 h-full flex flex-col border-r border-border/20 transition-all duration-200 bg-background",isExpanded?"w-[280px] z-50 shadow-xl bg-sidebar/95 backdrop-blur-xl":"w-[72px] bg-sidebar/50 backdrop-blur-md")}>
          {isExpanded ? (
            <>
              {/* Header */}
              <div className="px-3 pt-4 pb-2 space-y-2">
                <BrandSelector />
                <Button variant="ghost" className={cn("w-full justify-start gap-3 px-3 h-10 text-muted-foreground hover:text-primary hover:bg-primary/5 rounded-xl font-medium",!activeBrand&&"opacity-50 pointer-events-none")} onClick={onOpenBrandMemory}><Brain className="w-4 h-4"/><span className="text-sm">Brand Profile</span></Button>
              </div>
              <div className="px-4 py-2"><Separator className="opacity-50"/></div>
              {/* Main Navigation */}
              <ScrollArea className="flex-1 px-3">
                <div className="space-y-6 py-2 pb-8">
                  <SectionGroup title="PROJECTS" count={projects.length} isOpen={projectsOpen} onToggle={()=>setProjectsOpen(!projectsOpen)} onAdd={()=>setIsCreateProjectOpen(true)} activeBrand={!!activeBrand}><ProjectsSection/></SectionGroup>
                  <SectionGroup title="LIBRARY" count={products.length+styleReferences.length} isOpen={libraryOpen} onToggle={()=>setLibraryOpen(!libraryOpen)} activeBrand={!!activeBrand} noAdd>
                    <div className="space-y-4 pt-1 pl-1">
                      <SubSectionGroup title="Products" icon={<Package className="w-3.5 h-3.5"/>} count={products.length} isOpen={productsOpen} onToggle={()=>setProductsOpen(!productsOpen)} onAdd={()=>setIsCreateProductOpen(true)} activeBrand={!!activeBrand}><ProductsSection/></SubSectionGroup>
                      <SubSectionGroup title="Style References" icon={<Palette className="w-3.5 h-3.5"/>} count={styleReferences.length} isOpen={styleRefsOpen} onToggle={()=>setStyleRefsOpen(!styleRefsOpen)} onAdd={()=>setIsCreateStyleRefOpen(true)} activeBrand={!!activeBrand}><StyleReferencesSection createDialogOpen={isCreateStyleRefOpen} onCreateDialogChange={setIsCreateStyleRefOpen}/></SubSectionGroup>
                    </div>
                  </SectionGroup>
                </div>
              </ScrollArea>
              {/* Footer */}
              <div className="p-3 border-t border-border/30 flex items-center justify-between gap-1 bg-background/80 backdrop-blur-md"><Button variant="ghost" size="sm" className="flex-1 justify-start gap-2 h-9 px-2 text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-lg font-medium text-xs transition-colors duration-150" onClick={()=>setIsSettingsOpen(true)}><Settings className="w-4 h-4"/>Settings</Button><Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" className="w-8 h-8 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors duration-150" onClick={onToggleCollapse}><PanelLeftClose className="w-4 h-4"/></Button></TooltipTrigger><TooltipContent>Collapse Sidebar</TooltipContent></Tooltip></div>
              <CreateProductDialog open={isCreateProductOpen} onOpenChange={setIsCreateProductOpen}/>
              <CreateProjectDialog open={isCreateProjectOpen} onOpenChange={setIsCreateProjectOpen}/>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center py-6 gap-4">
              <BrandSelector compact/>
              <Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" className="w-10 h-10 rounded-xl text-muted-foreground hover:text-primary hover:bg-primary/10" onClick={onOpenBrandMemory} disabled={!activeBrand}><Brain className="w-5 h-5" strokeWidth={1.5}/></Button></TooltipTrigger><TooltipContent side="right">Brand Profile</TooltipContent></Tooltip>
              <div className="flex-1"/>
              <CollapsedNavIcon icon={<Settings className="w-5 h-5"/>} label="Settings" onClick={()=>setIsSettingsOpen(true)}/>
              <CollapsedNavIcon icon={<PanelLeftClose className="w-5 h-5 rotate-180"/>} label="Expand" onClick={onToggleCollapse}/>
            </div>
          )}
          <SettingsDialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen}/>
        </aside>
      </div>
    </TooltipProvider>
  )
}

function CollapsedNavIcon({ icon, label, onClick, disabled }: any) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="w-10 h-10 rounded-xl text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
          onClick={onClick}
          disabled={disabled}
        >
          {icon}
        </Button>
      </TooltipTrigger>
      <TooltipContent side="right" sideOffset={10}>
        <p>{label}</p>
      </TooltipContent>
    </Tooltip>
  )
}

function SectionGroup({title,count,isOpen,onToggle,onAdd,activeBrand,children,noAdd}:any){return(<div className="group/section"><div className="flex items-center justify-between py-1.5 px-2 mb-1"><button onClick={onToggle} className="flex-1 flex items-center gap-2 text-[11px] font-semibold text-muted-foreground/60 hover:text-foreground/80 transition-colors duration-150 uppercase tracking-wider text-left" disabled={!activeBrand}><ChevronRight className={cn("w-4 h-4 transition-transform duration-200",isOpen&&"rotate-90")}/>{title}{count!==undefined&&<span className="ml-1 text-[10px] font-normal opacity-60">({count})</span>}</button>{!noAdd&&(<Button variant="ghost" size="icon" className="h-5 w-5 rounded-md hover:bg-muted/50 hover:text-primary opacity-0 group-hover/section:opacity-100 transition-opacity focus:opacity-100" onClick={(e)=>{e.stopPropagation();onAdd?.();}} disabled={!activeBrand}><Plus className="w-3.5 h-3.5"/></Button>)}</div><div className={cn("grid transition-all duration-200 ease-in-out",isOpen?"grid-rows-[1fr] opacity-100":"grid-rows-[0fr] opacity-0")}><div className="overflow-hidden">{children}</div></div></div>)}

function SubSectionGroup({title,icon,count,isOpen,onToggle,onAdd,activeBrand,children}:any){return(<div className="group/subsection pl-2"><div className="flex items-center justify-between py-1 px-2 mb-0.5 rounded-lg hover:bg-muted/30 transition-colors duration-150"><button onClick={onToggle} className="flex-1 flex items-center gap-2.5 text-xs font-semibold text-muted-foreground/80 hover:text-foreground transition-colors duration-150 text-left" disabled={!activeBrand}><div className={cn("transition-transform duration-200",isOpen?"rotate-0":"-rotate-90 text-muted-foreground/50")}><ChevronDown className="w-3 h-3"/></div>{icon&&<span className="text-muted-foreground/60 group-hover/subsection:text-foreground/70 transition-colors">{icon}</span>}{title}{count!==undefined&&<span className="ml-0.5 text-[10px] font-normal opacity-60">({count})</span>}</button><Button variant="ghost" size="icon" className="h-5 w-5 rounded-md hover:bg-muted/50 hover:text-primary opacity-0 group-hover/subsection:opacity-100 transition-opacity focus:opacity-100" onClick={(e)=>{e.stopPropagation();onAdd?.();}} disabled={!activeBrand}><Plus className="w-3 h-3"/></Button></div><div className={cn("grid transition-all duration-150 ease-in-out border-l border-border/30 ml-[11px] pl-2",isOpen?"grid-rows-[1fr] opacity-100 py-1":"grid-rows-[0fr] opacity-0")}><div className="overflow-hidden">{children}</div></div></div>)}
