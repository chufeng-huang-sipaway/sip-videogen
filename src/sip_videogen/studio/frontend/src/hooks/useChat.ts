import { useState, useCallback, useRef, useEffect } from 'react'
import { bridge, isPyWebView, type ChatAttachment, type ExecutionEvent, type Interaction, type ActivityEventType, type ChatContext, type GeneratedImage } from '@/lib/bridge'
import { ALLOWED_ATTACHMENT_EXTS, ALLOWED_IMAGE_EXTS } from '@/lib/constants'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  images: GeneratedImage[] | string[]
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

export function useChat(brandSlug: string | null) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState('')
  const [progressType, setProgressType] = useState<ActivityEventType>('')
  const [loadedSkills, setLoadedSkills] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [attachmentError, setAttachmentError] = useState<string | null>(null)
  const [attachments, setAttachments] = useState<PendingAttachment[]>([])
  const progressInterval = useRef<ReturnType<typeof setInterval> | null>(null)
  const attachmentsRef = useRef<PendingAttachment[]>([])

  useEffect(() => {
    attachmentsRef.current = attachments
  }, [attachments])

  // Clear messages when brand changes
  useEffect(() => {
    setMessages([])
    setError(null)
    setAttachments([])
    setAttachmentError(null)
  }, [brandSlug])

  const addFilesAsAttachments = useCallback(async (files: File[]) => {
    const prepared: PendingAttachment[] = []

    for (const file of files) {
      const ext = getExt(file.name)
      if (ext && !ALLOWED_ATTACHMENT_EXTS.has(ext)) {
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
    const isImage=(ALLOWED_IMAGE_EXTS as readonly string[]).includes(ext)

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
      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? {
              ...m,
              content: result.response,
              images: result.images,
              executionTrace: result.execution_trace || [],
              interaction: result.interaction,
              memoryUpdate: result.memory_update,
              status: 'sent',
            }
          : m
      ))
      setAttachments([])
      setAttachmentError(null)
    } catch (err) {
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
    if (isPyWebView()) bridge.clearChat().catch(() => {})
  }, [])

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
    sendMessage,
    clearMessages,
    regenerateMessage,
    resolveInteraction,
    addFilesAsAttachments,
    addAttachmentReference,
    removeAttachment,
    setAttachmentError,
  }
}
