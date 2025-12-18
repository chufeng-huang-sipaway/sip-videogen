import { useEffect, useRef, useState } from 'react'
import { Send, Plus, ImagePlus, Package } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface MessageInputProps {
  disabled?: boolean
  placeholder?: string
  onSend: (text: string) => void
  canSendWithoutText?: boolean
  onSelectImages?: (files: File[]) => void
  onOpenProductPicker?: () => void
  hasProducts?: boolean
}

export function MessageInput({
  disabled,
  placeholder,
  onSend,
  canSendWithoutText = false,
  onSelectImages,
  onOpenProductPicker,
  hasProducts = false,
}: MessageInputProps) {
  const [message, setMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0 && onSelectImages) {
      onSelectImages(Array.from(files))
    }
    // Reset input so the same file can be selected again
    e.target.value = ''
  }

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
      <div className="relative flex items-center gap-2 px-2 py-2 rounded-2xl bg-background border border-border/40 shadow-sm transition-all duration-300 hover:shadow-md focus-within:shadow-lg focus-within:border-primary/30 group">

        {/* Hidden file input for image selection */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={handleFileSelect}
        />

        {/* Attachment Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 shrink-0 text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted/50 transition-colors rounded-lg"
              disabled={disabled}
            >
              <Plus className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-48">
            <DropdownMenuItem
              onClick={() => fileInputRef.current?.click()}
              className="cursor-pointer"
            >
              <ImagePlus className="h-4 w-4 mr-2" />
              Upload Image
            </DropdownMenuItem>
            {hasProducts && onOpenProductPicker && (
              <DropdownMenuItem
                onClick={onOpenProductPicker}
                className="cursor-pointer"
              >
                <Package className="h-4 w-4 mr-2" />
                Select Product
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

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
          className="flex-1 max-h-[160px] resize-none bg-transparent py-2 text-sm placeholder:text-muted-foreground/40 focus:outline-none disabled:opacity-50 min-h-[36px] leading-relaxed"
        />

        <div className="flex items-center shrink-0">
          <Button
            type="button"
            size="icon"
            onClick={submit}
            disabled={disabled || (!message.trim() && !canSendWithoutText)}
            className="h-8 w-8 rounded-lg shrink-0 transition-all duration-200 bg-primary hover:bg-primary/90 text-primary-foreground active:scale-95 disabled:opacity-30 disabled:bg-muted disabled:text-muted-foreground"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
