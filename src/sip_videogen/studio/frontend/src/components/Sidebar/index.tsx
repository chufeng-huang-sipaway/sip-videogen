import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { LayoutGrid, Package, FolderOpen, Sparkles } from 'lucide-react'
import { BrandSelector } from './BrandSelector'
import { BrandActions } from './BrandActions'
import { BrandSection } from './sections/BrandSection'
import { ProductsSection } from './sections/ProductsSection'
import { ProjectsSection } from './sections/ProjectsSection'

interface SidebarProps {
  width: number
  onOpenBrandMemory?: () => void
}

export function Sidebar({ width, onOpenBrandMemory }: SidebarProps) {
  return (
    <aside
      className="h-screen flex flex-col glass-sidebar border-r border-border/50 flex-shrink-0 transition-all duration-300 ease-in-out"
      style={{ width }}
    >
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
      
      <BrandActions />
      
      <div className="px-4 py-2">
        <Separator className="bg-border/60" />
      </div>

      <ScrollArea className="flex-1">
        <div className="px-3 py-2">
          <Accordion type="multiple" defaultValue={["brand", "products", "projects"]} className="space-y-1">
            <AccordionItem value="brand" className="border-none">
              <AccordionTrigger className="px-3 py-2 hover:bg-accent/50 rounded-lg hover:no-underline transition-colors [&[data-state=open]>svg]:rotate-90">
                <div className="flex items-center gap-2.5">
                  <LayoutGrid className="w-4 h-4 text-muted-foreground" />
                  <span className="font-medium text-sm">Brand Identity</span>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-3 pb-2 pt-1">
                <BrandSection onOpenBrandMemory={onOpenBrandMemory} />
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="products" className="border-none">
              <AccordionTrigger className="px-3 py-2 hover:bg-accent/50 rounded-lg hover:no-underline transition-colors [&[data-state=open]>svg]:rotate-90">
                <div className="flex items-center gap-2.5">
                  <Package className="w-4 h-4 text-muted-foreground" />
                  <span className="font-medium text-sm">Products</span>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-3 pb-2 pt-1">
                <ProductsSection />
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="projects" className="border-none">
              <AccordionTrigger className="px-3 py-2 hover:bg-accent/50 rounded-lg hover:no-underline transition-colors [&[data-state=open]>svg]:rotate-90">
                <div className="flex items-center gap-2.5">
                  <FolderOpen className="w-4 h-4 text-muted-foreground" />
                  <span className="font-medium text-sm">Projects</span>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-3 pb-2 pt-1">
                <ProjectsSection />
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      </ScrollArea>
    </aside>
  )
}
