import { ScrollArea } from '@/components/ui/scroll-area'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle } from 'lucide-react'
import { useChat } from '@/hooks/useChat'
import { MessageInput } from './MessageInput'
import { MessageList } from './MessageList'

interface ChatPanelProps {
  brandSlug: string | null
}

export function ChatPanel({ brandSlug }: ChatPanelProps) {
  const { messages, isLoading, progress, error, sendMessage } = useChat(brandSlug)

  return (
    <main className="flex-1 flex flex-col h-screen bg-white dark:bg-gray-900">
      {error && (
        <div className="p-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </div>
      )}

      <ScrollArea className="flex-1">
        <MessageList messages={messages} progress={progress} />
      </ScrollArea>

      <div className="border-t border-gray-200 dark:border-gray-800">
        <MessageInput
          disabled={isLoading || !brandSlug}
          placeholder={brandSlug ? 'Ask me to create something...' : 'Select a brand first...'}
          onSend={(text) => sendMessage(text)}
        />
      </div>
    </main>
  )
}
