import { useState, useCallback, useRef, useEffect } from 'react'
import { bridge, isPyWebView, type ChatAttachment, type ExecutionEvent, type Interaction, type ActivityEventType } from '@/lib/bridge'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  images: string[]
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
}

interface PendingAttachment extends ChatAttachment {
  id: string
  preview?: string
}

const ALLOWED_ATTACHMENT_EXTS = new Set([
  '.png',
  '.jpg',
  '.jpeg',
  '.gif',
  '.webp',
  '.svg',
  '.md',
  '.txt',
  '.json',
  '.yaml',
  '.yml',
])

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
    const isImage = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'].includes(ext)

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

  const sendMessage = useCallback(async (content: string) => {
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

      const result = await bridge.chat(finalContent, payloadAttachments)
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
    resolveInteraction,
    addFilesAsAttachments,
    addAttachmentReference,
    removeAttachment,
    setAttachmentError,
  }
}
