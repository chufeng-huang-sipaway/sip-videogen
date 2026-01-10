import{useCallback,useState,useEffect,useMemo,useRef}from'react'
import{useDropzone,type DropEvent,type FileRejection}from'react-dropzone'
import{ScrollArea}from'@/components/ui/scroll-area'
import{Alert,AlertDescription}from'@/components/ui/alert'
import{Button}from'@/components/ui/button'
import{AlertCircle,Upload,Plus}from'lucide-react'
import{useChat}from'@/hooks/useChat'
import{useProducts}from'@/context/ProductContext'
import{useProjects}from'@/context/ProjectContext'
import{useStyleReferences}from'@/context/StyleReferenceContext'
import{useWorkstation}from'@/context/WorkstationContext'
import{useDrag}from'@/context/DragContext'
import{MessageInput,type MessageInputRef}from'./MessageInput'
import{MessageList}from'./MessageList'
import{AttachmentChips}from'./AttachmentChips'
import{ProjectSelector}from'./ProjectSelector'
import{GenerationSettings}from'./GenerationSettings'
import{AutonomyToggle}from'./AutonomyToggle'
import{ApprovalPrompt}from'./ApprovalPrompt'
import{PanelModeToggle,type PanelMode}from'./PanelModeToggle'
import{PlaygroundMode}from'./PlaygroundMode'
import{ImageBatchCard}from'./ImageBatchCard'
import{resolveMentions}from'@/lib/mentionParser'
import type{ImageStatusEntry,AttachedStyleReference}from'@/lib/bridge'
import type{VideoAspectRatio}from'@/types/aspectRatio'

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
    styleReferences,
    attachedStyleReferences,
    attachStyleReference,
    detachStyleReference,
    clearStyleReferenceAttachments,
    refresh: refreshStyleRefs,
  } = useStyleReferences()

  const { prependToBatch } = useWorkstation()
  const { dragData, getDragData, clearDrag, registerDropZone, unregisterDropZone } = useDrag()
  const [mainEl, setMainEl] = useState<HTMLElement | null>(null)
  const mainRef = useCallback((el: HTMLElement | null) => { setMainEl(el) }, [])
  const [inputText, setInputText] = useState('')
  const [panelMode, setPanelMode] = useState<PanelMode>('assistant')
  const messageInputRef=useRef<MessageInputRef>(null)
  //Compute combined attachments (Quick Insert + mentions) for display
  const combinedAttachments=useMemo(()=>{
    const mentionAtts=resolveMentions(inputText,products,styleReferences)
    const allProductSlugs=[...new Set([...attachedProducts,...mentionAtts.products])]
    const srMap=new Map<string,AttachedStyleReference>()
    for(const t of mentionAtts.styleReferences)srMap.set(t.style_reference_slug,t)
    for(const t of attachedStyleReferences)srMap.set(t.style_reference_slug,t)
    return{products:allProductSlugs,styleReferences:Array.from(srMap.values())}
  },[inputText,products,styleReferences,attachedProducts,attachedStyleReferences])

  const handleImagesGenerated = useCallback((images: ImageStatusEntry[]) => {
    const batch = images.map(img => ({
      id: img.id,
      path: img.currentPath,
      originalPath: img.originalPath,
      prompt: img.prompt || undefined,
      sourceStyleReferencePath: img.sourceStyleReferencePath || undefined,
      timestamp: img.timestamp,
      viewedAt: img.viewedAt ?? null,
    }))
    prependToBatch(batch)
  }, [prependToBatch])
  //Handle videos generated - add to Workstation batch
  const handleVideosGenerated = useCallback((videos: Parameters<typeof prependToBatch>[0]) => {
    prependToBatch(videos)
  }, [prependToBatch])

  const {
    messages,
    isLoading,
    loadedSkills,
    thinkingSteps,
    imageBatch,
    error,
    attachmentError,
    attachments,
    imageAspectRatio,
    videoAspectRatio,
    sendMessage,
    clearMessages,
    cancelGeneration,
    regenerateMessage,
    resolveInteraction,
    addFilesAsAttachments,
    addAttachmentReference,
    removeAttachment,
    setAttachmentError,
    setImageAspectRatio,
    setVideoAspectRatio,
    todoList,
    isPaused,
    pendingApproval,
    autonomyMode,
    handlePause,
    handleResume,
    handleStop,
    handleNewDirection,
    handleApproveAll,
    handleSkipApproval,
    handleSetAutonomyMode,
  } = useChat(brandSlug, { onStyleReferencesCreated: () => refreshStyleRefs(), onImagesGenerated: handleImagesGenerated, onVideosGenerated: handleVideosGenerated })
  //Handle "Let me clarify" - skip approval and focus input
  const handleLetMeClarify=useCallback(()=>{
    handleSkipApproval()
    setTimeout(()=>messageInputRef.current?.focus(),100)
  },[handleSkipApproval])
  //Handle detach product - remove from Quick Insert AND from input text @mentions
  const handleDetachProduct=useCallback((slug:string)=>{
    detachProduct(slug)
    setInputText(prev=>prev.replace(new RegExp(`@product:${slug}\\s*`,'gi'),'').trim())
  },[detachProduct])
  //Handle detach style reference - remove from Quick Insert AND from input text @mentions
  const handleDetachStyleReference=useCallback((slug:string)=>{
    detachStyleReference(slug)
    setInputText(prev=>prev.replace(new RegExp(`@style:${slug}\\s*`,'gi'),'').trim())
  },[detachStyleReference])

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
      else if (data.type === 'style-reference') attachStyleReference(data.path)
      else if (data.type === 'product') attachProduct(data.path)
    }
    registerDropZone('chat-panel', mainEl, handleDrop)
    return () => unregisterDropZone('chat-panel')
  }, [mainEl, brandSlug, addAttachmentReference, attachStyleReference, attachProduct, registerDropZone, unregisterDropZone, setAttachmentError])

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
      else if (currentDrag.type === 'style-reference') attachStyleReference(currentDrag.path)
      else if (currentDrag.type === 'product') attachProduct(currentDrag.path)
      clearDrag()
      return
    }

    const textPlain = e.dataTransfer.getData('text/plain').trim()

    // Check for style reference drag first
    const styleRefSlug = e.dataTransfer.getData('application/x-brand-style-reference')
    const fallbackStyleRefSlug =
      !styleRefSlug && textPlain && styleReferences.some(t => t.slug === textPlain) ? textPlain : ''
    const finalStyleRefSlug = (styleRefSlug || fallbackStyleRefSlug).trim()

    if (finalStyleRefSlug) {
      e.preventDefault()
      e.stopPropagation()

      if (!brandSlug) {
        setAttachmentError('Select a brand before attaching style references.')
        return
      }

      attachStyleReference(finalStyleRefSlug)
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
    attachStyleReference,
    brandSlug,
    clearDrag,
    getDragData,
    products,
    setAttachmentError,
    styleReferences,
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

      {/* Header - Mode tabs only (top level navigation) */}
      <div className="flex items-center justify-center px-6 pt-4 pb-2 bg-transparent z-10">
        <PanelModeToggle value={panelMode} onChange={setPanelMode} disabled={!brandSlug}/>
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

      {/* Assistant Mode - hidden when playground active (keeps state) */}
      <div className={panelMode==='assistant'?'flex flex-col flex-1 min-h-0':'hidden'}>
        {/* Assistant subheader: Project selector + New Chat */}
        <div className="flex items-center justify-between px-4 pb-2">
          <ProjectSelector projects={projects} activeProject={activeProject} onSelect={setActiveProject} disabled={isLoading||!brandSlug}/>
          <Button variant="ghost" size="sm" onClick={()=>{clearMessages();clearAttachments();clearStyleReferenceAttachments();setInputText('')}} disabled={isLoading||messages.length===0} className="gap-2 text-xs font-medium h-8 rounded-full bg-white/50 dark:bg-white/10 hover:bg-white dark:hover:bg-white/20 border border-transparent hover:border-black/5 dark:hover:border-white/10 shadow-sm transition-all text-muted-foreground hover:text-foreground"><Plus className="w-3.5 h-3.5"/><span>New Chat</span></Button>
        </div>
        <ScrollArea className="flex-1">
          <div className="px-4 pb-4 max-w-3xl mx-auto w-full">
            {/* TodoList is now rendered inline with the message turn via MessageList */}
            <MessageList messages={messages} loadedSkills={loadedSkills} thinkingSteps={thinkingSteps} isLoading={isLoading} products={products} onInteractionSelect={async(messageId,selection)=>{resolveInteraction(messageId);await sendMessage(selection,{image_aspect_ratio:imageAspectRatio,video_aspect_ratio:videoAspectRatio});await refreshProducts()}} onRegenerate={regenerateMessage} todoList={todoList} isPaused={isPaused} onPause={handlePause} onResume={handleResume} onStop={handleStop} onNewDirection={handleNewDirection}/>
            {isLoading&&(imageBatch.tickets.size>0||imageBatch.expectedCount>0)&&(<div className="mt-2"><ImageBatchCard tickets={imageBatch.tickets} expectedCount={imageBatch.expectedCount}/></div>)}
          </div>
        </ScrollArea>
        {/* Chips row */}
        <div className="px-4 max-w-3xl mx-auto w-full">
          <AttachmentChips products={products} attachedProductSlugs={combinedAttachments.products} onDetachProduct={handleDetachProduct} styleReferences={styleReferences} attachedStyleReferences={combinedAttachments.styleReferences} onDetachStyleReference={handleDetachStyleReference} attachments={attachments} onRemoveAttachment={removeAttachment}/>
        </div>
        {/* Controls row */}
        <div className="px-4 max-w-3xl mx-auto w-full flex items-center gap-2 py-1">
          <GenerationSettings imageAspectRatio={imageAspectRatio} videoAspectRatio={videoAspectRatio as VideoAspectRatio} onImageAspectRatioChange={setImageAspectRatio} onVideoAspectRatioChange={setVideoAspectRatio} disabled={isLoading||!brandSlug}/>
          <AutonomyToggle enabled={autonomyMode} onChange={handleSetAutonomyMode} disabled={isLoading||!brandSlug}/>
        </div>
        {/* Approval Prompt - Above input when pending */}
        {pendingApproval&&(<div className="px-4 pb-2 w-full max-w-3xl mx-auto"><ApprovalPrompt request={pendingApproval} onApproveAll={handleApproveAll} onLetMeClarify={handleLetMeClarify}/></div>)}
        {/* Input Area - Clean, no gradient background */}
        <div className="px-4 pb-6 pt-2 w-full max-w-3xl mx-auto z-20">
          <MessageInput ref={messageInputRef} disabled={isLoading||!brandSlug} isGenerating={isLoading} onCancel={cancelGeneration} placeholder="" onMessageChange={setInputText} onSend={async(text)=>{const mentionAtts=resolveMentions(text,products,styleReferences);const allProducts=[...new Set([...attachedProducts,...mentionAtts.products])];const srMap=new Map<string,AttachedStyleReference>();for(const t of mentionAtts.styleReferences)srMap.set(t.style_reference_slug,t);for(const t of attachedStyleReferences)srMap.set(t.style_reference_slug,t);const allStyleRefs=Array.from(srMap.values());await sendMessage(text,{project_slug:activeProject,attached_products:allProducts.length>0?allProducts:undefined,attached_style_references:allStyleRefs.length>0?allStyleRefs:undefined,image_aspect_ratio:imageAspectRatio,video_aspect_ratio:videoAspectRatio});await refreshProducts()}} canSendWithoutText={attachments.length>0} onSelectImages={handleSelectImages} hasProducts={products.length>0} hasStyleReferences={styleReferences.length>0}/>
        </div>
      </div>
      {/* Playground Mode - hidden when assistant active (keeps state) */}
      <div className={panelMode==='playground'?'flex flex-col flex-1 min-h-0':'hidden'}>
        <PlaygroundMode brandSlug={brandSlug}/>
      </div>
          </main >
  )
}
