import { useCallback, useRef, useState, useEffect } from 'react'
import { Brain, FileText, Image, RefreshCw, History, ChevronRight } from 'lucide-react'
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from '@/components/ui/context-menu'
import { Spinner } from '@/components/ui/spinner'
import { useBrand } from '@/context/BrandContext'
import { bridge, isPyWebView } from '@/lib/bridge'
import { RegenerateConfirmDialog } from '@/components/BrandMemory/RegenerateConfirmDialog'
import { BackupDialog } from '@/components/BrandMemory/BackupDialog'
import type { BrandIdentityFull } from '@/types/brand-identity'

const ALLOWED_DOC_EXTS = ['.md', '.txt', '.json', '.yaml', '.yml']
const ALLOWED_IMAGE_EXTS = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg']

interface BrandBrainCardProps {
  onOpenBrandMemory: () => void
}

export function BrandBrainCard({ onOpenBrandMemory }: BrandBrainCardProps) {
  const { activeBrand, identity, isIdentityLoading, refreshIdentity, setIdentity } = useBrand()

  // File input refs
  const docInputRef = useRef<HTMLInputElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)

  // Upload states
  const [isUploadingDoc, setIsUploadingDoc] = useState(false)
  const [isUploadingImage, setIsUploadingImage] = useState(false)

  // Regenerate states
  const [showRegenerateConfirm, setShowRegenerateConfirm] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)

  // Backup dialog state
  const [showBackupDialog, setShowBackupDialog] = useState(false)

  // Load identity on mount if not already loaded
  useEffect(() => {
    if (activeBrand && !identity && !isIdentityLoading) {
      refreshIdentity()
    }
  }, [activeBrand, identity, isIdentityLoading, refreshIdentity])

  // Handle document upload
  const handleDocUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !isPyWebView() || !activeBrand) return

    setIsUploadingDoc(true)
    try {
      for (const file of Array.from(e.target.files)) {
        const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
        if (!ALLOWED_DOC_EXTS.includes(ext)) continue

        const reader = new FileReader()
        await new Promise<void>((resolve, reject) => {
          reader.onload = async () => {
            try {
              const base64 = (reader.result as string).split(',')[1]
              await bridge.uploadDocument(file.name, base64)
              resolve()
            } catch (err) {
              reject(err)
            }
          }
          reader.onerror = () => reject(reader.error)
          reader.readAsDataURL(file)
        })
      }
    } finally {
      setIsUploadingDoc(false)
      e.target.value = ''
    }
  }, [activeBrand])

  // Handle image upload
  const handleImageUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !isPyWebView() || !activeBrand) return

    setIsUploadingImage(true)
    try {
      for (const file of Array.from(e.target.files)) {
        const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
        if (!ALLOWED_IMAGE_EXTS.includes(ext)) continue

        const reader = new FileReader()
        await new Promise<void>((resolve, reject) => {
          reader.onload = async () => {
            try {
              const base64 = (reader.result as string).split(',')[1]
              await bridge.uploadAsset(file.name, base64, 'marketing')
              resolve()
            } catch (err) {
              reject(err)
            }
          }
          reader.onerror = () => reject(reader.error)
          reader.readAsDataURL(file)
        })
      }
    } finally {
      setIsUploadingImage(false)
      e.target.value = ''
    }
  }, [activeBrand])

  // Handle regenerate confirmation
  const handleRegenerateConfirm = async () => {
    if (!isPyWebView()) return

    setIsRegenerating(true)
    setShowRegenerateConfirm(false)

    try {
      const newIdentity = await bridge.regenerateBrandIdentity(true)
      setIdentity(newIdentity)
    } catch (err) {
      console.error('[BrandBrainCard] Regeneration failed:', err)
    } finally {
      setIsRegenerating(false)
    }
  }

  // Handle backup restore
  const handleBackupRestore = (restoredIdentity: BrandIdentityFull) => {
    setIdentity(restoredIdentity)
  }

  if (!activeBrand) return null

  // Get brand colors for display (up to 5)
  const brandColors = identity?.visual?.primary_colors?.slice(0, 5) ?? []

  return (
    <>
      <div className="px-4 pb-3">
        <ContextMenu>
          <ContextMenuTrigger asChild>
            {/* Card - click opens panel, right-click opens context menu */}
            <button
              onClick={onOpenBrandMemory}
              className="w-full p-3 rounded-lg border border-border/60 bg-card/50
                       cursor-pointer hover:bg-accent/50 transition-colors text-left"
            >
              {/* Header row */}
              <div className="flex items-center gap-2 mb-1">
                <Brain className="h-4 w-4 text-purple-500 flex-shrink-0" />
                <span className="font-medium text-sm flex-1 truncate">Brand Memory</span>
                <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
              </div>

              {/* Brand name / Loading state */}
              {isIdentityLoading ? (
                <div className="h-4 w-24 bg-muted/50 rounded animate-pulse mb-2" />
              ) : identity ? (
                <p className="text-xs text-muted-foreground mb-2 truncate">
                  {identity.core.name}
                </p>
              ) : (
                <p className="text-xs text-muted-foreground/50 mb-2 italic">
                  No identity loaded
                </p>
              )}

              {/* Color swatches */}
              {isIdentityLoading ? (
                <div className="flex gap-1">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="w-4 h-4 rounded-full bg-muted/50 animate-pulse" />
                  ))}
                </div>
              ) : brandColors.length > 0 ? (
                <div className="flex gap-1">
                  {brandColors.map((color, i) => (
                    <div
                      key={i}
                      className="w-4 h-4 rounded-full border border-border/50"
                      style={{ backgroundColor: color.hex }}
                      title={color.name}
                    />
                  ))}
                </div>
              ) : null}
            </button>
          </ContextMenuTrigger>

          <ContextMenuContent className="w-56">
            {/* Upload Documents */}
            <ContextMenuItem
              onClick={() => docInputRef.current?.click()}
              disabled={isUploadingDoc}
            >
              {isUploadingDoc ? (
                <Spinner className="h-4 w-4" />
              ) : (
                <FileText className="h-4 w-4" />
              )}
              <span>{isUploadingDoc ? 'Uploading...' : 'Upload Documents'}</span>
              <span className="ml-auto text-xs text-muted-foreground">.md, .txt</span>
            </ContextMenuItem>

            {/* Upload Images */}
            <ContextMenuItem
              onClick={() => imageInputRef.current?.click()}
              disabled={isUploadingImage}
            >
              {isUploadingImage ? (
                <Spinner className="h-4 w-4" />
              ) : (
                <Image className="h-4 w-4" />
              )}
              <span>{isUploadingImage ? 'Uploading...' : 'Upload Images'}</span>
              <span className="ml-auto text-xs text-muted-foreground">.png, .jpg</span>
            </ContextMenuItem>

            <ContextMenuSeparator />

            {/* Regenerate */}
            <ContextMenuItem
              onClick={() => setShowRegenerateConfirm(true)}
              disabled={isRegenerating || !identity}
            >
              {isRegenerating ? (
                <Spinner className="h-4 w-4" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              <span>{isRegenerating ? 'Regenerating...' : 'Regenerate'}</span>
            </ContextMenuItem>

            {/* History */}
            <ContextMenuItem
              onClick={() => setShowBackupDialog(true)}
              disabled={!identity}
            >
              <History className="h-4 w-4" />
              <span>History</span>
            </ContextMenuItem>
          </ContextMenuContent>
        </ContextMenu>

        {/* Hidden file inputs */}
        <input
          ref={docInputRef}
          type="file"
          className="hidden"
          multiple
          accept={ALLOWED_DOC_EXTS.join(',')}
          onChange={handleDocUpload}
        />
        <input
          ref={imageInputRef}
          type="file"
          className="hidden"
          multiple
          accept={ALLOWED_IMAGE_EXTS.join(',')}
          onChange={handleImageUpload}
        />
      </div>

      {/* Regenerate confirmation dialog */}
      <RegenerateConfirmDialog
        open={showRegenerateConfirm}
        onOpenChange={setShowRegenerateConfirm}
        onConfirm={handleRegenerateConfirm}
        brandName={identity?.core.name ?? 'this brand'}
      />

      {/* Backup history dialog */}
      <BackupDialog
        open={showBackupDialog}
        onOpenChange={setShowBackupDialog}
        brandName={identity?.core.name ?? 'this brand'}
        onRestore={handleBackupRestore}
      />
    </>
  )
}
