import { useEffect, useRef, useState } from 'react'
import { Package, Paperclip, Bot, User } from 'lucide-react'
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog'
import { ActivityIndicator, type ActivityType } from '@/components/ui/activity-indicator'
import { bridge, isPyWebView, type ProductEntry } from '@/lib/bridge'
import type { Message } from '@/hooks/useChat'
import { MarkdownContent } from './MarkdownContent'
import { ExecutionTrace } from './ExecutionTrace'
import { InteractionRenderer } from './InteractionRenderer'
import { MemoryUpdateBadge } from './MemoryUpdateBadge'
import { ChatImageGallery } from './ChatImageGallery'
import { cn } from '@/lib/utils'

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
      <div className="h-6 w-6 rounded bg-muted/20 flex items-center justify-center shrink-0">
        <Package className="h-3 w-3 text-muted-foreground/60" />
      </div>
    )
  }

  return (
    <img
      src={src}
      alt=""
      className="h-6 w-6 rounded object-cover shrink-0 border border-border/30"
    />
  )
}

function MessageBubble({ message, products, onInteractionSelect, isLoading }: {
  message: Message;
  products: ProductEntry[];
  onInteractionSelect: (id: string, sel: string) => void;
  isLoading: boolean
}) {
  const isUser = message.role === 'user'

  // Don't render status updates as full bubbles yet - they are rendered specially
  if (message.status === 'sending') return null

  return (
    <div
      className={cn(
        'group relative flex w-full gap-4 px-4 py-6 transition-colors duration-200',
        isUser ? 'bg-transparent' : 'bg-transparent'
      )}
    >
      {/* Avatar */}
      <div className="flex-shrink-0 mt-1">
        {isUser ? (
          <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary shadow-sm border border-primary/20">
            <User className="h-4 w-4" />
          </div>
        ) : (
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center text-primary-foreground shadow-md">
            <Bot className="h-4 w-4" />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 space-y-2">
        {/* Name */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-foreground/80">
            {isUser ? 'You' : 'Brand Studio'}
          </span>
        </div>

        {/* Text / Markdown */}
        <div className={cn(
          "prose prose-sm max-w-none dark:prose-invert leading-relaxed",
          isUser ? "text-foreground" : "text-foreground/90"
        )}>
          {message.role === 'assistant' ? (
            <MarkdownContent content={message.content} />
          ) : (
            <p className="whitespace-pre-wrap">{message.content}</p>
          )}
        </div>

        {/* Attachments */}
        {message.attachments && message.attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-2">
            {message.attachments.map((att) => (
              att.preview ? (
                <Dialog key={att.id}>
                  <DialogTrigger asChild>
                    <div className="cursor-pointer group relative overflow-hidden rounded-lg ring-1 ring-border/20 shadow-sm">
                      <img
                        src={att.preview}
                        alt={att.name}
                        className="h-20 w-20 object-cover hover:scale-105 transition duration-300"
                      />
                      <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1.5 py-0.5 truncate backdrop-blur-sm">
                        {att.name}
                      </div>
                    </div>
                  </DialogTrigger>
                  <DialogContent className="max-w-4xl p-0 overflow-hidden bg-background/90 border-none backdrop-blur-xl">
                    <img src={att.preview} alt={att.name} className="w-full h-auto max-h-[80vh] object-contain" />
                  </DialogContent>
                </Dialog>
              ) : (
                <div
                  key={att.id}
                  className="flex items-center gap-2 rounded-lg border border-border/50 bg-muted/30 px-2.5 py-1.5"
                >
                  <Paperclip className="h-3.5 w-3.5 opacity-70" />
                  <div className="text-xs max-w-[160px] truncate font-medium">
                    {att.name}
                  </div>
                </div>
              )
            ))}
          </div>
        )}

        {/* Attached Products (User only) */}
        {message.role === 'user' && message.attachedProductSlugs && message.attachedProductSlugs.length > 0 && (
          <div className="mt-3 pt-3 border-t border-border/40">
            <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground mb-2 font-medium uppercase tracking-wide">
              <Package className="h-3 w-3" />
              <span>Products referenced</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {message.attachedProductSlugs.map((slug) => {
                const product = products.find((p) => p.slug === slug)
                return (
                  <div
                    key={slug}
                    className="flex items-center gap-2 rounded-md bg-muted/20 border border-border/30 px-2 py-1 transition hover:bg-muted/30"
                  >
                    {product?.primary_image ? (
                      <MessageProductThumbnail path={product.primary_image} />
                    ) : (
                      <div className="h-6 w-6 rounded bg-muted/20 flex items-center justify-center shrink-0">
                        <Package className="h-3 w-3 text-muted-foreground/60" />
                      </div>
                    )}
                    <span className="text-xs text-foreground/90 max-w-[100px] truncate font-medium">
                      {product?.name || slug}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Gallery */}
        {message.images.length > 0 && (
          <div className="mt-3">
            <ChatImageGallery images={message.images} />
          </div>
        )}

        {/* Execution Trace */}
        {message.role === 'assistant' && message.executionTrace && message.executionTrace.length > 0 && (
          <div className="mt-3">
            <ExecutionTrace events={message.executionTrace} />
          </div>
        )}

        {/* Memory Update */}
        {message.memoryUpdate && (
          <div className="mt-2">
            <MemoryUpdateBadge message={message.memoryUpdate.message} />
          </div>
        )}

        {/* Interaction Request */}
        {message.role === 'assistant' && message.interaction && !message.interactionResolved && (
          <div className="mt-3">
            <InteractionRenderer
              interaction={message.interaction}
              onSelect={(selection) => onInteractionSelect(message.id, selection)}
              disabled={isLoading}
            />
          </div>
        )}

        {/* Error */}
        {message.status === 'error' && (
          <div className="mt-2 flex items-center gap-2 text-xs text-destructive bg-destructive/10 px-3 py-2 rounded-lg border border-destructive/20">
            <span className="font-semibold">Error:</span>
            {message.error}
          </div>
        )}
      </div>
    </div>
  )
}

export function MessageList({ messages, progress, progressType, loadedSkills, isLoading, products, onInteractionSelect }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, progress])

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8 animate-in fade-in duration-500">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500/10 to-purple-500/10 flex items-center justify-center mb-6 ring-1 ring-border/50 shadow-sm">
          <Bot className="w-8 h-8 text-primary/60" />
        </div>
        <h2 className="text-2xl font-semibold tracking-tight mb-2">Welcome to Brand Studio</h2>
        <p className="text-muted-foreground max-w-md leading-relaxed">
          Select a brand, then ask me to generate on-brand marketing images or provide brand guidance.
        </p>
      </div>
    )
  }

  // Find if there is an active "thinking" process to show at the end
  const showActivity = isLoading || progress

  return (
    <div className="flex flex-col pb-4">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          products={products}
          onInteractionSelect={onInteractionSelect}
          isLoading={isLoading}
        />
      ))}

      {/* Thinking Indicator - separate from bubbles, flush left aligned with bot */}
      {showActivity && (
        <div className="px-4 py-2 flex w-full gap-4 animate-in fade-in duration-300">
          {/* Placeholder for alignment or actual bot icon if desired, but minimalist usually just shows text */}
          <div className="h-8 w-8 flex-shrink-0" /> {/* Spacer to align with bot text starts */}

          <div className="flex-1">
            <ActivityIndicator
              type={progressType || 'thinking'}
              message={progress || 'Thinking...'}
              skills={loadedSkills}
            />
          </div>
        </div>
      )}

      <div ref={bottomRef} className="h-px" />
    </div>
  )
}
