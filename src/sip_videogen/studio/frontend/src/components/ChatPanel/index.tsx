import { useCallback, useState } from 'react'
import { useDropzone, type DropEvent, type FileRejection } from 'react-dropzone'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { AlertCircle, Paperclip, Plus, X, Upload } from 'lucide-react'
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

  // Track drag state for both files and internal assets
  const [isInternalDragOver, setIsInternalDragOver] = useState(false)

  const handleDrop = useCallback(
    (accepted: File[], rejections: FileRejection[], event: DropEvent) => {
      setIsInternalDragOver(false)

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

  // Handle native drag events for internal asset drags (not detected by react-dropzone)
  const handleNativeDragOver = useCallback((e: React.DragEvent) => {
    // Check if this is an internal asset drag
    if (e.dataTransfer.types.includes('application/x-brand-asset')) {
      e.preventDefault()
      e.stopPropagation()
      setIsInternalDragOver(true)
    }
  }, [])

  const handleNativeDragLeave = useCallback((e: React.DragEvent) => {
    // Only reset if leaving the container entirely
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX
    const y = e.clientY
    if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
      setIsInternalDragOver(false)
    }
  }, [])

  const handleNativeDrop = useCallback((e: React.DragEvent) => {
    const assetPath = e.dataTransfer.getData('application/x-brand-asset')
    if (assetPath && assetPath.trim()) {
      e.preventDefault()
      e.stopPropagation()
      setIsInternalDragOver(false)

      if (!brandSlug) {
        setAttachmentError('Select a brand before attaching files.')
        return
      }

      addAttachmentReference(assetPath.trim())
    }
  }, [addAttachmentReference, brandSlug, setAttachmentError])

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

  // Show overlay when either react-dropzone detects drag OR internal asset drag
  const showDragOverlay = isDragActive || isInternalDragOver

  return (
    <main
      {...getRootProps()}
      onDragOver={handleNativeDragOver}
      onDragLeave={handleNativeDragLeave}
      onDrop={handleNativeDrop}
      className="flex-1 flex flex-col h-screen bg-white dark:bg-gray-900 relative"
    >
      <input {...getInputProps()} />

      {/* Prominent drag overlay */}
      {showDragOverlay && (
        <div className="absolute inset-0 z-50 bg-blue-500/20 backdrop-blur-[2px] border-4 border-dashed border-blue-500 flex items-center justify-center pointer-events-none">
          <div className="bg-blue-500 text-white px-6 py-4 rounded-xl shadow-lg flex items-center gap-3">
            <Upload className="h-6 w-6" />
            <span className="text-lg font-medium">Drop files here to attach</span>
          </div>
        </div>
      )}

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
