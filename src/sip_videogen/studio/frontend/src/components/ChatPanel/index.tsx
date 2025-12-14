import { ScrollArea } from '@/components/ui/scroll-area'

export function ChatPanel() {
  return (
    <main className="flex-1 flex flex-col h-screen bg-white dark:bg-gray-900">
      <ScrollArea className="flex-1">
        <div className="flex items-center justify-center h-full text-gray-500">
          Select a brand to start
        </div>
      </ScrollArea>
    </main>
  )
}
