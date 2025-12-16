import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { BrandSelector } from './BrandSelector'
import { BrandActions } from './BrandActions'
import { BrandSection } from './sections/BrandSection'
import { ProductsSection } from './sections/ProductsSection'
import { ProjectsSection } from './sections/ProjectsSection'

interface SidebarProps {
  width: number
}

export function Sidebar({ width }: SidebarProps) {
  return (
    <aside
      className="h-screen flex flex-col glass-sidebar border-r border-gray-200/50 dark:border-gray-700/50 flex-shrink-0"
      style={{ width }}
    >
      <div className="p-4 flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
          <span className="text-white text-sm font-bold">B</span>
        </div>
        <h1 className="text-lg font-semibold">Brand Studio</h1>
      </div>
      <Separator />
      <div className="p-4">
        <BrandSelector />
      </div>
      <BrandActions />
      <Separator />
      <ScrollArea className="flex-1">
        <div className="p-4">
          <Accordion type="multiple" defaultValue={["brand", "products", "projects"]}>
            <AccordionItem value="brand">
              <AccordionTrigger>Brand</AccordionTrigger>
              <AccordionContent>
                <BrandSection />
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="products">
              <AccordionTrigger>Products</AccordionTrigger>
              <AccordionContent>
                <ProductsSection />
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="projects">
              <AccordionTrigger>Projects</AccordionTrigger>
              <AccordionContent>
                <ProjectsSection />
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      </ScrollArea>
    </aside>
  )
}
