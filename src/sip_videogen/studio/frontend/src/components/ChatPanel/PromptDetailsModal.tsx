import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { ImageGenerationMetadata } from '@/lib/bridge'

interface Props {
  metadata: ImageGenerationMetadata | null
  onClose: () => void
}

export function PromptDetailsModal({ metadata, onClose }: Props) {
  if (!metadata) return null

  return (
    <Dialog open={!!metadata} onOpenChange={() => onClose()}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Generation Details</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Prompt */}
          <div>
            <h4 className="text-sm font-medium text-muted-foreground mb-1">Prompt</h4>
            <pre className="bg-muted p-3 rounded-lg text-sm whitespace-pre-wrap font-mono">
              {metadata.prompt}
            </pre>
          </div>

          {/* API Parameters */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">Model</h4>
              <code className="text-sm bg-muted px-2 py-1 rounded">{metadata.model}</code>
            </div>
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">Aspect Ratio</h4>
              <code className="text-sm bg-muted px-2 py-1 rounded">{metadata.aspect_ratio}</code>
            </div>
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">Image Size</h4>
              <code className="text-sm bg-muted px-2 py-1 rounded">{metadata.image_size}</code>
            </div>
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">Generation Time</h4>
              <code className="text-sm bg-muted px-2 py-1 rounded">{metadata.generation_time_ms}ms</code>
            </div>
          </div>

          {/* Reference Image */}
          {metadata.reference_image && (
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">Reference Image</h4>
              <code className="text-sm bg-muted px-2 py-1 rounded break-all">
                {metadata.reference_image}
              </code>
            </div>
          )}

          {/* Products */}
          {metadata.product_slugs && metadata.product_slugs.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">Products Referenced</h4>
              <div className="flex flex-wrap gap-1">
                {metadata.product_slugs.map((slug) => (
                  <span
                    key={slug}
                    className="px-2 py-0.5 bg-primary/10 text-primary rounded text-sm"
                  >
                    {slug}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Validation */}
          {metadata.validate_identity && (
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">Identity Validation</h4>
              <span className="text-sm text-green-600 dark:text-green-400">Enabled</span>
            </div>
          )}

          {/* Timestamp */}
          <div className="text-xs text-muted-foreground border-t pt-3 mt-4">
            Generated: {new Date(metadata.generated_at).toLocaleString()}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
