import { useState } from 'react'
import { ImageViewer } from '@/components/ui/image-viewer'

interface ChatImageGalleryProps {
  images: string[]
}

export function ChatImageGallery({ images }: ChatImageGalleryProps) {
  const [previewSrc, setPreviewSrc] = useState<string | null>(null)

  if (images.length === 0) return null

  // Dynamic column count based on image count
  const columnClass =
    images.length === 1
      ? 'columns-1'
      : images.length <= 3
        ? 'columns-2'
        : 'columns-3'

  return (
    <>
      <div className={`${columnClass} gap-2 mt-3`}>
        {images.map((src, i) => (
          <div key={i} className="break-inside-avoid mb-2">
            <img
              src={src}
              alt=""
              onClick={() => setPreviewSrc(src)}
              className="w-full rounded-lg cursor-pointer hover:opacity-90 transition-opacity
                       border border-gray-200 dark:border-gray-700"
            />
          </div>
        ))}
      </div>
      <ImageViewer src={previewSrc} onClose={() => setPreviewSrc(null)} />
    </>
  )
}
