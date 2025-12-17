import { useCallback, useState } from 'react'
import { useDropzone, type DropEvent, type FileRejection } from 'react-dropzone'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { AlertCircle, Paperclip, X, Upload, MessageSquarePlus } from 'lucide-react'
import { useChat } from '@/hooks/useChat'
import { useProducts } from '@/context/ProductContext'
import { useProjects } from '@/context/ProjectContext'
import { MessageInput } from './MessageInput'
import { MessageList } from './MessageList'
import { AttachedProducts } from './AttachedProducts'
import { ProjectSelector } from './ProjectSelector'
import { BrandSelector } from './BrandSelector'
import { useBrand } from '@/context/BrandContext'

interface ChatPanelProps {
  brandSlug: string | null
}

export function ChatPanel({ brandSlug }: ChatPanelProps) {
  const {
    messages,
    isLoading,
    progress,
    progressType,
    loadedSkills,
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

  const {
    products,
    attachedProducts,
    attachProduct,
    detachProduct,
    clearAttachments,
  } = useProducts()

  const {
    projects,
    activeProject,
    setActiveProject,
  } = useProjects()

  const { brands, activeBrand, selectBrand } = useBrand()

  const activeProjectEntry = projects.find(p => p.slug === activeProject) || null

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
    // Check if this is an internal asset or product drag
    if (
      e.dataTransfer.types.includes('application/x-brand-asset') ||
      e.dataTransfer.types.includes('application/x-brand-product')
    ) {
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
    setIsInternalDragOver(false)

    // Check for product drag first
    const productSlug = e.dataTransfer.getData('application/x-brand-product')
    if (productSlug && productSlug.trim()) {
      e.preventDefault()
      e.stopPropagation()

      if (!brandSlug) {
        setAttachmentError('Select a brand before attaching products.')
        return
      }

      attachProduct(productSlug.trim())
      return
    }

    // Check for asset drag
    const assetPath = e.dataTransfer.getData('application/x-brand-asset')
    if (assetPath && assetPath.trim()) {
      e.preventDefault()
      e.stopPropagation()

      if (!brandSlug) {
        setAttachmentError('Select a brand before attaching files.')
        return
      }

      addAttachmentReference(assetPath.trim())
    }
  }, [addAttachmentReference, attachProduct, brandSlug, setAttachmentError])

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
      {...getRootProps({
        onDragOver: handleNativeDragOver,
        onDragLeave: handleNativeDragLeave,
        onDrop: handleNativeDrop,
      })}
      className="flex-1 flex flex-col h-screen bg-background relative"
    >
      <input {...getInputProps()} />

      {/* Prominent drag overlay */}
      {showDragOverlay && (
        <div className="absolute inset-0 z-50 bg-background/60 backdrop-blur-sm border-4 border-dashed border-primary/20 flex items-center justify-center pointer-events-none transition-all duration-200">
          <div className="bg-card text-card-foreground px-8 py-6 rounded-2xl shadow-2xl ring-1 ring-border/50 flex flex-col items-center gap-4 animate-in fade-in zoom-in-95 duration-200">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
              <Upload className="h-8 w-8 text-primary" />
            </div>
            <div className="text-center">
              <h3 className="text-xl font-semibold">Drop files to attach</h3>
              <p className="text-sm text-muted-foreground mt-1">Add context to your conversation</p>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between px-6 py-3 border-b border-border/20 bg-background/80 backdrop-blur-md sticky top-0 z-20 transition-all gap-4">
        <div className="flex items-center gap-2 overflow-hidden">
          <div className="flex items-center gap-1.5 p-1 rounded-lg transition-colors group">
            <BrandSelector
              brands={brands}
              activeBrand={activeBrand}
              onSelect={selectBrand}
              disabled={isLoading}
            />
            <span className="text-muted-foreground/20 text-lg font-light pb-0.5">|</span>
            <ProjectSelector
              projects={projects}
              activeProject={activeProject}
              onSelect={setActiveProject}
              disabled={isLoading || !brandSlug}
            />
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            clearMessages()
            clearAttachments()
          }}
          disabled={isLoading || messages.length === 0}
          className="gap-2 text-muted-foreground/40 hover:text-foreground text-xs font-medium h-8 px-2 transition-colors"
        >
          <MessageSquarePlus className="w-4 h-4" />
          <span>New Chat</span>
        </Button>
      </div>

      {
        error && (
          <div className="px-6 pt-4">
            <Alert variant="destructive" className="rounded-xl shadow-sm">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          </div>
        )
      }

      {
        attachmentError && (
          <div className="px-6 pt-4">
            <Alert variant="destructive" className="rounded-xl shadow-sm">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{attachmentError}</AlertDescription>
            </Alert>
          </div>
        )
      }

      <ScrollArea className="flex-1 px-6">
        <div className="py-6 max-w-4xl mx-auto">
          <MessageList
            messages={messages}
            progress={progress}
            progressType={progressType}
            loadedSkills={loadedSkills}
            isLoading={isLoading}
            products={products}
            onInteractionSelect={(messageId, selection) => {
              resolveInteraction(messageId)
              void sendMessage(selection)
            }}
          />
        </div>
      </ScrollArea>

      {/* Attached products display */}
      <div className="px-6 max-w-4xl mx-auto w-full">
        <AttachedProducts
          products={products}
          attachedSlugs={attachedProducts}
          onDetach={detachProduct}
        />
      </div>

      {
        attachments.length > 0 && (
          <div className="px-6 py-3 border-t border-border/40 bg-muted/30 backdrop-blur-sm">
            <div className="max-w-4xl mx-auto w-full">
              <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground mb-2">
                <Paperclip className="h-3 w-3" />
                <span>Attachments</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {attachments.map((att) => (
                  <div
                    key={att.id}
                    className="group flex items-center gap-2 rounded-lg border border-border/60 bg-background/80 px-2 py-1.5 shadow-sm transition-all hover:shadow-md hover:border-border"
                  >
                    {att.preview ? (
                      <img src={att.preview} alt={att.name} className="h-8 w-8 rounded object-cover ring-1 ring-border/20" />
                    ) : (
                      <div className="h-8 w-8 rounded bg-muted flex items-center justify-center text-[10px] text-muted-foreground font-medium">
                        {att.source === 'asset' ? 'Asset' : 'File'}
                      </div>
                    )}
                    <div className="text-xs max-w-[160px] truncate font-medium">{att.name}</div>
                    <button
                      type="button"
                      className="text-muted-foreground/60 hover:text-destructive transition-colors opacity-0 group-hover:opacity-100"
                      onClick={() => removeAttachment(att.id)}
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )
      }

      <div className="p-6 pt-2 bg-gradient-to-t from-background via-background to-transparent">
        <div className="max-w-4xl mx-auto w-full">
          {/* Suggestion Chips for Empty State */}
          {messages.length === 0 && !isLoading && attachments.length === 0 && brandSlug && (
            <div className="flex items-center gap-2 mb-3 animate-in fade-in slide-in-from-bottom-2 duration-500">
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground/40 font-medium ml-1">Try:</span>
              <button
                onClick={() => sendMessage("Draft a holiday email for our subscribers")}
                className="text-xs px-3 py-1.5 rounded-full bg-muted/30 hover:bg-muted/60 text-muted-foreground hover:text-foreground transition-colors border border-transparent hover:border-border/30"
              >
                Holiday email
              </button>
              <button
                onClick={() => sendMessage("Create a product spotlight post")}
                className="text-xs px-3 py-1.5 rounded-full bg-muted/30 hover:bg-muted/60 text-muted-foreground hover:text-foreground transition-colors border border-transparent hover:border-border/30"
              >
                Product spotlight
              </button>
              <button
                onClick={() => sendMessage("Rewrite this with a luxury tone")}
                className="text-xs px-3 py-1.5 rounded-full bg-muted/30 hover:bg-muted/60 text-muted-foreground hover:text-foreground transition-colors border border-transparent hover:border-border/30"
              >
                Tone: luxury
              </button>
            </div>
          )}
          <MessageInput
            disabled={isLoading || !brandSlug}
            placeholder={
              brandSlug
                ? activeProjectEntry
                  ? `Ask me to create something for ${activeProjectEntry.name}...`
                  : 'Ask me to create something...'
                : 'Select a brand to start...'
            }
            onSend={(text) =>
              sendMessage(text, {
                project_slug: activeProject,
                attached_products: attachedProducts.length > 0 ? attachedProducts : undefined,
              })
            }
            canSendWithoutText={attachments.length > 0}
          />
        </div>
      </div>
    </main >
  )
}
