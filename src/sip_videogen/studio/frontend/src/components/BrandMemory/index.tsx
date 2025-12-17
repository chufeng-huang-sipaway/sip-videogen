import { useState, useEffect, useCallback } from 'react'
import { Brain, RefreshCw, History, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Spinner } from '@/components/ui/spinner'
import { useBrand } from '@/context/BrandContext'
import { bridge, isPyWebView } from '@/lib/bridge'
import type { BrandIdentityFull } from '@/types/brand-identity'
import { MemorySectionGroup } from './MemorySection'
import { CoreSection } from './sections/CoreSection'
import { VisualSection } from './sections/VisualSection'
import { VoiceSection } from './sections/VoiceSection'
import { AudienceSection } from './sections/AudienceSection'
import { PositioningSection } from './sections/PositioningSection'
import { ConstraintsAvoidSection } from './sections/ConstraintsAvoidSection'
import { RegenerateConfirmDialog } from './RegenerateConfirmDialog'

interface BrandMemoryProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

/**
 * BrandMemory - Main view container for the Brand Memory panel.
 *
 * This component displays the AI's understanding of the brand, organized into
 * expandable sections. Users can view and edit brand identity data.
 *
 * Architecture notes:
 * - Opens as a Dialog/modal to keep ChatPanel mounted (preserves conversation)
 * - Fetches full identity (L1 data) via getBrandIdentity() bridge method
 * - Header shows brand name, last updated, and action buttons
 * - Sections will be rendered via MemorySection components (Task 3.1.2)
 */
export function BrandMemory({ open, onOpenChange }: BrandMemoryProps) {
  const { activeBrand } = useBrand()

  // State
  const [identity, setIdentity] = useState<BrandIdentityFull | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showRegenerateConfirm, setShowRegenerateConfirm] = useState(false)

  // Load identity when dialog opens
  const loadIdentity = useCallback(async () => {
    if (!activeBrand || !isPyWebView()) return

    setIsLoading(true)
    setError(null)

    try {
      const data = await bridge.getBrandIdentity()
      setIdentity(data)
    } catch (err) {
      console.error('[BrandMemory] Failed to load identity:', err)
      setError(err instanceof Error ? err.message : 'Failed to load brand identity')
    } finally {
      setIsLoading(false)
    }
  }, [activeBrand])

  // Load identity when dialog opens or brand changes
  useEffect(() => {
    if (open && activeBrand) {
      loadIdentity()
    }
  }, [open, activeBrand, loadIdentity])

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      setIdentity(null)
      setError(null)
    }
  }, [open])

  // Format last updated date
  const formatLastUpdated = (isoString: string): string => {
    const date = new Date(isoString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffDays === 0) {
      return 'Updated today'
    } else if (diffDays === 1) {
      return 'Updated yesterday'
    } else if (diffDays < 7) {
      return `Updated ${diffDays} days ago`
    } else {
      return `Updated ${date.toLocaleDateString()}`
    }
  }

  // Handle dialog close
  const handleClose = () => {
    onOpenChange(false)
  }

  // Handle regenerate confirmation (actual regeneration logic in Task 3.5.2-3.5.4)
  const handleRegenerateConfirm = () => {
    // TODO: Implement actual regeneration (Task 3.5.2-3.5.4)
    console.log('[BrandMemory] Regenerate confirmed')
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl max-h-[85vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-purple-500" />
            Brand Memory
          </DialogTitle>
          <DialogDescription className="flex items-center justify-between">
            <span>
              {identity
                ? `What the AI knows about ${identity.core.name}`
                : 'Loading brand identity...'}
            </span>
            {identity && (
              <span className="text-xs text-muted-foreground">
                {formatLastUpdated(identity.updated_at)}
              </span>
            )}
          </DialogDescription>
        </DialogHeader>

        {/* Action buttons */}
        {identity && !isLoading && (
          <div className="flex items-center gap-2 flex-shrink-0 pb-2 border-b border-border">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowRegenerateConfirm(true)}
              className="gap-1.5"
            >
              <RefreshCw className="h-4 w-4" />
              Regenerate
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                // TODO: Implement backup history (Stage 5)
                console.log('[BrandMemory] History clicked')
              }}
              className="gap-1.5"
            >
              <History className="h-4 w-4" />
              History
            </Button>
          </div>
        )}

        {/* Content area */}
        <ScrollArea className="flex-1 min-h-0">
          <div className="pr-4 py-2">
            {/* Loading state */}
            {isLoading && (
              <div className="py-12 flex flex-col items-center gap-4">
                <Spinner className="h-8 w-8 text-purple-500" />
                <p className="text-sm text-muted-foreground">Loading brand memory...</p>
              </div>
            )}

            {/* Error state */}
            {error && !isLoading && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Identity sections */}
            {identity && !isLoading && !error && (
              <MemorySectionGroup>
                <CoreSection
                  data={identity.core}
                  onIdentityUpdate={setIdentity}
                />
                <VisualSection
                  data={identity.visual}
                  onIdentityUpdate={setIdentity}
                />
                <VoiceSection
                  data={identity.voice}
                  onIdentityUpdate={setIdentity}
                />
                <AudienceSection
                  data={identity.audience}
                  onIdentityUpdate={setIdentity}
                />
                <PositioningSection
                  data={identity.positioning}
                  onIdentityUpdate={setIdentity}
                />
                <ConstraintsAvoidSection
                  data={{ constraints: identity.constraints, avoid: identity.avoid }}
                  onIdentityUpdate={setIdentity}
                />
              </MemorySectionGroup>
            )}

            {/* No brand selected */}
            {!activeBrand && !isLoading && (
              <div className="py-12 text-center">
                <p className="text-sm text-muted-foreground">
                  No brand selected. Please select a brand from the sidebar.
                </p>
              </div>
            )}
          </div>
        </ScrollArea>
      </DialogContent>

      {/* Regenerate confirmation dialog */}
      <RegenerateConfirmDialog
        open={showRegenerateConfirm}
        onOpenChange={setShowRegenerateConfirm}
        onConfirm={handleRegenerateConfirm}
        brandName={identity?.core.name ?? 'this brand'}
      />
    </Dialog>
  )
}

