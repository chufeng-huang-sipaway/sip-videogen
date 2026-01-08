import { useState, useCallback, useRef, useEffect } from 'react'
import { bridge, isPyWebView, type ChatAttachment, type ExecutionEvent, type Interaction, type ActivityEventType, type ChatContext, type GeneratedImage, type GeneratedVideo, type AttachedStyleReference, type ImageStatusEntry, type RegisterImageInput, type ThinkingStep } from '@/lib/bridge'
import type{TodoListData,TodoUpdateData,TodoItemData}from'@/lib/types/todo'
import type{ApprovalRequestData}from'@/lib/types/approval'
import { getAllowedAttachmentExts, getAllowedImageExts } from '@/lib/constants'
import { DEFAULT_ASPECT_RATIO, DEFAULT_GENERATION_MODE, type AspectRatio, type GenerationMode } from '@/types/aspectRatio'
import type { SetStateAction } from 'react'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  images: GeneratedImage[] | string[]
  videos?: GeneratedVideo[]
  timestamp: Date
  status: 'sending' | 'sent' | 'error'
  error?: string
  executionTrace?: ExecutionEvent[]
  interaction?: Interaction | null
  interactionResolved?: boolean
  memoryUpdate?: { message: string } | null
  attachments?: Array<{
    id: string
    name: string
    preview?: string
    path?: string
    source?: 'upload' | 'asset'
  }>
  /** Product slugs that were attached when this message was sent */
  attachedProductSlugs?: string[]
  /** Style references that were attached when this message was sent */
  attachedStyleReferences?: AttachedStyleReference[]
  /** Thinking steps parsed from executionTrace for completed messages */
  thinkingSteps?: ThinkingStep[]
  /** Skills that were loaded during generation of this message */
  loadedSkills?: string[]
}

interface PendingAttachment extends ChatAttachment {
  id: string
  preview?: string
}


function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

function getExt(name: string): string {
  const idx = name.lastIndexOf('.')
  return idx >= 0 ? name.slice(idx).toLowerCase() : ''
}

import type{GeneratedImage as WorkstationMedia}from'@/context/WorkstationContext'
interface UseChatOptions {
  onStyleReferencesCreated?: (slugs: string[]) => void
  onImagesGenerated?: (images: ImageStatusEntry[]) => void
  onVideosGenerated?: (videos: WorkstationMedia[]) => void
}

export function useChat(brandSlug: string | null, options?: UseChatOptions) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState('')
  const [progressType, setProgressType] = useState<ActivityEventType>('')
  const [loadedSkills, setLoadedSkills] = useState<string[]>([])
  const loadedSkillsRef = useRef<string[]>([])
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([])
  const thinkingStepsRef = useRef<ThinkingStep[]>([])
  const [error, setError] = useState<string | null>(null)
  const [attachmentError, setAttachmentError] = useState<string | null>(null)
  const [attachments, setAttachments] = useState<PendingAttachment[]>([])
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>(DEFAULT_ASPECT_RATIO)
  const [generationMode, setGenerationMode] = useState<GenerationMode>(DEFAULT_GENERATION_MODE)
  //Todo list state
  const [todoList,setTodoList]=useState<TodoListData|null>(null)
  const [isPaused,setIsPaused]=useState(false)
  //Approval state
  const [pendingApproval,setPendingApproval]=useState<ApprovalRequestData|null>(null)
  const [autonomyMode,setAutonomyMode]=useState(false)
  const progressInterval = useRef<ReturnType<typeof setInterval> | null>(null)
  const attachmentsRef = useRef<PendingAttachment[]>([])
  const requestIdRef = useRef(0)
  const cancelledRequestIdRef = useRef<number | null>(null)
  //Register global handler for pushed thinking steps (works around PyWebView concurrency)
  useEffect(()=>{
    const handler=(step:ThinkingStep)=>{
      const prev=thinkingStepsRef.current
      const byId=new Map(prev.map(s=>[s.id,s]))
      const ex=byId.get(step.id)
      if(ex){
        if(ex.status==='pending'&&(step.status==='complete'||step.status==='failed')){
          byId.set(step.id,{...ex,status:step.status,detail:step.detail??ex.detail})
        }else if(step.detail&&(!ex.detail||step.detail.length>ex.detail.length)){
          byId.set(step.id,{...ex,detail:step.detail})
        }else return //No change
      }else{byId.set(step.id,step)}
      const sorted=Array.from(byId.values()).sort((a,b)=>(a.seq??0)-(b.seq??0))
      thinkingStepsRef.current=sorted
      setThinkingSteps(sorted)
    }
    ;(window as unknown as{__onThinkingStep?:(s:ThinkingStep)=>void}).__onThinkingStep=handler
    return()=>{(window as unknown as{__onThinkingStep?:unknown}).__onThinkingStep=undefined}
  },[])
  //Register todo list event handlers
  useEffect(()=>{
    const w=window as unknown as{
      __onTodoList?:(d:TodoListData)=>void
      __onTodoUpdate?:(d:TodoUpdateData)=>void
      __onTodoCleared?:()=>void
      __onTodoCompleted?:(d:{id:string})=>void
      __onTodoInterrupted?:(d:{id:string;reason:string})=>void
      __onInterruptStatus?:(d:{signal:string|null})=>void
    }
    //Full todo list created
    w.__onTodoList=(d)=>setTodoList(d)
    //Item update - handles status, outputs (delta), AND error
    w.__onTodoUpdate=(u)=>{
      setTodoList(prev=>{
        if(!prev)return null
        return{...prev,items:prev.items.map(item=>item.id===u.itemId?{
          ...item,
          status:u.status as TodoItemData['status'],
          outputs:u.outputs?[...(item.outputs||[]),...u.outputs]:item.outputs,
          error:u.error??item.error,
        }:item)}
      })
    }
    //Todo cleared
    w.__onTodoCleared=()=>setTodoList(null)
    //Todo completed
    w.__onTodoCompleted=(d)=>{
      setTodoList(prev=>prev?.id===d.id?{...prev,completedAt:new Date().toISOString()}:prev)
    }
    //Todo interrupted (only for stop/new_direction, NOT pause)
    w.__onTodoInterrupted=(d)=>{
      setTodoList(prev=>prev?.id===d.id?{...prev,interruptedAt:new Date().toISOString(),interruptReason:d.reason}:prev)
    }
    //Interrupt status (includes pause)
    w.__onInterruptStatus=(d)=>{setIsPaused(d.signal==='pause')}
    return()=>{
      w.__onTodoList=undefined
      w.__onTodoUpdate=undefined
      w.__onTodoCleared=undefined
      w.__onTodoCompleted=undefined
      w.__onTodoInterrupted=undefined
      w.__onInterruptStatus=undefined
    }
  },[])
  //Register approval event handlers
  useEffect(()=>{
    const w=window as unknown as{
      __onApprovalRequest?:(d:ApprovalRequestData)=>void
      __onApprovalCleared?:()=>void
    }
    //Approval request - show prompt
    w.__onApprovalRequest=(d)=>setPendingApproval(d)
    //Approval cleared - hide prompt
    w.__onApprovalCleared=()=>setPendingApproval(null)
    return()=>{
      w.__onApprovalRequest=undefined
      w.__onApprovalCleared=undefined
    }
  },[])

  useEffect(() => {
    attachmentsRef.current = attachments
  }, [attachments])

//Clear messages when brand changes, load persisted preferences from backend
  useEffect(() => {
    //Mark current request as cancelled so late responses are ignored
    if(requestIdRef.current>0)cancelledRequestIdRef.current=requestIdRef.current
    setMessages([])
    setError(null)
    setAttachments([])
    setAttachmentError(null)
    setIsLoading(false)
    //Load persisted preferences from backend config file
    if(brandSlug&&isPyWebView()){
      bridge.getChatPrefs(brandSlug).then(prefs=>{
        if(prefs.aspect_ratio)setAspectRatio(prefs.aspect_ratio as AspectRatio)
        else setAspectRatio(DEFAULT_ASPECT_RATIO)
        if(prefs.generation_mode)setGenerationMode(prefs.generation_mode as GenerationMode)
        else setGenerationMode(DEFAULT_GENERATION_MODE)
      }).catch(()=>{setAspectRatio(DEFAULT_ASPECT_RATIO);setGenerationMode(DEFAULT_GENERATION_MODE)})
    }else{setAspectRatio(DEFAULT_ASPECT_RATIO);setGenerationMode(DEFAULT_GENERATION_MODE)}
  }, [brandSlug])

  const addFilesAsAttachments = useCallback(async (files: File[]) => {
    const prepared: PendingAttachment[] = []
    const allowedAttachmentExts = getAllowedAttachmentExts()

    for (const file of files) {
      const ext = getExt(file.name)
      if (ext && !allowedAttachmentExts.has(ext)) {
        setAttachmentError(`Unsupported file type: ${ext}`)
        continue
      }

      const reader = new FileReader()
      const attachmentPromise = new Promise<PendingAttachment>((resolve, reject) => {
        reader.onload = () => {
          const dataUrl = reader.result as string
          const base64 = dataUrl.split(',')[1] || ''
          resolve({
            id: generateId(),
            name: file.name,
            data: base64,
            preview: dataUrl,
            mime: file.type,
            source: 'upload',
          })
        }
        reader.onerror = () => reject(reader.error)
      })

      try {
        reader.readAsDataURL(file)
        const attachment = await attachmentPromise
        prepared.push(attachment)
      } catch {
        setAttachmentError(`Failed to read file: ${file.name}`)
      }
    }

    if (prepared.length > 0) {
      setAttachmentError(null)
      setAttachments(prev => [...prev, ...prepared])
    }
  }, [])

  const addAttachmentReference = useCallback(async (path: string, name?: string) => {
    const fileName = name || path.split('/').pop() || path
    const ext = getExt(fileName).toLowerCase()
    const isImage=getAllowedImageExts().includes(ext)

    let preview: string | undefined
    if (isImage && isPyWebView()) {
      try {
        preview = await bridge.getAssetThumbnail(path)
      } catch {
        // Fallback to no preview if thumbnail load fails
      }
    }

    setAttachments(prev => [
      ...prev,
      {
        id: generateId(),
        name: fileName,
        preview,
        path,
        source: 'asset',
      },
    ])
  }, [])

  const removeAttachment = useCallback((id: string) => {
    setAttachments(prev => prev.filter(att => att.id !== id))
  }, [])

  const resolveInteraction = useCallback((messageId: string) => {
    setMessages(prev => prev.map(m =>
      m.id === messageId ? { ...m, interactionResolved: true } : m
    ))
  }, [])

  const sendMessage = useCallback(async (content: string, context?: ChatContext) => {
    const hasAttachments = attachmentsRef.current.length > 0
    if (!content.trim() && !hasAttachments) return
    if (isLoading || !brandSlug) return
    const requestId = ++requestIdRef.current
    cancelledRequestIdRef.current = null

    const trimmed = content.trim()
    const payloadAttachments: ChatAttachment[] = attachmentsRef.current.map(
      ({ name, data, path, mime, source }) => ({
        name,
        data,
        path,
        mime,
        source,
      })
    )
    const attachmentDisplay = attachmentsRef.current.map(({ id, name, preview, path, source }) => ({
      id,
      name,
      preview,
      path,
      source,
    }))

    const finalContent = trimmed || (hasAttachments ? 'Please review the attached files.' : '')

    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: finalContent,
      images: [],
      timestamp: new Date(),
      status: 'sent',
      attachments: attachmentDisplay.length ? attachmentDisplay : undefined,
      attachedProductSlugs: context?.attached_products?.length
        ? [...context.attached_products]
        : undefined,
      attachedStyleReferences: context?.attached_style_references?.length
        ? [...context.attached_style_references]
        : undefined,
    }

    const assistantId = generateId()
    const assistantMessage: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      images: [],
      timestamp: new Date(),
      status: 'sending',
    }

    setMessages(prev => [...prev, userMessage, assistantMessage])
    setIsLoading(true)

    //Clear thinking steps and skills at start
    setThinkingSteps([])
    thinkingStepsRef.current=[]
    setLoadedSkills([])
    loadedSkillsRef.current = []
    //Try polling for progress (may not work due to PyWebView concurrency)
    if (isPyWebView()) {
      progressInterval.current = setInterval(async () => {
        try {
          const ps = await bridge.getProgress()
          if (ps.status) { setProgress(ps.status); setProgressType(ps.type || '') }
          //Accumulate skills with ref (closure-safe)
          if (ps.skills && ps.skills.length > 0) {
            const nu = ps.skills.filter((s: string) => !loadedSkillsRef.current.includes(s))
            if (nu.length > 0) { loadedSkillsRef.current = [...loadedSkillsRef.current, ...nu]; setLoadedSkills([...loadedSkillsRef.current]) }
          }
          //Upsert thinking steps by id, sort by seq, handle status transitions
          if (ps.thinking_steps && ps.thinking_steps.length > 0) {
            setThinkingSteps(prev => {
              const byId = new Map(prev.map(s => [s.id, s]))
              let changed = false
              for (const s of ps.thinking_steps) {
                const ex = byId.get(s.id)
                if (ex) {
                  //Status monotonicity: pending -> complete/failed only
                  if (ex.status === 'pending' && (s.status === 'complete' || s.status === 'failed')) {
                    byId.set(s.id, { ...ex, status: s.status, detail: s.detail ?? ex.detail })
                    changed = true
                  } else if (s.detail && (!ex.detail || s.detail.length > ex.detail.length)) {
                    byId.set(s.id, { ...ex, detail: s.detail })
                    changed = true
                  }
                } else {
                  byId.set(s.id, s)
                  changed = true
                }
              }
              if (!changed) return prev
              return Array.from(byId.values()).sort((a, b) => (a.seq ?? 0) - (b.seq ?? 0))
            })
          }
        } catch { /* Ignore - concurrent calls may fail in PyWebView */ }
      }, 500)
    }

    try {
      // Mock response for development mode
      if (!isPyWebView()) {
        await new Promise(r => setTimeout(r, 1000))
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? {
                ...m,
                content: `This is a mock response to: "${finalContent}"\n\nIn production, this will connect to the Brand Advisor agent.`,
                images: [],
                executionTrace: [],
                status: 'sent',
              }
            : m
        ))
        setAttachments([])
        return
      }

      const result = await bridge.chat(finalContent, payloadAttachments, context)
      if (cancelledRequestIdRef.current === requestId) { return }
      //Extract thinking steps from execution trace for persistence
      const stepsFromTrace = (result.execution_trace || []).filter(e => e.type === 'thinking_step').map((e, i) => ({ id: `trace-${e.timestamp}-${i}`, step: e.message, detail: e.detail, timestamp: e.timestamp }))
      //Persist skills with message (use ref for latest values)
      const finalSkills = loadedSkillsRef.current.length > 0 ? [...loadedSkillsRef.current] : undefined
      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, content: result.response, images: result.images, videos: result.videos || [], executionTrace: result.execution_trace || [], interaction: result.interaction, memoryUpdate: result.memory_update, status: 'sent', thinkingSteps: stepsFromTrace, loadedSkills: finalSkills }
          : m
      ))
      setAttachments([])
      setAttachmentError(null)
      //Notify if style references were created
      if (result.style_references?.length && options?.onStyleReferencesCreated) {
        options.onStyleReferencesCreated(result.style_references)
      }
      //Register generated images and notify workstation
      if (result.images?.length && options?.onImagesGenerated) {
        const inputs: RegisterImageInput[] = []
        for (const img of result.images) {
          const rawPath = img.path
          const path = rawPath?.startsWith('file://') ? rawPath.slice('file://'.length) : rawPath
          if (!path || path.startsWith('data:')) continue
          const sourceStyleReferencePath = img.metadata?.reference_image ?? img.metadata?.reference_images?.[0]
          inputs.push({ path, prompt: img.metadata?.prompt, sourceStyleReferencePath })
        }
        try {
          const registered = inputs.length ? await bridge.registerGeneratedImages(inputs) : []
          if (registered.length) {
            const registeredByPath = new Map(registered.map(entry => [entry.originalPath, entry]))
            setMessages(prev => prev.map(m => {
              if (m.id !== assistantId) return m
              const images = (result.images || []).map(img => {
                if (typeof img === 'string') return img
                const entry = img.path ? registeredByPath.get(img.path) : undefined
                return { ...img, id: entry?.id, path: entry?.currentPath ?? img.path, sourceStyleReferencePath: entry?.sourceStyleReferencePath ?? img.metadata?.reference_image ?? img.metadata?.reference_images?.[0] }
              })
              return { ...m, images }
            }))
          }
          if (registered.length) {
            options.onImagesGenerated(registered)
          }
        } catch { /* ignore registration errors */ }
      }
      //Register generated videos to Workstation
      if(result.videos?.length&&options?.onVideosGenerated){
        const videoItems:WorkstationMedia[]=result.videos.map(vid=>({
          id:vid.path||`vid_${Date.now()}_${Math.random().toString(36).slice(2,7)}`,
          path:'',
          originalPath:vid.path,
          prompt:vid.metadata?.prompt,
          timestamp:vid.metadata?.generated_at||new Date().toISOString(),
          viewedAt:null,
          type:'video'as const,
          conceptImagePath:vid.metadata?.concept_image_path||undefined,
        }))
        if(videoItems.length)options.onVideosGenerated(videoItems)
      }
    } catch (err) {
      if (cancelledRequestIdRef.current === requestId) {
        return
      }
      const msg = err instanceof Error ? err.message : 'Unknown error'
      setError(msg)
      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, content: 'Sorry, something went wrong.', status: 'error', error: msg }
          : m
      ))
    } finally {
      if (progressInterval.current) { clearInterval(progressInterval.current); progressInterval.current = null }
      setProgress(''); setProgressType(''); setLoadedSkills([]); setThinkingSteps([]); thinkingStepsRef.current=[]; setIsLoading(false)
    }
  }, [brandSlug, isLoading])

//Wrapper setters that persist to backend config file
  const setAspectRatioWithPersist=useCallback((action:SetStateAction<AspectRatio>)=>{
    setAspectRatio(prev=>{
      const next=typeof action==='function'?action(prev):action
      if(brandSlug&&isPyWebView())bridge.saveChatPrefs(brandSlug,next,undefined).catch(()=>{})
      return next
    })
  },[brandSlug])
  const setGenerationModeWithPersist=useCallback((action:SetStateAction<GenerationMode>)=>{
    setGenerationMode(prev=>{
      const next=typeof action==='function'?action(prev):action
      if(brandSlug&&isPyWebView())bridge.saveChatPrefs(brandSlug,undefined,next).catch(()=>{})
      return next
    })
  },[brandSlug])

const clearMessages = useCallback(() => {
    setMessages([])
    setError(null)
    setAttachments([])
    setAttachmentError(null)
    //Preserve aspect ratio and generation mode (user preferences)
    if (isPyWebView()) bridge.clearChat().catch(() => {})
  }, [])

  const cancelGeneration = useCallback(async () => {
    if (!isLoading) return
    cancelledRequestIdRef.current = requestIdRef.current
    try { if (isPyWebView()) await bridge.cancelGeneration() } catch { /* ignore */ }
    if (progressInterval.current) { clearInterval(progressInterval.current); progressInterval.current = null }
    setProgress(''); setProgressType(''); setLoadedSkills([]); setIsLoading(false)
    setMessages(prev => prev.map(m => m.status === 'sending' ? { ...m, content: 'Generation cancelled.', status: 'sent' } : m))
  }, [isLoading])

  const regenerateMessage = useCallback(async (assistantMessageId: string) => {
    if (isLoading || !brandSlug) return

    // Find the assistant message index
    const assistantIdx = messages.findIndex(m => m.id === assistantMessageId)
    if (assistantIdx === -1) return

    // Find the preceding user message
    let userMsgIdx = assistantIdx - 1
    while (userMsgIdx >= 0 && messages[userMsgIdx].role !== 'user') {
      userMsgIdx--
    }
    if (userMsgIdx < 0) return

    const userMessage = messages[userMsgIdx]

    // Get all messages before this user-assistant exchange
    const priorMessages = messages.slice(0, userMsgIdx)

    // Clear backend conversation completely
    if (isPyWebView()) {
      await bridge.clearChat()
    }

    // Update frontend state to remove the exchange we're regenerating
    setMessages(priorMessages)
    setError(null)
    setAttachments([])
    setAttachmentError(null)

    // Re-send the user message to get a new response
    await sendMessage(userMessage.content, {
      attached_products: userMessage.attachedProductSlugs,
      attached_style_references: userMessage.attachedStyleReferences,
      aspect_ratio: aspectRatio,
      generation_mode: generationMode,
    })
  }, [messages, isLoading, brandSlug, sendMessage, aspectRatio, generationMode])
  //Todo list control handlers
  const handlePause=useCallback(async()=>{
    await bridge.interruptTask('pause')
  },[])
  const handleResume=useCallback(async()=>{
    await bridge.resumeTask()
    setIsPaused(false)
  },[])
  const handleStop=useCallback(async()=>{
    await bridge.interruptTask('stop')
  },[])
  const handleNewDirection=useCallback(async(msg:string)=>{
    await bridge.interruptTask('new_direction',msg)
  },[])
  //Approval handlers
  const handleApprove=useCallback(async()=>{
    if(!pendingApproval)return
    await bridge.respondToApproval(pendingApproval.id,'approve')
  },[pendingApproval])
  const handleApproveAll=useCallback(async()=>{
    if(!pendingApproval)return
    await bridge.respondToApproval(pendingApproval.id,'approve_all')
    setAutonomyMode(true)//UI reflects mode change
  },[pendingApproval])
  const handleModifyApproval=useCallback(async(newPrompt:string)=>{
    if(!pendingApproval)return
    await bridge.respondToApproval(pendingApproval.id,'modify',newPrompt)
  },[pendingApproval])
  const handleSkipApproval=useCallback(async()=>{
    if(!pendingApproval)return
    await bridge.respondToApproval(pendingApproval.id,'skip')
  },[pendingApproval])
  const handleSetAutonomyMode=useCallback(async(enabled:boolean)=>{
    await bridge.setAutonomyMode(enabled)
    setAutonomyMode(enabled)
  },[])

return {
    messages,
    isLoading,
    progress,
    progressType,
    loadedSkills,
    thinkingSteps,
    error,
    attachmentError,
    attachments,
    aspectRatio,
    generationMode,
    //Todo list state and handlers
    todoList,
    isPaused,
    handlePause,
    handleResume,
    handleStop,
    handleNewDirection,
    //Approval state and handlers
    pendingApproval,
    autonomyMode,
    handleApprove,
    handleApproveAll,
    handleModifyApproval,
    handleSkipApproval,
    handleSetAutonomyMode,
    sendMessage,
    clearMessages,
    cancelGeneration,
    regenerateMessage,
    resolveInteraction,
    addFilesAsAttachments,
    addAttachmentReference,
    removeAttachment,
    setAttachmentError,
    setAspectRatio: setAspectRatioWithPersist,
    setGenerationMode: setGenerationModeWithPersist,
  }
}
