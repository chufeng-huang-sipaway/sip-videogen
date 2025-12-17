import { useEffect, useRef, useState } from 'react'
import { Package, Paperclip } from 'lucide-react'
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog'
import { ActivityIndicator, type ActivityType } from '@/components/ui/activity-indicator'
import { bridge, isPyWebView, type ProductEntry } from '@/lib/bridge'
import type { Message } from '@/hooks/useChat'
import { MarkdownContent } from './MarkdownContent'
import { ExecutionTrace } from './ExecutionTrace'
import { InteractionRenderer } from './InteractionRenderer'
import { MemoryUpdateBadge } from './MemoryUpdateBadge'
import { ChatImageGallery } from './ChatImageGallery'

interface MessageListProps {
  messages: Message[]
  progress: string
  progressType: ActivityType
  loadedSkills: string[]
  isLoading: boolean
  products: ProductEntry[]
  onInteractionSelect: (messageId: string, selection: string) => void
}

/** Thumbnail component for product images in message history */
function MessageProductThumbnail({ path }: { path: string }) {
  const [src, setSrc] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (!isPyWebView() || !path) return
      try {
        const dataUrl = await bridge.getProductImageThumbnail(path)
        if (!cancelled) setSrc(dataUrl)
      } catch {
        // Ignore thumbnail errors
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [path])

  if (!src) {
    return (
      <div className="h-6 w-6 rounded bg-white/20 flex items-center justify-center shrink-0">
        <Package className="h-3 w-3 text-white/60" />
      </div>
    )
  }

  return (
    <img
      src={src}
      alt=""
      className="h-6 w-6 rounded object-cover shrink-0 border border-white/30"
    />
  )
}

export function MessageList({ messages, progress, progressType, loadedSkills, isLoading, products, onInteractionSelect }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, progress])

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center text-gray-500 p-8">
        <h2 className="text-xl font-semibold mb-2">Welcome to Brand Studio</h2>
        <p className="text-sm max-w-md">
          Select a brand, then ask me to generate on-brand marketing images or provide brand guidance.
        </p>
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[80%] rounded-2xl px-4 py-3 ${
              message.role === 'user'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 dark:bg-gray-800'
            }`}
          >
            {message.status === 'sending' ? (
              <ActivityIndicator
                type={progressType || 'thinking'}
                message={message.content || progress || 'Thinking...'}
                skills={loadedSkills}
              />
            ) : message.role === 'assistant' ? (
              <MarkdownContent content={message.content} />
            ) : (
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
            )}

            {message.attachments && message.attachments.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {message.attachments.map((att) => (
                  att.preview ? (
                    // Image attachment - show clickable thumbnail
                    <Dialog key={att.id}>
                      <DialogTrigger asChild>
                        <div className="cursor-pointer group relative">
                          <img
                            src={att.preview}
                            alt={att.name}
                            className="h-20 w-20 rounded-lg object-cover border border-white/30
                                     hover:opacity-90 transition"
                          />
                          <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-white
                                        text-[10px] px-1 py-0.5 rounded-b-lg truncate">
                            {att.name}
                          </div>
                        </div>
                      </DialogTrigger>
                      <DialogContent className="max-w-4xl p-0 overflow-hidden bg-black/90">
                        <img src={att.preview} alt={att.name} className="w-full h-auto max-h-[80vh] object-contain" />
                      </DialogContent>
                    </Dialog>
                  ) : (
                    // Non-image attachment - show icon and name
                    <div
                      key={att.id}
                      className="flex items-center gap-2 rounded-lg border border-gray-200
                               dark:border-gray-700 bg-white/80 dark:bg-gray-700/50 px-2 py-1"
                    >
                      <Paperclip className="h-4 w-4 text-gray-500" />
                      <div className="text-xs text-gray-700 dark:text-gray-200 max-w-[160px] truncate">
                        {att.name}
                      </div>
                    </div>
                  )
                ))}
              </div>
            )}

            {/* Attached products (user messages only) */}
            {message.role === 'user' &&
              message.attachedProductSlugs &&
              message.attachedProductSlugs.length > 0 && (
                <div className="mt-2 pt-2 border-t border-white/20">
                  <div className="flex items-center gap-1.5 text-[10px] text-white/70 mb-1.5">
                    <Package className="h-3 w-3" />
                    <span>Products referenced</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {message.attachedProductSlugs.map((slug) => {
                      const product = products.find((p) => p.slug === slug)
                      return (
                        <div
                          key={slug}
                          className="flex items-center gap-1.5 rounded-md bg-white/10
                                   border border-white/20 px-1.5 py-0.5"
                        >
                          {product?.primary_image ? (
                            <MessageProductThumbnail path={product.primary_image} />
                          ) : (
                            <div className="h-6 w-6 rounded bg-white/20 flex items-center
                                          justify-center shrink-0">
                              <Package className="h-3 w-3 text-white/60" />
                            </div>
                          )}
                          <span className="text-[11px] text-white/90 max-w-[80px] truncate">
                            {product?.name || slug}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

            {message.images.length > 0 && (
              <ChatImageGallery images={message.images} />
            )}

            {message.role === 'assistant' && message.executionTrace && message.executionTrace.length > 0 && (
              <ExecutionTrace events={message.executionTrace} />
            )}

            {message.memoryUpdate && (
              <MemoryUpdateBadge message={message.memoryUpdate.message} />
            )}

            {message.role === 'assistant' &&
              message.interaction &&
              !message.interactionResolved && (
                <InteractionRenderer
                  interaction={message.interaction}
                  onSelect={(selection) => onInteractionSelect(message.id, selection)}
                  disabled={isLoading}
                />
              )}

            {message.status === 'error' && (
              <p className="text-xs text-red-500 mt-2">{message.error}</p>
            )}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
