import { useEffect, useRef, useState } from 'react'
import { Send, Paperclip } from 'lucide-react'

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
      <div className="relative flex items-end gap-2 p-3 rounded-2xl bg-background border border-border/40 shadow-sm transition-all duration-300 hover:shadow-md focus-within:shadow-lg focus-within:border-primary/30 group">

        {/* Attachment Button */}
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 opacity-50 hover:opacity-100 transition-opacity rounded-xl"
          disabled={disabled}
        >
          <Paperclip className="h-4 w-4" />
        </Button>

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
          className="flex-1 max-h-[160px] resize-none bg-transparent px-2 py-2.5 text-sm placeholder:text-muted-foreground/40 focus:outline-none disabled:opacity-50 min-h-[44px] leading-relaxed"
        />

        <div className="flex items-center gap-2 mb-0.5">
          {/* Enter hint */}
          <div className="hidden group-focus-within:flex items-center gap-1 text-[10px] text-muted-foreground/30 font-medium mr-2 animate-in fade-in zoom-in-95 duration-200">
            <span>Enter to send</span>
          </div>

          <Button
            type="button"
            size="icon"
            onClick={submit}
            disabled={disabled || (!message.trim() && !canSendWithoutText)}
            className="h-9 w-9 rounded-xl shrink-0 transition-all duration-300 bg-primary/90 hover:bg-primary text-primary-foreground shadow-sm hover:shadow-primary/20 active:scale-95 disabled:opacity-20 disabled:bg-muted"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
