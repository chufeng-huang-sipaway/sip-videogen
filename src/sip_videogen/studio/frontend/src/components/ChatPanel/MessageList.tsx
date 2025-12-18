import { useEffect, useRef, useState } from 'react'
import { Package, Paperclip, Bot, User } from 'lucide-react'
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog'
import { bridge, isPyWebView, type ProductEntry } from '@/lib/bridge'
import type { Message } from '@/hooks/useChat'
import { MarkdownContent } from './MarkdownContent'
import { ExecutionTrace } from './ExecutionTrace'
import { InteractionRenderer } from './InteractionRenderer'
import { MemoryUpdateBadge } from './MemoryUpdateBadge'
import { ChatImageGallery } from './ChatImageGallery'
import { cn } from '@/lib/utils'
import { useBrand } from '@/context/BrandContext'
import { Button } from '@/components/ui/button'
import { BrandSelector } from './BrandSelector'
import { Sparkles, Download, Copy, RefreshCw, XCircle, Check } from 'lucide-react'


interface MessageListProps {
  messages: Message[]
  progress: string
  loadedSkills: string[]
  isLoading: boolean
  products: ProductEntry[]
  onInteractionSelect: (messageId: string, selection: string) => void
  onRegenerate?: (messageId: string) => void
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

function MessageBubble({ message, products, onInteractionSelect, isLoading, onRegenerate }: {
  message: Message;
  products: ProductEntry[];
  onInteractionSelect: (id: string, sel: string) => void;
  isLoading: boolean;
  onRegenerate?: (id: string) => void;
}) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)
  const [downloading, setDownloading] = useState(false)

  // Handle copy to clipboard
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback for older browsers
      const textArea = document.createElement('textarea')
      textArea.value = message.content
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  // Handle download all images
  const handleDownloadAll = async () => {
    if (downloading || message.images.length === 0) return
    setDownloading(true)

    try {
      for (let i = 0; i < message.images.length; i++) {
        const url = message.images[i]
        const filename = `brand-studio-${i + 1}.png`

        // Handle data URLs
        if (url.startsWith('data:')) {
          const response = await fetch(url)
          const blob = await response.blob()
          const objectUrl = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = objectUrl
          a.download = filename
          a.click()
          URL.revokeObjectURL(objectUrl)
        } else {
          // HTTP URL - direct download
          const a = document.createElement('a')
          a.href = url
          a.download = filename
          a.click()
        }

        // Small delay between downloads
        if (i < message.images.length - 1) {
          await new Promise(r => setTimeout(r, 150))
        }
      }
    } finally {
      setDownloading(false)
    }
  }

  // Don't render status updates as full bubbles yet - they are rendered specially
  if (message.status === 'sending') return null

  return (
    <div
      className={cn(
        'group relative flex w-full gap-5 px-6 py-8 transition-colors duration-200 border-b border-transparent',
        isUser ? 'bg-transparent' : 'bg-muted/30 border-border/20'
      )}
    >
      {/* Avatar */}
      <div className="flex-shrink-0 mt-0.5">
        {isUser ? (
          <div className="h-9 w-9 rounded-xl bg-primary/10 flex items-center justify-center text-primary shadow-sm border border-primary/20 ring-4 ring-background">
            <User className="h-5 w-5" />
          </div>
        ) : (
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-md ring-4 ring-background">
            <Bot className="h-5 w-5" />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 space-y-2.5">
        {/* Name & Time */}
        <div className="flex items-center gap-3 mb-1.5 px-1">
          <span className="text-sm font-semibold tracking-tight text-foreground/90">
            {isUser ? 'You' : 'Brand Assistant'}
          </span>
          <span className="text-[10px] text-muted-foreground/50 uppercase tracking-widest font-medium">
            {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>

        {/* Text / Markdown */}
        <div className={cn(
          "prose prose-base max-w-none dark:prose-invert leading-loose tracking-wide",
          isUser ? "text-foreground font-light" : "text-foreground/80 font-light"
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
                    <div className="cursor-pointer group relative overflow-hidden rounded-xl ring-1 ring-border/20 shadow-sm hover:ring-primary/40 transition-all">
                      <img
                        src={att.preview}
                        alt={att.name}
                        className="h-24 w-24 object-cover hover:scale-105 transition duration-300"
                      />
                    </div>
                  </DialogTrigger>
                  <DialogContent className="max-w-screen-lg p-0 overflow-hidden bg-background/90 border-none backdrop-blur-xl">
                    <div className="relative flex items-center justify-center min-h-[50vh]">
                      <img src={att.preview} alt={att.name} className="max-w-full max-h-[90vh] object-contain shadow-2xl" />
                    </div>
                  </DialogContent>
                </Dialog>
              ) : (
                <div key={att.id} className="flex items-center gap-2 rounded-lg border border-border/50 bg-muted/40 px-3 py-2">
                  <Paperclip className="h-4 w-4 opacity-70" />
                  <div className="text-xs font-medium">{att.name}</div>
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
          <div className="mt-4">
            <div className="p-1 rounded-2xl border border-border/40 bg-background/50 backdrop-blur-sm shadow-sm">
              <ChatImageGallery images={message.images} />
            </div>
          </div>
        )}

        {/* Execution Trace */}
        {message.role === 'assistant' && message.executionTrace && message.executionTrace.length > 0 && (
          <div className="mt-3 opacity-80 hover:opacity-100 transition-opacity">
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
          <div className="mt-4 p-4 rounded-xl border border-primary/20 bg-primary/5">
            <InteractionRenderer
              interaction={message.interaction}
              onSelect={(selection) => onInteractionSelect(message.id, selection)}
              disabled={isLoading}
            />
          </div>
        )}

        {/* Quick Actions for Assistant */}
        {message.role === 'assistant' && !message.interaction && !isLoading && (
          <div className="flex flex-wrap gap-2 mt-4 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs gap-1.5 rounded-full bg-background/50 hover:bg-background"
              onClick={() => onRegenerate?.(message.id)}
            >
              <RefreshCw className="w-3 h-3" />
              Regenerate
            </Button>
            <Button
              variant="outline"
              size="sm"
              className={cn(
                "h-7 text-xs gap-1.5 rounded-full bg-background/50 hover:bg-background transition-colors",
                copied && "text-green-600 border-green-600/30"
              )}
              onClick={handleCopy}
            >
              {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
              {copied ? 'Copied!' : 'Copy'}
            </Button>
            {message.images.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs gap-1.5 rounded-full bg-background/50 hover:bg-background"
                onClick={handleDownloadAll}
                disabled={downloading}
              >
                <Download className={cn("w-3 h-3", downloading && "animate-bounce")} />
                {downloading ? 'Downloading...' : 'Download All'}
              </Button>
            )}
          </div>
        )}

        {/* Error */}
        {message.status === 'error' && (
          <div className="mt-3 flex items-start gap-3 text-sm text-destructive bg-destructive/5 px-4 py-3 rounded-xl border border-destructive/20">
            <XCircle className="h-5 w-5 shrink-0 mt-0.5" />
            <div className="flex flex-col gap-1">
              <span className="font-semibold">Error occurred</span>
              <span className="text-destructive/90">{message.error}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/** Transform tool names to friendly messages */
const TOOL_FRIENDLY_NAMES: Record<string, { label: string; description: string }> = {
  generate_image: { label: 'Creating Image', description: 'Generating visual content with AI' },
  search_web: { label: 'Searching Web', description: 'Looking up information online' },
  read_file: { label: 'Reading File', description: 'Processing document contents' },
  write_file: { label: 'Saving File', description: 'Writing content to disk' },
  analyze_image: { label: 'Analyzing Image', description: 'Understanding visual content' },
  get_brand_identity: { label: 'Loading Brand', description: 'Fetching brand guidelines' },
  update_brand: { label: 'Updating Brand', description: 'Saving brand changes' },
  get_product: { label: 'Loading Product', description: 'Fetching product details' },
  update_product: { label: 'Updating Product', description: 'Saving product changes' },
  get_asset: { label: 'Loading Asset', description: 'Fetching media file' },
}

function parseProgress(progress: string): { toolName: string; friendly: { label: string; description: string } } {
  // Handle "Using tool_name" format
  const usingMatch = progress.match(/^Using\s+(\w+)$/i)
  if (usingMatch) {
    const toolName = usingMatch[1]
    const friendly = TOOL_FRIENDLY_NAMES[toolName] || {
      label: toolName.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      description: 'Processing your request',
    }
    return { toolName, friendly }
  }

  // Handle thinking
  if (progress.toLowerCase().includes('thinking') || !progress) {
    return {
      toolName: 'thinking',
      friendly: { label: 'Thinking', description: 'Analyzing your request' },
    }
  }

  // Default
  return {
    toolName: '',
    friendly: { label: progress || 'Processing', description: 'Working on your request' },
  }
}

interface ActivityCardProps {
  progress: string
  loadedSkills: string[]
}

function ActivityCard({ progress, loadedSkills }: ActivityCardProps) {
  const [elapsed, setElapsed] = useState(0)
  const startTimeRef = useRef(Date.now())

  // Reset timer when progress changes significantly
  useEffect(() => {
    startTimeRef.current = Date.now()
    setElapsed(0)
  }, [progress])

  // Update elapsed time every second
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000))
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  const { toolName, friendly } = parseProgress(progress)
  const isImageGen = toolName === 'generate_image'

  const formatElapsed = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}m ${secs}s`
  }

  return (
    <div className="px-6 py-4 animate-in fade-in duration-300">
      <div className="rounded-xl bg-gradient-to-br from-muted/50 to-muted/30 border border-border/40 overflow-hidden">
        {/* Main content */}
        <div className="p-4 flex items-start gap-4">
          {/* Animated icon */}
          <div className="relative flex-shrink-0 mt-0.5">
            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
              {isImageGen ? (
                <Sparkles className="w-5 h-5 text-primary animate-pulse" />
              ) : (
                <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
              )}
            </div>
            {/* Pulse ring */}
            <div className="absolute inset-0 rounded-full bg-primary/20 animate-ping opacity-30" />
          </div>

          {/* Status info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-semibold text-foreground">
                {friendly.label}
              </span>
              <span className="text-xs text-muted-foreground/70">
                {formatElapsed(elapsed)}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mb-2">
              {friendly.description}
            </p>

            {/* Tool badge */}
            {toolName && toolName !== 'thinking' && (
              <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-background/60 border border-border/30">
                <span className="text-[10px] text-muted-foreground/80 font-mono">
                  {toolName}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Skills section */}
        {loadedSkills && loadedSkills.length > 0 && (
          <div className="px-4 py-3 border-t border-border/30 bg-background/30">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] font-medium text-muted-foreground/70 uppercase tracking-wider">
                Expert Skills Active
              </span>
              <span className="text-[10px] font-medium text-primary bg-primary/10 px-1.5 py-0.5 rounded">
                {loadedSkills.length}
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {loadedSkills.map((skill, i) => (
                <span
                  key={i}
                  className="text-[10px] px-2 py-1 rounded-full bg-primary/10 text-primary/80 font-medium"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export function MessageList({ messages, progress, loadedSkills, isLoading, products, onInteractionSelect, onRegenerate }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, progress])

  const { brands, activeBrand, selectBrand } = useBrand()

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4 animate-in fade-in slide-in-from-bottom-4 duration-700 pb-20">

        {/* Minimal High-End Hero Card */}
        <div className="relative w-full max-w-sm mx-auto">

          {/* Card Container - Simplified/Softened */}
          <div className="relative bg-muted/20 rounded-3xl p-8 flex flex-col items-center">

            {/* Icon - Simplified */}
            <div className="w-12 h-12 rounded-full bg-background/80 flex items-center justify-center shadow-sm mb-6 text-foreground/80">
              <Bot className="w-6 h-6" strokeWidth={1.5} />
            </div>

            <div className="space-y-4 mb-8 text-center">
              <h2 className="text-2xl font-semibold tracking-tight text-foreground">
                {activeBrand ? `Hello, ${brands.find(b => b.slug === activeBrand)?.name}` : 'Brand Studio'}
              </h2>
              <p className="text-muted-foreground/70 text-sm font-light leading-7 max-w-[260px] mx-auto">
                {activeBrand
                  ? "What would you like to create today?"
                  : "Select a brand to begin your creative journey."}
              </p>
            </div>

            {/* Actions */}
            {activeBrand && (
              <div className="flex flex-col gap-3 w-full">
                {/* Primary CTA - Mid-weight fill, tighter */}
                <Button
                  className="w-full h-10 rounded-full text-sm font-medium bg-neutral-800 text-white hover:bg-neutral-900 transition-all shadow-sm"
                  onClick={() => onInteractionSelect('suggestion', "Generate Social Post")}
                >
                  <Sparkles className="w-3.5 h-3.5 mr-2 text-white/70" />
                  Generate Social Post
                </Button>

                {/* Secondary Options - Quiet/Ghost Pills */}
                <div className="flex items-center justify-center gap-2 mt-1">
                  <Button
                    variant="ghost"
                    className="h-8 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted/50 text-xs font-medium px-4"
                    onClick={() => onInteractionSelect('suggestion', "Create Ad Campaign")}
                  >
                    Ad Campaign
                  </Button>
                  <Button
                    variant="ghost"
                    className="h-8 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted/50 text-xs font-medium px-4"
                    onClick={() => onInteractionSelect('suggestion', "Brand Guidelines")}
                  >
                    Guidelines
                  </Button>
                </div>
              </div>
            )}

            {!activeBrand && (
              <div className="flex justify-center mt-2">
                <BrandSelector brands={brands} activeBrand={activeBrand} onSelect={selectBrand} />
              </div>
            )}

            {/* Footer Product Link - REMOVED per request */}
          </div>
        </div>
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
          onRegenerate={onRegenerate}
        />
      ))}

      {/* Activity Indicator */}
      {showActivity && (
        <ActivityCard
          progress={progress}
          loadedSkills={loadedSkills}
        />
      )}

      <div ref={bottomRef} className="h-px" />
    </div>
  )
}
