import{useCallback,useState,useEffect,useMemo}from'react'
import{useDropzone,type DropEvent,type FileRejection}from'react-dropzone'
import{ScrollArea}from'@/components/ui/scroll-area'
import{Alert,AlertDescription}from'@/components/ui/alert'
import{Button}from'@/components/ui/button'
import{AlertCircle,Paperclip,X,Upload,Plus}from'lucide-react'
import{useChat}from'@/hooks/useChat'
import{useProducts}from'@/context/ProductContext'
import{useProjects}from'@/context/ProjectContext'
import{useTemplates}from'@/context/TemplateContext'
import{useWorkstation}from'@/context/WorkstationContext'
import{useDrag}from'@/context/DragContext'
import{MessageInput}from'./MessageInput'
import{MessageList}from'./MessageList'
import{AttachedProducts}from'./AttachedProducts'
import{AttachedTemplates}from'./AttachedTemplates'
import{ProjectSelector}from'./ProjectSelector'
import{AspectRatioSelector}from'./AspectRatioSelector'
import{resolveMentions}from'@/lib/mentionParser'
import type{ImageStatusEntry,AttachedTemplate}from'@/lib/bridge'

interface ChatPanelProps {
  brandSlug: string | null
}

function getDataTransferTypes(dt: DataTransfer): string[] {
  // `DataTransfer.types` is a `DOMStringList` in some WebKit environments (no `.includes`).
  return Array.from(dt.types)
}

function looksLikeAssetPath(value: string): boolean {
  const v = value.trim()
  if (!v) return false
  if (v.startsWith('file://')) return true
  if (v.includes('/') || v.includes('\\')) return true
  return /\.(png|jpe?g|gif|webp|svg|bmp|tiff?)$/i.test(v)
}

export function ChatPanel({ brandSlug }: ChatPanelProps) {
  const {
    products,
    attachedProducts,
    attachProduct,
    detachProduct,
    clearAttachments,
    refresh: refreshProducts,
  } = useProducts()

  const {
    projects,
    activeProject,
    setActiveProject,
  } = useProjects()

  const {
    templates,
    attachedTemplates,
    attachTemplate,
    detachTemplate,
    setTemplateStrictness,
    clearTemplateAttachments,
    refresh: refreshTemplates,
  } = useTemplates()

  const { prependToBatch } = useWorkstation()
  const { dragData, getDragData, clearDrag, registerDropZone, unregisterDropZone } = useDrag()
  const [mainEl, setMainEl] = useState<HTMLElement | null>(null)
  const mainRef = useCallback((el: HTMLElement | null) => { setMainEl(el) }, [])
  const [inputText, setInputText] = useState('')
  //Compute combined attachments (Quick Insert + mentions) for display
  const combinedAttachments=useMemo(()=>{
    const mentionAtts=resolveMentions(inputText,products,templates)
    const allProductSlugs=[...new Set([...attachedProducts,...mentionAtts.products])]
    const tplMap=new Map<string,AttachedTemplate>()
    for(const t of mentionAtts.templates)tplMap.set(t.template_slug,t)
    for(const t of attachedTemplates)tplMap.set(t.template_slug,t)
    return{products:allProductSlugs,templates:Array.from(tplMap.values())}
  },[inputText,products,templates,attachedProducts,attachedTemplates])

  const handleImagesGenerated = useCallback((images: ImageStatusEntry[]) => {
    const batch = images.map(img => ({
      id: img.id,
      path: img.currentPath,
      originalPath: img.originalPath,
      prompt: img.prompt || undefined,
      sourceTemplatePath: img.sourceTemplatePath || undefined,
      timestamp: img.timestamp,
      viewedAt: img.viewedAt ?? null,
    }))
    prependToBatch(batch)
  }, [prependToBatch])

  const {
    messages,
    isLoading,
    progress,
    loadedSkills,
    thinkingSteps,
    error,
    attachmentError,
    attachments,
    aspectRatio,
    sendMessage,
    clearMessages,
    cancelGeneration,
    regenerateMessage,
    resolveInteraction,
    addFilesAsAttachments,
    addAttachmentReference,
    removeAttachment,
    setAttachmentError,
    setAspectRatio,
  } = useChat(brandSlug, { onTemplatesCreated: () => refreshTemplates(), onImagesGenerated: handleImagesGenerated })



  // Track drag state for both files and internal assets
  const [isInternalDragOver, setIsInternalDragOver] = useState(false)


  // Register as drop zone for mouse-based drag (bypasses PyWebView HTML5 drag issues)
  useEffect(() => {
    if (!mainEl) return
    const handleDrop = (data: { type: string; path: string }) => {
      if (!brandSlug) {
        setAttachmentError('Select a brand before attaching files.')
        return
      }
      if (data.type === 'asset') addAttachmentReference(data.path)
      else if (data.type === 'template') attachTemplate(data.path)
      else if (data.type === 'product') attachProduct(data.path)
    }
    registerDropZone('chat-panel', mainEl, handleDrop)
    return () => unregisterDropZone('chat-panel')
  }, [mainEl, brandSlug, addAttachmentReference, attachTemplate, attachProduct, registerDropZone, unregisterDropZone, setAttachmentError])

  // Handle image selection from file input
  const handleSelectImages = useCallback((files: File[]) => {
    if (!brandSlug) {
      setAttachmentError('Select a brand before attaching files.')
      return
    }
    void addFilesAsAttachments(files)
  }, [addFilesAsAttachments, brandSlug, setAttachmentError])

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
    // Always allow drops when context drag is active (use getDragData for sync read)
    if (getDragData()) {
      e.preventDefault()
      e.stopPropagation()
      return
    }
    const types = getDataTransferTypes(e.dataTransfer)
    const hasFiles = (e.dataTransfer.files?.length ?? 0) > 0
    const isFileDrag = hasFiles || types.includes('Files')

    // WebKit/PyWebView can omit custom types during dragover, which prevents `drop`
    // unless we call `preventDefault()`. Treat any drag-without-files as internal.
    if (!isFileDrag) {
      e.preventDefault()
      e.stopPropagation()
      setIsInternalDragOver(true)
    }
  }, [getDragData])

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
    const currentDrag = getDragData()
    if (currentDrag) {
      e.preventDefault()
      e.stopPropagation()
      if (!brandSlug) {
        setAttachmentError('Select a brand before attaching files.')
        clearDrag()
        return
      }
      if (currentDrag.type === 'asset') addAttachmentReference(currentDrag.path)
      else if (currentDrag.type === 'template') attachTemplate(currentDrag.path)
      else if (currentDrag.type === 'product') attachProduct(currentDrag.path)
      clearDrag()
      return
    }

    const textPlain = e.dataTransfer.getData('text/plain').trim()

    // Check for template drag first
    const templateSlug = e.dataTransfer.getData('application/x-brand-template')
    const fallbackTemplateSlug =
      !templateSlug && textPlain && templates.some(t => t.slug === textPlain) ? textPlain : ''
    const finalTemplateSlug = (templateSlug || fallbackTemplateSlug).trim()

    if (finalTemplateSlug) {
      e.preventDefault()
      e.stopPropagation()

      if (!brandSlug) {
        setAttachmentError('Select a brand before attaching templates.')
        return
      }

      attachTemplate(finalTemplateSlug)
      return
    }

    // Check for product drag
    const productSlug = e.dataTransfer.getData('application/x-brand-product')
    const fallbackProductSlug =
      !productSlug && textPlain && products.some(p => p.slug === textPlain) ? textPlain : ''
    const finalProductSlug = (productSlug || fallbackProductSlug).trim()

    if (finalProductSlug) {
      e.preventDefault()
      e.stopPropagation()

      if (!brandSlug) {
        setAttachmentError('Select a brand before attaching products.')
        return
      }

      attachProduct(finalProductSlug)
      return
    }

    // Check for asset drag
    const assetPath = e.dataTransfer.getData('application/x-brand-asset')
    const fallbackAssetPath = !assetPath && looksLikeAssetPath(textPlain) ? textPlain : ''
    const finalAssetPath = (assetPath || fallbackAssetPath).trim()

    if (finalAssetPath) {
      e.preventDefault()
      e.stopPropagation()

      if (!brandSlug) {
        setAttachmentError('Select a brand before attaching files.')
        return
      }

      addAttachmentReference(finalAssetPath)
    }
  }, [
    addAttachmentReference,
    attachProduct,
    attachTemplate,
    brandSlug,
    clearDrag,
    getDragData,
    products,
    setAttachmentError,
    templates,
  ])

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

  // Show overlay when either react-dropzone detects drag, internal asset drag, or context drag
  const showDragOverlay = isDragActive || isInternalDragOver || dragData !== null

  return (
    <main
      {...getRootProps({
        onDragOver: handleNativeDragOver,
        onDragLeave: handleNativeDragLeave,
        onDrop: handleNativeDrop,
      })}
      ref={mainRef}
      className="flex-1 flex flex-col h-screen glass-sidebar border-l border-white/10 relative"
    >
      <input {...getInputProps()} />

      {/* Prominent drag overlay - handles drop directly, click to dismiss if stuck */}
      {showDragOverlay && (
        <div className="absolute inset-0 z-50 bg-background/80 backdrop-blur-md flex items-center justify-center transition-all duration-200 cursor-pointer" onDragOver={(e) => { e.preventDefault(); e.stopPropagation() }} onDrop={handleNativeDrop} onClick={() => { clearDrag(); setIsInternalDragOver(false) }}>
          <div className="bg-card text-card-foreground px-10 py-8 rounded-3xl shadow-float flex flex-col items-center gap-4 animate-in fade-in zoom-in-95 duration-200 border border-border/20 pointer-events-none">
            <div className="w-20 h-20 rounded-full bg-secondary flex items-center justify-center">
              <Upload className="h-8 w-8 text-foreground/50" strokeWidth={1.5} />
            </div>
            <div className="text-center">
              <h3 className="text-xl font-medium tracking-tight">Drop files to attach</h3>
              <p className="text-sm text-muted-foreground mt-2 font-light">Add context to your conversation</p>
            </div>
          </div>
        </div>
      )}

      {/* Header - Minimalist */}
      <div className="h-16 flex items-center justify-between px-6 pt-4 pb-2 bg-transparent z-10">
        <div className="flex items-center gap-2">
          {/* Project Selector acts as Breadcrumb now */}
          <ProjectSelector
            projects={projects}
            activeProject={activeProject}
            onSelect={setActiveProject}
            disabled={isLoading || !brandSlug}
          />
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            clearMessages()
            clearAttachments()
            clearTemplateAttachments()
            setInputText('')
          }}
          disabled={isLoading || messages.length === 0}
          className="gap-2 text-xs font-medium h-8 rounded-full bg-white/50 dark:bg-white/10 hover:bg-white dark:hover:bg-white/20 border border-transparent hover:border-black/5 dark:hover:border-white/10 shadow-sm transition-all text-muted-foreground hover:text-foreground"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Chat</span>
        </Button>
      </div>

      {
        error && (
          <div className="px-8 pt-2">
            <Alert variant="destructive" className="rounded-xl shadow-sm border-destructive/20 bg-destructive/5">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          </div>
        )
      }

      {
        attachmentError && (
          <div className="px-8 pt-2">
            <Alert variant="destructive" className="rounded-xl shadow-sm border-destructive/20 bg-destructive/5">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{attachmentError}</AlertDescription>
            </Alert>
          </div>
        )
      }

      <ScrollArea className="flex-1">
        <div className="px-4 pb-4 max-w-3xl mx-auto w-full">
          <MessageList
            messages={messages}
            progress={progress}
            loadedSkills={loadedSkills}
            thinkingSteps={thinkingSteps}
            isLoading={isLoading}
            products={products}
            onInteractionSelect={async (messageId, selection) => {
              resolveInteraction(messageId)
              await sendMessage(selection)
              await refreshProducts()
            }}
            onRegenerate={regenerateMessage}
          />
        </div>
      </ScrollArea>

      {/* Context Area (Attachments) - Floating above input */}
      <div className="px-4 max-w-3xl mx-auto w-full flex flex-col gap-2 mb-2">
        <AttachedProducts
          products={products}
          attachedSlugs={combinedAttachments.products}
          onDetach={detachProduct}
        />
        <AttachedTemplates
          templates={templates}
          attachedTemplates={combinedAttachments.templates}
          onDetach={detachTemplate}
          onToggleStrict={setTemplateStrictness}
        />

        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 px-2">
            {attachments.map((att) => (
              <div
                key={att.id}
                className="group flex items-center gap-2 rounded-full border border-border/60 bg-white/80 dark:bg-white/10 backdrop-blur-sm px-3 py-1 shadow-sm"
              >
                {att.preview ? (
                  <img src={att.preview} alt={att.name} className="h-4 w-4 rounded object-cover" />
                ) : (
                  <Paperclip className="h-3 w-3 text-muted-foreground" />
                )}
                <span className="text-xs max-w-[120px] truncate font-medium text-foreground/80">{att.name}</span>
                <button
                  type="button"
                  className="text-muted-foreground/60 hover:text-destructive ml-1"
                  onClick={() => removeAttachment(att.id)}
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Aspect Ratio Selector */}
      <div className="px-4 max-w-3xl mx-auto w-full">
        <AspectRatioSelector value={aspectRatio} onChange={setAspectRatio} disabled={isLoading||!brandSlug}/>
      </div>

      {/* Input Area - Clean, no gradient background */}
      <div className="px-4 pb-6 pt-2 w-full max-w-3xl mx-auto z-20">
        <MessageInput
          disabled={isLoading || !brandSlug}
          isGenerating={isLoading}
          onCancel={cancelGeneration}
          placeholder=""
          onMessageChange={setInputText}
          onSend={async(text)=>{
//Parse mentions from text and merge with Quick Insert attachments
const mentionAtts=resolveMentions(text,products,templates)
//Merge products (dedupe)
const allProducts=[...new Set([...attachedProducts,...mentionAtts.products])]
//Merge templates (Quick Insert wins for strictness)
const tplMap=new Map<string,AttachedTemplate>()
for(const t of mentionAtts.templates)tplMap.set(t.template_slug,t)
for(const t of attachedTemplates)tplMap.set(t.template_slug,t)
const allTemplates=Array.from(tplMap.values())
await sendMessage(text,{project_slug:activeProject,attached_products:allProducts.length>0?allProducts:undefined,attached_templates:allTemplates.length>0?allTemplates:undefined,aspect_ratio:aspectRatio})
await refreshProducts()}}
          canSendWithoutText={attachments.length > 0}
          onSelectImages={handleSelectImages}
          hasProducts={products.length > 0}
          hasTemplates={templates.length > 0}
        />
      </div>

    </main >
  )
}
