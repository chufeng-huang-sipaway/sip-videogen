import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import type { ImageGenerationMetadata } from '@/lib/bridge'

interface Props {
  metadata: ImageGenerationMetadata | null
  onClose: () => void
}

export function PromptDetailsModal({ metadata, onClose }: Props) {
  if (!metadata) return null

  const showOriginalPrompt =
    metadata.original_prompt && metadata.original_prompt !== metadata.prompt
  const referenceImages =
    metadata.reference_images && metadata.reference_images.length > 0
      ? metadata.reference_images
      : metadata.reference_image
        ? [metadata.reference_image]
        : []

  return (
    <Dialog open={!!metadata} onOpenChange={() => onClose()}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Generation Details</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Prompt */}
          <div>
            <h4 className="text-sm font-medium text-muted-foreground mb-1">
              Prompt Used (Final)
            </h4>
            <pre className="bg-muted p-3 rounded-lg text-sm whitespace-pre-wrap font-mono">
              {metadata.prompt}
            </pre>
            {showOriginalPrompt && (
              <div className="mt-3">
                <h4 className="text-sm font-medium text-muted-foreground mb-1">
                  Original Prompt
                </h4>
                <pre className="bg-muted p-3 rounded-lg text-sm whitespace-pre-wrap font-mono">
                  {metadata.original_prompt}
                </pre>
              </div>
            )}
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

          {/* Reference Images */}
          {(metadata.reference_images_detail?.length || referenceImages.length > 0) && (
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">
                Reference Images
              </h4>
              <div className="space-y-2">
                {metadata.reference_images_detail && metadata.reference_images_detail.length > 0
                  ? metadata.reference_images_detail.map((ref, idx) => {
                      const labelParts = []
                      if (ref.product_slug) labelParts.push(`product: ${ref.product_slug}`)
                      if (ref.role) labelParts.push(`role: ${ref.role}`)
                      if (ref.used_for) labelParts.push(`used_for: ${ref.used_for}`)

                      return (
                        <div key={`${ref.path}-${idx}`}>
                          <code className="text-sm bg-muted px-2 py-1 rounded break-all block">
                            {ref.path}
                          </code>
                          {labelParts.length > 0 && (
                            <div className="text-xs text-muted-foreground mt-1">
                              {labelParts.join(' | ')}
                            </div>
                          )}
                        </div>
                      )
                    })
                  : referenceImages.map((path) => (
                      <code
                        key={path}
                        className="text-sm bg-muted px-2 py-1 rounded break-all block"
                      >
                        {path}
                      </code>
                    ))}
              </div>
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
              <div className="space-y-1 text-sm">
                <div>
                  Status:{' '}
                  {metadata.validation_passed === true
                    ? 'Passed'
                    : metadata.validation_passed === false
                      ? 'Failed'
                      : 'Unknown'}
                </div>
                {typeof metadata.validation_attempts === 'number' && (
                  <div>Attempts: {metadata.validation_attempts}</div>
                )}
                {typeof metadata.final_attempt_number === 'number' && (
                  <div>Final Attempt: {metadata.final_attempt_number}</div>
                )}
              </div>
              {metadata.validation_warning && (
                <pre className="mt-2 bg-muted p-2 rounded text-xs whitespace-pre-wrap font-mono">
                  {metadata.validation_warning}
                </pre>
              )}
            </div>
          )}

          {/* API Call Code */}
          {metadata.api_call_code && (
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">
                Python API Call (Final)
              </h4>
              <pre className="bg-zinc-900 text-zinc-100 p-3 rounded-lg text-xs whitespace-pre-wrap font-mono overflow-x-auto">
                {metadata.api_call_code}
              </pre>
            </div>
          )}

          {/* Request Payload */}
          {metadata.request_payload && (
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">
                Request Payload (Final)
              </h4>
              <pre className="bg-muted p-3 rounded-lg text-xs whitespace-pre-wrap font-mono overflow-x-auto">
                {JSON.stringify(metadata.request_payload, null, 2)}
              </pre>
            </div>
          )}

          {/* Attempts */}
          {metadata.attempts && metadata.attempts.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-2">Attempts</h4>
              <Accordion type="multiple" className="w-full">
                {metadata.attempts.map((attempt) => {
                  const status =
                    attempt.validation_passed === true
                      ? 'Passed'
                      : attempt.validation_passed === false
                        ? 'Failed'
                        : attempt.error
                          ? 'Error'
                          : metadata.validate_identity
                            ? 'Unknown'
                            : 'Generated'
                  return (
                    <AccordionItem
                      key={`attempt-${attempt.attempt_number}`}
                      value={`attempt-${attempt.attempt_number}`}
                    >
                      <AccordionTrigger>
                        Attempt {attempt.attempt_number} - {status}
                      </AccordionTrigger>
                      <AccordionContent>
                        <div className="space-y-3">
                          <div>
                            <h5 className="text-xs font-semibold text-muted-foreground mb-1">
                              Prompt
                            </h5>
                            <pre className="bg-muted p-3 rounded-lg text-xs whitespace-pre-wrap font-mono">
                              {attempt.prompt}
                            </pre>
                          </div>
                          {attempt.error && (
                            <div>
                              <h5 className="text-xs font-semibold text-muted-foreground mb-1">
                                Error
                              </h5>
                              <pre className="bg-muted p-2 rounded text-xs whitespace-pre-wrap font-mono">
                                {attempt.error}
                              </pre>
                            </div>
                          )}
                          {attempt.validation && (
                            <div>
                              <h5 className="text-xs font-semibold text-muted-foreground mb-1">
                                Validation Result
                              </h5>
                              <pre className="bg-muted p-3 rounded-lg text-xs whitespace-pre-wrap font-mono overflow-x-auto">
                                {JSON.stringify(attempt.validation, null, 2)}
                              </pre>
                            </div>
                          )}
                          {attempt.api_call_code && (
                            <div>
                              <h5 className="text-xs font-semibold text-muted-foreground mb-1">
                                Python API Call
                              </h5>
                              <pre className="bg-zinc-900 text-zinc-100 p-3 rounded-lg text-xs whitespace-pre-wrap font-mono overflow-x-auto">
                                {attempt.api_call_code}
                              </pre>
                            </div>
                          )}
                          {attempt.request_payload && (
                            <div>
                              <h5 className="text-xs font-semibold text-muted-foreground mb-1">
                                Request Payload
                              </h5>
                              <pre className="bg-muted p-3 rounded-lg text-xs whitespace-pre-wrap font-mono overflow-x-auto">
                                {JSON.stringify(attempt.request_payload, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  )
                })}
              </Accordion>
            </div>
          )}

          {/* Raw Metadata */}
          <div>
            <Accordion type="single" collapsible className="w-full">
              <AccordionItem value="raw-metadata">
                <AccordionTrigger>Raw Metadata (JSON)</AccordionTrigger>
                <AccordionContent>
                  <pre className="bg-muted p-3 rounded-lg text-xs whitespace-pre-wrap font-mono overflow-x-auto">
                    {JSON.stringify(metadata, null, 2)}
                  </pre>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </div>

          {/* Timestamp */}
          <div className="text-xs text-muted-foreground border-t pt-3 mt-4">
            Generated: {new Date(metadata.generated_at).toLocaleString()}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
