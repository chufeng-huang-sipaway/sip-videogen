import { useState, useCallback, useRef, useEffect } from 'react'
import { bridge, isPyWebView, type ChatAttachment, type ExecutionEvent, type Interaction, type ActivityEventType, type ChatContext, type GeneratedImage, type GeneratedVideo, type AttachedTemplate, type ImageStatusEntry, type RegisterImageInput } from '@/lib/bridge'
import { getAllowedAttachmentExts, getAllowedImageExts } from '@/lib/constants'
import { DEFAULT_ASPECT_RATIO, type AspectRatio } from '@/types/aspectRatio'

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
  /** Templates that were attached when this message was sent */
  attachedTemplates?: AttachedTemplate[]
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

interface UseChatOptions {
  onTemplatesCreated?: (slugs: string[]) => void
  onImagesGenerated?: (images: ImageStatusEntry[]) => void
}

export function useChat(brandSlug: string | null, options?: UseChatOptions) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState('')
  const [progressType, setProgressType] = useState<ActivityEventType>('')
  const [loadedSkills, setLoadedSkills] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [attachmentError, setAttachmentError] = useState<string | null>(null)
  const [attachments, setAttachments] = useState<PendingAttachment[]>([])
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>(DEFAULT_ASPECT_RATIO)
  const progressInterval = useRef<ReturnType<typeof setInterval> | null>(null)
  const attachmentsRef = useRef<PendingAttachment[]>([])
  const requestIdRef = useRef(0)
  const cancelledRequestIdRef = useRef<number | null>(null)

  useEffect(() => {
    attachmentsRef.current = attachments
  }, [attachments])

//Clear messages when brand changes
  useEffect(() => {
    setMessages([])
    setError(null)
    setAttachments([])
    setAttachmentError(null)
    setAspectRatio(DEFAULT_ASPECT_RATIO)
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
      attachedTemplates: context?.attached_templates?.length
        ? [...context.attached_templates]
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

    // Try polling for progress (may not work due to PyWebView concurrency)
    if (isPyWebView()) {
      progressInterval.current = setInterval(async () => {
        try {
          const progressStatus = await bridge.getProgress()
          if (progressStatus.status) {
            setProgress(progressStatus.status)
            setProgressType(progressStatus.type || '')
          }
          // Always update skills (they accumulate during the request)
          if (progressStatus.skills && progressStatus.skills.length > 0) {
            setLoadedSkills(progressStatus.skills)
          }
        } catch {
          // Ignore - concurrent calls may fail in PyWebView
        }
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
      if (cancelledRequestIdRef.current === requestId) {
        return
      }
      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? {
              ...m,
              content: result.response,
              images: result.images,
              videos: result.videos || [],
              executionTrace: result.execution_trace || [],
              interaction: result.interaction,
              memoryUpdate: result.memory_update,
              status: 'sent',
            }
          : m
      ))
      setAttachments([])
      setAttachmentError(null)
      //Notify if templates were created
      if (result.templates?.length && options?.onTemplatesCreated) {
        options.onTemplatesCreated(result.templates)
      }
      //Register generated images and notify workstation
      if (result.images?.length && options?.onImagesGenerated) {
        const inputs: RegisterImageInput[] = []
        for (const img of result.images) {
          const rawPath = img.path
          const path = rawPath?.startsWith('file://') ? rawPath.slice('file://'.length) : rawPath
          if (!path || path.startsWith('data:')) continue
          const sourceTemplatePath = img.metadata?.reference_image ?? img.metadata?.reference_images?.[0]
          inputs.push({ path, prompt: img.metadata?.prompt, sourceTemplatePath })
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
                return { ...img, id: entry?.id, path: entry?.currentPath ?? img.path, sourceTemplatePath: entry?.sourceTemplatePath ?? img.metadata?.reference_image ?? img.metadata?.reference_images?.[0] }
              })
              return { ...m, images }
            }))
          }
          if (registered.length) {
            options.onImagesGenerated(registered)
          }
        } catch { /* ignore registration errors */ }
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
      if (progressInterval.current) {
        clearInterval(progressInterval.current)
        progressInterval.current = null
      }
      setProgress('')
      setProgressType('')
      setLoadedSkills([])
      setIsLoading(false)
    }
  }, [brandSlug, isLoading])

const clearMessages = useCallback(() => {
    setMessages([])
    setError(null)
    setAttachments([])
    setAttachmentError(null)
    setAspectRatio(DEFAULT_ASPECT_RATIO)
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
      attached_templates: userMessage.attachedTemplates,
    })
  }, [messages, isLoading, brandSlug, sendMessage])

return {
    messages,
    isLoading,
    progress,
    progressType,
    loadedSkills,
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
  }
}
