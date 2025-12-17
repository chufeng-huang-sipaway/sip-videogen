import { useEffect, useRef, useState } from 'react'
import { Send, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface MessageInputProps {
  disabled?: boolean
  placeholder?: string
  onSend: (text: string) => void
  canSendWithoutText?: boolean
}

export function MessageInput({ disabled, placeholder, onSend, canSendWithoutText = false }: MessageInputProps) {
  const [message, setMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }, [message])

  const submit = () => {
    const text = message.trim()
    if (!text && !canSendWithoutText) return
    if (disabled) return
    onSend(text)
    setMessage('')
  }

  return (
    <div className="p-4 pb-6">
      <div className="relative flex items-end gap-2 p-2 rounded-[26px] bg-background border border-border/60 shadow-lg shadow-black/5 ring-1 ring-black/5 transition-shadow hover:shadow-xl hover:shadow-black/10 focus-within:shadow-xl focus-within:shadow-primary/5 focus-within:border-primary/20">
        <div className="pl-3 pb-2.5 text-muted-foreground">
          <Sparkles className="w-5 h-5 opacity-50" />
        </div>
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="flex-1 max-h-[160px] resize-none bg-transparent px-2 py-2.5 text-sm placeholder:text-muted-foreground/60 focus:outline-none disabled:opacity-50"
        />
        <Button
          type="button"
          size="icon"
          onClick={submit}
          disabled={disabled || (!message.trim() && !canSendWithoutText)}
          className="h-9 w-9 rounded-full shrink-0 mb-0.5 mr-0.5 transition-all duration-200 hover:scale-105 active:scale-95"
        >
          <Send className="h-4 w-4 ml-0.5" />
        </Button>
      </div>
    </div>
  )
}
