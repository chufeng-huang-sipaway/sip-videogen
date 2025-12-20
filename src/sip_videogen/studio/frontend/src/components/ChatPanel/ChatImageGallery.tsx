import { useState } from 'react'
import { Info } from 'lucide-react'
import { ImageViewer } from '@/components/ui/image-viewer'
import { PromptDetailsModal } from './PromptDetailsModal'
import type { GeneratedImage, ImageGenerationMetadata } from '@/lib/bridge'

interface ChatImageGalleryProps {
  images: GeneratedImage[] | string[]
}

export function ChatImageGallery({ images }: ChatImageGalleryProps) {
  const [previewSrc, setPreviewSrc] = useState<string | null>(null)
  const [selectedMetadata, setSelectedMetadata] = useState<ImageGenerationMetadata | null>(null)

  if (images.length === 0) return null

  // Normalize to GeneratedImage format for backward compatibility
  const normalizedImages: GeneratedImage[] = images.map(img =>
    typeof img === 'string' ? { url: img } : img
  )

  // Dynamic column count based on image count
  const columnClass =
    normalizedImages.length === 1
      ? 'columns-1'
      : normalizedImages.length <= 3
        ? 'columns-2'
        : 'columns-3'

  return (
    <>
      <div className={`${columnClass} gap-2 mt-3`}>
        {normalizedImages.map((img, i) => (
          <div key={i} className="break-inside-avoid mb-2 relative group">
            <img
              src={img.url}
              alt=""
              onClick={() => setPreviewSrc(img.url)}
              className="w-full rounded-lg cursor-pointer hover:opacity-90 transition-opacity
                       border border-gray-200 dark:border-gray-700"
            />
            {/* Tooltip icon - top right corner, visible on hover */}
            {img.metadata && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setSelectedMetadata(img.metadata!)
                }}
                className="absolute top-2 right-2 p-1.5 rounded-full
                           bg-black/50 hover:bg-black/70 text-white
                           opacity-0 group-hover:opacity-100 transition-opacity"
                title="View prompt details"
              >
                <Info className="h-4 w-4" />
              </button>
            )}
          </div>
        ))}
      </div>
      <ImageViewer src={previewSrc} onClose={() => setPreviewSrc(null)} />
      <PromptDetailsModal
        metadata={selectedMetadata}
        onClose={() => setSelectedMetadata(null)}
      />
    </>
  )
}
