import { useEffect, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog'
import type { Message } from '@/hooks/useChat'

interface MessageListProps {
  messages: Message[]
  progress: string
}

function ImageLightbox({ src }: { src: string }) {
  const [open, setOpen] = useState(false)

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <img
          src={src}
          alt=""
          className="rounded-lg cursor-pointer hover:opacity-90 transition max-h-48 object-cover"
        />
      </DialogTrigger>
      <DialogContent className="max-w-4xl">
        <img src={src} alt="" className="w-full h-auto" />
      </DialogContent>
    </Dialog>
  )
}

export function MessageList({ messages, progress }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, progress])

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center text-gray-500 p-8">
        <h2 className="text-xl font-semibold mb-2">Welcome to Brand Studio</h2>
        <p className="text-sm max-w-md">
          Select a brand, then ask me to generate on-brand marketing images or provide brand guidance.
        </p>
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[80%] rounded-2xl px-4 py-3 ${
              message.role === 'user'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 dark:bg-gray-800'
            }`}
          >
            {message.status === 'sending' ? (
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm">{message.content || progress || 'Thinking...'}</span>
              </div>
            ) : (
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
            )}

            {message.images.length > 0 && (
              <div className="mt-3 grid grid-cols-2 gap-2">
                {message.images.map((img, i) => (
                  <ImageLightbox key={i} src={img} />
                ))}
              </div>
            )}

            {message.status === 'error' && (
              <p className="text-xs text-red-500 mt-2">{message.error}</p>
            )}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
