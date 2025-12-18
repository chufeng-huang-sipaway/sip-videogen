import { Dialog, DialogContent } from '@/components/ui/dialog'
import { X, FolderOpen } from 'lucide-react'
import { bridge, isPyWebView } from '@/lib/bridge'

interface Props {
  src: string | null
  alt?: string
  onClose: () => void
  /** File path for "Open in Finder" functionality (relative path within brand assets/documents) */
  filePath?: string
  /** Type of file - determines which bridge method to use */
  fileType?: 'asset' | 'document'
}

export function ImageViewer({ src, alt, onClose, filePath, fileType = 'asset' }: Props) {
  if (!src) return null

  const handleOpenInFinder = async () => {
    if (!filePath || !isPyWebView()) return
    try {
      if (fileType === 'document') {
        await bridge.openDocumentInFinder(filePath)
      } else {
        await bridge.openAssetInFinder(filePath)
      }
    } catch (err) {
      console.error('[ImageViewer] Failed to open in Finder:', err)
    }
  }

  return (
    <Dialog open={!!src} onOpenChange={() => onClose()}>
      <DialogContent className="max-w-4xl p-0 overflow-hidden bg-black/90">
        {/* Action buttons */}
        <div className="absolute top-2 right-2 flex items-center gap-1 z-10">
          {filePath && isPyWebView() && (
            <button
              onClick={handleOpenInFinder}
              className="p-1.5 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors"
              title="Open in Finder"
            >
              <FolderOpen className="h-4 w-4" />
            </button>
          )}
          <button
            onClick={onClose}
            className="p-1.5 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors"
            title="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <img
          src={src}
          alt={alt || 'Preview'}
          className="w-full h-auto max-h-[80vh] object-contain"
        />
      </DialogContent>
    </Dialog>
  )
}
