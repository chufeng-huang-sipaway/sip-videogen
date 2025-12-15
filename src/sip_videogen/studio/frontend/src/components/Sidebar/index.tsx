import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { BrandSelector } from './BrandSelector'
import { BrandActions } from './BrandActions'
import { DocumentsList } from './DocumentsList'
import { AssetTree } from './AssetTree'

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
          <DocumentsList />
          <Separator className="my-4" />
          <AssetTree />
        </div>
      </ScrollArea>
    </aside>
  )
}
