import { ScrollArea } from '@/components/ui/scroll-area'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { AlertCircle, Plus } from 'lucide-react'
import { useChat } from '@/hooks/useChat'
import { MessageInput } from './MessageInput'
import { MessageList } from './MessageList'

interface ChatPanelProps {
  brandSlug: string | null
}

export function ChatPanel({ brandSlug }: ChatPanelProps) {
  const { messages, isLoading, progress, error, sendMessage, clearMessages } = useChat(brandSlug)

  return (
    <main className="flex-1 flex flex-col h-screen bg-white dark:bg-gray-900">
      <div className="flex items-center justify-between p-3 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Chat</span>
        <Button
          variant="ghost"
          size="sm"
          onClick={clearMessages}
          disabled={isLoading || messages.length === 0}
          className="text-gray-500 hover:text-gray-700"
        >
          <Plus className="h-4 w-4 mr-1" />
          New Chat
        </Button>
      </div>

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
