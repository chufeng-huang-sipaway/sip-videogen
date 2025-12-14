import { ScrollArea } from '@/components/ui/scroll-area'

interface ChatPanelProps {
  brandSlug: string | null
}

export function ChatPanel({ brandSlug }: ChatPanelProps) {
  return (
    <main className="flex-1 flex flex-col h-screen bg-white dark:bg-gray-900">
      <ScrollArea className="flex-1">
        <div className="flex items-center justify-center h-full text-gray-500">
          {brandSlug ? `Chat with ${brandSlug}` : 'Select a brand to start'}
        </div>
      </ScrollArea>
    </main>
  )
}
