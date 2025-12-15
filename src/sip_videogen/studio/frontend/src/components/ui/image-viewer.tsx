import { Dialog, DialogContent } from '@/components/ui/dialog'
import { X } from 'lucide-react'

interface Props {
  src: string | null
  alt?: string
  onClose: () => void
}

export function ImageViewer({ src, alt, onClose }: Props) {
  if (!src) return null

  return (
    <Dialog open={!!src} onOpenChange={() => onClose()}>
      <DialogContent className="max-w-4xl p-0 overflow-hidden bg-black/90">
        <button
          onClick={onClose}
          className="absolute top-2 right-2 p-1 rounded-full bg-black/50 text-white hover:bg-black/70 z-10"
        >
          <X className="h-5 w-5" />
        </button>
        <img
          src={src}
          alt={alt || 'Preview'}
          className="w-full h-auto max-h-[80vh] object-contain"
        />
      </DialogContent>
    </Dialog>
  )
}
