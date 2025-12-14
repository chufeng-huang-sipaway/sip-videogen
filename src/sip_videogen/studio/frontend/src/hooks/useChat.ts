import { useState, useCallback, useRef, useEffect } from 'react'
import { bridge, isPyWebView } from '@/lib/bridge'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  images: string[]
  timestamp: Date
  status: 'sending' | 'sent' | 'error'
  error?: string
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

export function useChat(brandSlug: string | null) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState('')
  const [error, setError] = useState<string | null>(null)
  const progressInterval = useRef<ReturnType<typeof setInterval> | null>(null)

  // Clear messages when brand changes
  useEffect(() => {
    setMessages([])
    setError(null)
  }, [brandSlug])

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading || !brandSlug) return

    setError(null)
    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: content.trim(),
      images: [],
      timestamp: new Date(),
      status: 'sent',
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
          const status = await bridge.getProgress()
          if (status) setProgress(status)
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
                content: `This is a mock response to: "${content}"\n\nIn production, this will connect to the Brand Advisor agent.`,
                images: [],
                status: 'sent'
              }
            : m
        ))
        return
      }

      const result = await bridge.chat(content)
      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, content: result.response, images: result.images, status: 'sent' }
          : m
      ))
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
      setIsLoading(false)
    }
  }, [isLoading, brandSlug])

  const clearMessages = useCallback(() => {
    setMessages([])
    setError(null)
    if (isPyWebView()) bridge.clearChat().catch(() => {})
  }, [])

  return { messages, isLoading, progress, error, sendMessage, clearMessages }
}
