import { useEffect, useRef, useState } from 'react'
import { ArrowUp, Plus, Image, Package } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'

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
    <div className="relative w-full">
      <div className={cn(
        "relative flex items-end gap-2 p-2 rounded-[26px] bg-background shadow-float border border-border/10 transition-shadow duration-300 ring-1 ring-black/5",
        "focus-within:shadow-xl focus-within:ring-black/10"
      )}>

        {/* Hidden file input for image selection */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={handleFileSelect}
        />

        {/* Attachment Menu - Minimalist Circle */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-10 w-10 shrink-0 rounded-full text-muted-foreground hover:bg-muted/50 transition-colors mb-[1px]"
              disabled={disabled}
            >
              <Plus className="h-5 w-5" strokeWidth={1.5} />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-48 rounded-2xl shadow-float border-border/20 p-1.5" sideOffset={10}>
            <DropdownMenuItem
              onClick={() => fileInputRef.current?.click()}
              className="cursor-pointer gap-2 py-2.5 rounded-xl text-xs font-medium"
            >
              <Image className="h-4 w-4 opacity-70" />
              Upload Image
            </DropdownMenuItem>
            {hasProducts && onOpenProductPicker && (
              <DropdownMenuItem
                onClick={onOpenProductPicker}
                className="cursor-pointer gap-2 py-2.5 rounded-xl text-xs font-medium"
              >
                <Package className="h-4 w-4 opacity-70" />
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
          className="flex-1 max-h-[160px] resize-none bg-transparent py-3.5 text-sm placeholder:text-muted-foreground/50 focus:outline-none disabled:opacity-50 min-h-[44px] leading-relaxed"
        />

        <div className="flex items-center shrink-0 mb-[1px]">
          <Button
            type="button"
            size="icon"
            onClick={submit}
            disabled={disabled || (!message.trim() && !canSendWithoutText)}
            className="h-10 w-10 rounded-full shrink-0 transition-all duration-200 bg-foreground text-background hover:bg-foreground/90 active:scale-95 disabled:opacity-20 disabled:bg-muted disabled:text-muted-foreground shadow-sm"
          >
            <ArrowUp className="h-5 w-5" strokeWidth={2} />
          </Button>
        </div>
      </div>
    </div>
  )
}
