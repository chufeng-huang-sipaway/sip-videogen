import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Package, FolderOpen, Sparkles } from 'lucide-react'
import { BrandSelector } from './BrandSelector'
import { BrandBrainCard } from './BrandBrainCard'
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
    </aside>
  )
}
