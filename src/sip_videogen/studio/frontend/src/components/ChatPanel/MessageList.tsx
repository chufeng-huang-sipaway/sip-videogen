import { useEffect, useRef, useState } from 'react'
import { Package, Paperclip, Play, Film, Layout, XCircle, RefreshCw, Download, Copy, Check } from 'lucide-react'
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog'
import { type GeneratedVideo, type TemplateSummary, type ProductEntry, type ThinkingStep } from '@/lib/bridge'
import type { Message } from '@/hooks/useChat'
import { MarkdownContent } from './MarkdownContent'
import { ExecutionTrace } from './ExecutionTrace'
import { ThinkingSteps } from './ThinkingSteps'
import { InteractionRenderer } from './InteractionRenderer'
import { ChatImageGallery } from './ChatImageGallery'
import { cn } from '@/lib/utils'
import { useTemplates } from '@/context/TemplateContext'
import { Button } from '@/components/ui/button'


//Video gallery component for rendering generated videos
function ChatVideoGallery({ videos }: { videos: GeneratedVideo[] }) {
  if (!videos || videos.length === 0) return null
  return (
    <div className="grid gap-4 mt-4">
      {videos.map((video, idx) => (
        <Dialog key={idx}>
          <DialogTrigger asChild>
            <div className="cursor-pointer group relative overflow-hidden rounded-xl ring-1 ring-border/20 shadow-sm hover:ring-primary/40 transition-all bg-black/5">
              <div className="relative aspect-video">
                <video
                  src={video.url}
                  className="w-full h-full object-contain"
                  muted
                  playsInline
                  preload="metadata"
                />
                <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/30 transition-colors">
                  <div className="w-14 h-14 rounded-full bg-white/90 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                    <Play className="w-6 h-6 text-black ml-1" />
                  </div>
                </div>
              </div>
              {video.filename && (
                <div className="absolute bottom-2 left-2 right-2 flex items-center gap-2 text-[10px] text-white/90 bg-black/50 rounded-md px-2 py-1">
                  <Film className="w-3 h-3" />
                  <span className="truncate">{video.filename}</span>
                </div>
              )}
            </div>
          </DialogTrigger>
          <DialogContent className="max-w-screen-lg p-0 overflow-hidden bg-black border-none">
            <div className="relative flex items-center justify-center min-h-[50vh]">
              <video
                src={video.url}
                className="max-w-full max-h-[90vh] object-contain shadow-2xl"
                controls
                autoPlay
                playsInline
              />
            </div>
          </DialogContent>
        </Dialog>
      ))}
    </div>
  )
}


interface MessageListProps {
  messages: Message[]
  progress: string
  loadedSkills: string[]
  thinkingSteps: ThinkingStep[]
  isLoading: boolean
  products: ProductEntry[]
  templates?: TemplateSummary[]
  onInteractionSelect: (messageId: string, selection: string) => void
  onRegenerate?: (messageId: string) => void
}

function MessageBubble({ message, onInteractionSelect, isLoading, onRegenerate }: {
  message: Message;
  products: ProductEntry[];
  templates?: TemplateSummary[];
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
        const img = message.images[i]
        // Support both string and GeneratedImage formats
        const url = typeof img === 'string' ? img : img.url
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
    <div className={cn('group relative flex w-full px-2 py-0 transition-colors duration-200',isUser?'justify-end':'justify-start')}>
      {/* Content Container */}
      <div className={cn("flex flex-col",isUser?"items-end max-w-[80%]":"items-start w-full")}>
        {/* Message Content */}
        {isUser?(
          <div className="relative px-5 py-3 rounded-2xl text-sm leading-relaxed bg-secondary/80 text-foreground font-normal rounded-tr-sm">
            <p className="whitespace-pre-wrap">{message.content}</p>
          </div>
        ):(
          <div className="prose prose-sm max-w-none dark:prose-invert prose-p:leading-relaxed prose-p:my-2 prose-li:my-0.5 text-foreground/90 px-1">
            <MarkdownContent content={message.content} />
          </div>
        )}

        {/* Attachments */}
        {message.attachments && message.attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-2 justify-end">
            {message.attachments.map((att) => (
              att.preview ? (
                <div key={att.id} className="relative rounded-lg overflow-hidden border border-border/20 shadow-sm w-16 h-16">
                  <img src={att.preview} alt={att.name} className="w-full h-full object-cover" />
                </div>
              ) : (
                <div key={att.id} className="flex items-center gap-2 rounded-lg border border-border/30 bg-background px-2 py-1 text-xs text-muted-foreground">
                  <Paperclip className="h-3 w-3" />
                  <span className="max-w-[100px] truncate">{att.name}</span>
                </div>
              )
            ))}
          </div>
        )}

        {/* User Context Chips (Products/Templates) */}
        {isUser && ((message.attachedProductSlugs && message.attachedProductSlugs.length > 0) || (message.attachedTemplates && message.attachedTemplates.length > 0)) && (
          <div className="flex flex-wrap gap-1.5 mt-2 justify-end">
            {message.attachedProductSlugs?.map(slug => (
              <div key={slug} className="flex items-center gap-1.5 rounded-full border border-border/30 bg-background/50 px-2 py-0.5 text-[10px] text-muted-foreground">
                <Package className="h-3 w-3 opacity-50" />
                <span>{slug}</span>
              </div>
            ))}
            {message.attachedTemplates?.map(t => (
              <div key={t.template_slug} className="flex items-center gap-1.5 rounded-full border border-border/30 bg-background/50 px-2 py-0.5 text-[10px] text-muted-foreground">
                <Layout className="h-3 w-3 opacity-50" />
                <span>{t.template_slug}</span>
              </div>
            ))}
          </div>
        )}

        {/* Galleries (Images/Videos) */}
        {(message.images.length > 0 || (message.videos && message.videos.length > 0)) && (
          <div className="mt-4 w-full max-w-2xl">
            {message.images.length > 0 && <ChatImageGallery images={message.images} />}
            {message.videos && message.videos.length > 0 && <ChatVideoGallery videos={message.videos} />}
          </div>
        )}

        {/* Thinking Steps (Persisted from completed messages) */}
        {message.role === 'assistant' && message.thinkingSteps && message.thinkingSteps.length > 0 && (
          <div className="mt-2 w-full"><ThinkingSteps steps={message.thinkingSteps} isGenerating={false} skills={message.loadedSkills} /></div>
        )}
        {/* Execution Trace (Fallback for non-report_thinking flows) */}
        {message.role === 'assistant' && message.executionTrace && message.executionTrace.length > 0 && (!message.thinkingSteps || message.thinkingSteps.length === 0) && (
          <div className="mt-2 w-full"><ExecutionTrace events={message.executionTrace} /></div>
        )}

        {/* Interaction Request */}
        {message.role === 'assistant' && message.interaction && !message.interactionResolved && (
          <div className="mt-4 p-4 rounded-xl border border-primary/10 bg-primary/5 w-full">
            <InteractionRenderer
              interaction={message.interaction}
              onSelect={(selection) => onInteractionSelect(message.id, selection)}
              disabled={isLoading}
            />
          </div>
        )}

        {/* Quick Actions */}
        {message.role === 'assistant' && !message.interaction && !isLoading && (
          <div className="flex gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground" onClick={handleCopy} title="Copy">
              {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            </Button>
            <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground" onClick={() => onRegenerate?.(message.id)} title="Regenerate">
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
            {message.images.length > 0 && (
              <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground" onClick={handleDownloadAll} title="Download All">
                <Download className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        )}

        {/* Error */}
        {message.status === 'error' && (
          <div className="mt-2 flex items-start gap-2 text-xs text-destructive bg-destructive/5 px-3 py-2 rounded-lg border border-destructive/20 max-w-md">
            <XCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <div className="flex flex-col gap-0.5">
              <span className="font-medium">Error occurred</span>
              <span className="text-destructive/80 opacity-90">{message.error}</span>
            </div>
          </div>
        )}
      </div>

    </div>
  )
}

/** Transform tool names to friendly messages */
const TOOL_FRIENDLY_NAMES: Record<string, { label: string; description: string }> = {
  generate_image: { label: 'Creating Image', description: 'Generating visual content' },
  generate_video_clip: { label: 'Creating Video', description: 'Generating video clip' },
  search_web: { label: 'Searching Web', description: 'Looking up information' },
  read_file: { label: 'Reading File', description: 'Processing document' },
  write_file: { label: 'Saving File', description: 'Writing content' },
  analyze_image: { label: 'Analyzing Image', description: 'Understanding visuals' },
  get_brand_identity: { label: 'Loading Brand', description: 'Fetching guidelines' },
}

function parseProgress(progress: string): { toolName: string; friendly: { label: string; description: string } } {
  // Handle "Using tool_name" format
  const usingMatch = progress.match(/^Using\s+(\w+)$/i)
  if (usingMatch) {
    const toolName = usingMatch[1]
    const friendly = TOOL_FRIENDLY_NAMES[toolName] || {
      label: toolName.replace(/_/g, ' '),
      description: 'Processing',
    }
    return { toolName, friendly }
  }

  // Handle thinking
  if (progress.toLowerCase().includes('thinking') || !progress) {
    return {
      toolName: 'thinking',
      friendly: { label: 'Thinking', description: 'Analyzing request' },
    }
  }

  // Default
  return {
    toolName: '',
    friendly: { label: progress || 'Processing', description: 'Working...' },
  }
}

interface ActivityCardProps {
  progress: string
  loadedSkills: string[]
}

function ActivityCard({ progress, loadedSkills }: ActivityCardProps) {
  const { friendly } = parseProgress(progress)

  return (
    <div className="px-6 py-4 animate-in fade-in duration-300">
      <div className="rounded-xl bg-background border border-border/30 shadow-soft p-5 max-w-md">

        {/* Loading Header */}
        <div className="flex items-center gap-3 mb-3">
          <div className="w-5 h-5 relative flex items-center justify-center">
            <div className="absolute inset-0 border-2 border-border rounded-full opacity-20"></div>
            <div className="absolute inset-0 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
          </div>
          <div>
            <div className="text-sm font-medium text-foreground">{friendly.label}</div>
            <div className="text-xs text-muted-foreground">{friendly.description}</div>
          </div>
        </div>

        {/* Minimal Skeleton Bars */}
        <div className="space-y-2 opacity-60">
          <div className="h-1.5 w-3/4 bg-gradient-to-r from-muted via-muted-foreground/10 to-muted rounded-full animate-shimmer bg-[length:200%_100%]"></div>
          <div className="h-1.5 w-1/2 bg-gradient-to-r from-muted via-muted-foreground/10 to-muted rounded-full animate-shimmer bg-[length:200%_100%] delay-150"></div>
        </div>

        {/* Skills (Minimal) */}
        {loadedSkills && loadedSkills.length > 0 && (
          <div className="flex gap-1.5 mt-4 overflow-hidden">
            {loadedSkills.slice(0, 3).map((skill, i) => (
              <span key={i} className="text-[9px] uppercase tracking-wider text-muted-foreground border border-border/40 px-1.5 py-0.5 rounded-sm">
                {skill}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function MessageList({ messages, progress, loadedSkills, thinkingSteps, isLoading, products, templates, onInteractionSelect, onRegenerate }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, progress, thinkingSteps])
  const { templates: contextTemplates } = useTemplates()
  const allTemplates = templates || contextTemplates
  if (messages.length === 0) return null
  //Find if there is an active "thinking" process to show at the end
  const showActivity = isLoading || progress
  return (
    <div className="flex flex-col pb-4 w-full gap-8">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} products={products} templates={allTemplates} onInteractionSelect={onInteractionSelect} isLoading={isLoading} onRegenerate={onRegenerate} />
      ))}
      {/* Thinking Steps (Real-time during loading) */}
      {isLoading && <div className="px-6"><ThinkingSteps steps={thinkingSteps} isGenerating={true} skills={loadedSkills} /></div>}
      {/* Activity Indicator */}
      {showActivity && <ActivityCard progress={progress} loadedSkills={loadedSkills} />}
      <div ref={bottomRef} className="h-px" />
    </div>
  )
}
