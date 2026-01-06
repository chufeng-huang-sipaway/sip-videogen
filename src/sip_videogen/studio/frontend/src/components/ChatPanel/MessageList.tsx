import { useEffect, useRef, useState } from 'react'
import { Package, Paperclip, Play, Film, Layout, XCircle, RefreshCw, Download, Copy, Check } from 'lucide-react'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { type GeneratedVideo, type StyleReferenceSummary, type ProductEntry, type ThinkingStep, type GeneratedImage, type ImageGenerationMetadata } from '@/lib/bridge'
import type { Message } from '@/hooks/useChat'
import { MarkdownContent } from './MarkdownContent'
import { ExecutionTrace } from './ExecutionTrace'
import { ThinkingTimeline } from './ThinkingTimeline'
import { InteractionRenderer } from './InteractionRenderer'
import { ChatImageGallery } from './ChatImageGallery'
import { PromptDetailsModal } from './PromptDetailsModal'
import { cn } from '@/lib/utils'
import { useStyleReferences } from '@/context/StyleReferenceContext'
import { Button } from '@/components/ui/button'
//Helper to normalize images (string | GeneratedImage)
function normalizeImages(imgs:(GeneratedImage|string)[]|undefined):GeneratedImage[]{if(!imgs)return[];return imgs.map(i=>typeof i==='string'?{url:i}:i)}


//Video gallery component for rendering generated videos - compact 48x48 thumbnails
function ChatVideoGallery({videos}:{videos:GeneratedVideo[]}){
const[viewerVideo,setViewerVideo]=useState<GeneratedVideo|null>(null)
if(!videos||videos.length===0)return null
const maxThumbs=4
const shown=videos.slice(0,maxThumbs)
const extra=videos.length-maxThumbs
return(<>
<div className="mt-2 flex items-center gap-1.5">
<div className="flex items-center gap-1 text-xs text-muted-foreground"><Film className="h-3.5 w-3.5"/><span>Generated {videos.length} video{videos.length>1?'s':''}</span></div>
</div>
<div className="mt-1.5 flex flex-wrap gap-1">
{shown.map((vid,i)=>(<button key={vid.path||vid.url||i} onClick={()=>setViewerVideo(vid)} className="relative w-12 h-12 rounded border border-border/60 overflow-hidden hover:ring-2 hover:ring-primary/50 transition-all group">
<div className="w-full h-full bg-gradient-to-br from-muted/80 to-muted/40"/>
<div className="absolute inset-0 flex items-center justify-center">
<div className="w-6 h-6 rounded-full bg-white/80 flex items-center justify-center group-hover:scale-110 transition-transform">
<Play className="w-3 h-3 text-black ml-0.5"/>
</div>
</div>
</button>))}
{extra>0&&(<button onClick={()=>setViewerVideo(videos[maxThumbs])} className="w-12 h-12 rounded border border-border/60 bg-muted flex items-center justify-center text-xs text-muted-foreground hover:bg-muted/80 transition-colors">+{extra}</button>)}
</div>
{viewerVideo&&(<Dialog open={!!viewerVideo} onOpenChange={()=>setViewerVideo(null)}>
<DialogContent className="max-w-4xl p-0 overflow-hidden bg-black/90 border-none">
<video src={viewerVideo.url} className="w-full h-auto max-h-[80vh] object-contain" controls autoPlay playsInline/>
</DialogContent>
</Dialog>)}
</>)}


interface MessageListProps {
  messages: Message[]
  loadedSkills: string[]
  thinkingSteps: ThinkingStep[]
  isLoading: boolean
  products: ProductEntry[]
  styleReferences?: StyleReferenceSummary[]
  onInteractionSelect: (messageId: string, selection: string) => void
  onRegenerate?: (messageId: string) => void
}

function MessageBubble({ message, onInteractionSelect, isLoading, onRegenerate, onViewDetails, liveThinkingSteps, liveSkills }: {
  message: Message;
  products: ProductEntry[];
  styleReferences?: StyleReferenceSummary[];
  onInteractionSelect: (id: string, sel: string) => void;
  isLoading: boolean;
  onRegenerate?: (id: string) => void;
  onViewDetails?: (metadata: ImageGenerationMetadata) => void;
  liveThinkingSteps?: ThinkingStep[];
  liveSkills?: string[];
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

  // For 'sending' status, show the thinking timeline (loading state)
  if (message.status === 'sending') {
    return (
      <div className={cn('group relative flex w-full px-2 py-0 transition-colors duration-200 justify-start')}>
        <div className="flex flex-col items-start w-full">
          <ThinkingTimeline steps={liveThinkingSteps || []} isGenerating={true} skills={liveSkills || []} />
        </div>
      </div>
    )
  }

  return (
    <div className={cn('group relative flex w-full px-2 py-0 transition-colors duration-200',isUser?'justify-end':'justify-start')}>
      {/* Content Container */}
      <div className={cn("flex flex-col",isUser?"items-end max-w-[80%]":"items-start w-full")}>
        {/* Thinking Steps (Persisted from completed messages) - ABOVE response */}
        {message.role === 'assistant' && (() => {
          const normImgs = normalizeImages(message.images)
          const imgMeta = normImgs.find(i => i.metadata)?.metadata ?? null
          const hasContent = (message.thinkingSteps && message.thinkingSteps.length > 0) || imgMeta
          return hasContent ? (
            <div className="mb-2 w-full">
              <ThinkingTimeline steps={message.thinkingSteps || []} isGenerating={false} skills={message.loadedSkills} imageMetadata={imgMeta} onViewFullDetails={imgMeta && onViewDetails ? () => onViewDetails(imgMeta) : undefined}/>
              {normImgs.length > 1 && imgMeta && (<div className="text-xs text-muted-foreground mt-1">Showing metadata for image 1 of {normImgs.length}</div>)}
            </div>
          ) : null
        })()}
        {/* Message Content */}
        {isUser?(
          <div className="relative px-5 py-3 rounded-2xl text-sm leading-relaxed bg-secondary/80 text-foreground font-normal rounded-tr-sm">
            <p className="whitespace-pre-wrap">{message.content}</p>
          </div>
        ):(
          <div className="prose prose-sm max-w-none dark:prose-invert prose-p:leading-relaxed prose-p:my-2 prose-li:my-0.5 text-foreground/90 px-1 overflow-hidden break-words">
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

        {/* User Context Chips (Products/Style References) */}
        {isUser && ((message.attachedProductSlugs && message.attachedProductSlugs.length > 0) || (message.attachedStyleReferences && message.attachedStyleReferences.length > 0)) && (
          <div className="flex flex-wrap gap-1.5 mt-2 justify-end">
            {message.attachedProductSlugs?.map(slug => (
              <div key={slug} className="flex items-center gap-1.5 rounded-full border border-border/30 bg-background/50 px-2 py-0.5 text-[10px] text-muted-foreground">
                <Package className="h-3 w-3 opacity-50" />
                <span>{slug}</span>
              </div>
            ))}
            {message.attachedStyleReferences?.map(sr => (
              <div key={sr.style_reference_slug} className="flex items-center gap-1.5 rounded-full border border-border/30 bg-background/50 px-2 py-0.5 text-[10px] text-muted-foreground">
                <Layout className="h-3 w-3 opacity-50" />
                <span>{sr.style_reference_slug}</span>
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

        {/* Execution Trace (Fallback for non-report_thinking flows) */}
        {message.role === 'assistant' && message.executionTrace && message.executionTrace.length > 0 && (!message.thinkingSteps || message.thinkingSteps.length === 0) && (
          <div className="mt-2 w-full"><ExecutionTrace events={message.executionTrace} /></div>
        )}

        {/* Interaction Request */}
        {message.role === 'assistant' && message.interaction && !message.interactionResolved && (
          <InteractionRenderer interaction={message.interaction} onSelect={(selection)=>onInteractionSelect(message.id,selection)} disabled={isLoading}/>
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

export function MessageList({ messages, loadedSkills, thinkingSteps, isLoading, products, styleReferences, onInteractionSelect, onRegenerate }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const [detailsMeta,setDetailsMeta]=useState<ImageGenerationMetadata|null>(null)
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, thinkingSteps])
  const { styleReferences: contextStyleRefs } = useStyleReferences()
  const allStyleRefs = styleReferences || contextStyleRefs
  if (messages.length === 0) return null
  return (
    <div className="flex flex-col pb-4 w-full gap-8">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} products={products} styleReferences={allStyleRefs} onInteractionSelect={onInteractionSelect} isLoading={isLoading} onRegenerate={onRegenerate} onViewDetails={setDetailsMeta} liveThinkingSteps={thinkingSteps} liveSkills={loadedSkills}/>
      ))}
      <div ref={bottomRef} className="h-px" />
      {/* Modal rendered ONCE at parent level */}
      {detailsMeta&&<PromptDetailsModal metadata={detailsMeta} onClose={()=>setDetailsMeta(null)}/>}
    </div>
  )
}
