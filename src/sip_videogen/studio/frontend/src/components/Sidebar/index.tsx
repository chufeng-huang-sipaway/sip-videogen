import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { BrandSelector } from './BrandSelector'
import { DocumentsList } from './DocumentsList'
import { AssetTree } from './AssetTree'

export function Sidebar() {
  return (
    <aside className="w-72 h-screen flex flex-col glass bg-sidebar-light dark:bg-sidebar-dark border-r border-gray-200/50 dark:border-gray-700/50">
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
