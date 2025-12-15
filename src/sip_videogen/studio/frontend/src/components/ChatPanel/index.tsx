import { useCallback } from 'react'
import { useDropzone, type DropEvent, type FileRejection } from 'react-dropzone'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { AlertCircle, Paperclip, Plus, X } from 'lucide-react'
import { useChat } from '@/hooks/useChat'
import { MessageInput } from './MessageInput'
import { MessageList } from './MessageList'

interface ChatPanelProps {
  brandSlug: string | null
}

export function ChatPanel({ brandSlug }: ChatPanelProps) {
  const {
    messages,
    isLoading,
    progress,
    error,
    attachmentError,
    attachments,
    sendMessage,
    clearMessages,
    resolveInteraction,
    addFilesAsAttachments,
    addAttachmentReference,
    removeAttachment,
    setAttachmentError,
  } = useChat(brandSlug)

  const handleDrop = useCallback(
    (accepted: File[], rejections: FileRejection[], event: DropEvent) => {
      if (!brandSlug) {
        setAttachmentError('Select a brand before attaching files.')
        return
      }

      if (rejections.length > 0) {
        const first = rejections[0]
        const firstError = first.errors[0]?.message
        setAttachmentError(firstError || 'Unsupported file type')
      }

      const dataTransfer = 'dataTransfer' in event ? (event as DragEvent).dataTransfer : null
      const assetPath =
        dataTransfer?.getData('application/x-brand-asset') ||
        dataTransfer?.getData('text/plain') ||
        ''

      if (assetPath && assetPath.trim()) {
        addAttachmentReference(assetPath.trim())
      }

      if (accepted.length > 0) {
        void addFilesAsAttachments(accepted)
      }
    },
    [addAttachmentReference, addFilesAsAttachments, brandSlug, setAttachmentError]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    noClick: true,
    noKeyboard: true,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'],
      'text/plain': ['.txt', '.md'],
      'application/json': ['.json'],
      'application/x-yaml': ['.yaml', '.yml'],
    },
    onDrop: handleDrop,
  })

  return (
    <main
      {...getRootProps()}
      className={`flex-1 flex flex-col h-screen bg-white dark:bg-gray-900 ${isDragActive ? 'ring-2 ring-blue-400 ring-offset-2' : ''}`}
    >
      <input {...getInputProps()} />
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

      {attachmentError && (
        <div className="px-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{attachmentError}</AlertDescription>
          </Alert>
        </div>
      )}

      <ScrollArea className="flex-1">
        <MessageList
          messages={messages}
          progress={progress}
          isLoading={isLoading}
          onInteractionSelect={(messageId, selection) => {
            resolveInteraction(messageId)
            void sendMessage(selection)
          }}
        />
      </ScrollArea>

      {attachments.length > 0 && (
        <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50">
          <div className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300 mb-1">
            <Paperclip className="h-3 w-3" />
            <span>Attachments</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {attachments.map((att) => (
              <div
                key={att.id}
                className="flex items-center gap-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-2 py-1"
              >
                {att.preview ? (
                  <img src={att.preview} alt={att.name} className="h-10 w-10 rounded object-cover" />
                ) : (
                  <div className="h-10 w-10 rounded bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-[10px] text-gray-500">
                    {att.source === 'asset' ? 'Asset' : 'File'}
                  </div>
                )}
                <div className="text-xs max-w-[160px] truncate">{att.name}</div>
                <button
                  type="button"
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  onClick={() => removeAttachment(att.id)}
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="border-t border-gray-200 dark:border-gray-800">
        <MessageInput
          disabled={isLoading || !brandSlug}
          placeholder={brandSlug ? 'Ask me to create something...' : 'Select a brand first...'}
          onSend={(text) => sendMessage(text)}
          canSendWithoutText={attachments.length > 0}
        />
      </div>
    </main>
  )
}
