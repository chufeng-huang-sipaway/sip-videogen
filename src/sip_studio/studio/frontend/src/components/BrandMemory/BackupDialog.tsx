import { useState, useEffect, useCallback } from 'react'
import { History, RotateCcw, AlertCircle, CheckCircle, Clock, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Spinner } from '@/components/ui/spinner'
import { bridge, isPyWebView } from '@/lib/bridge'
import type { BackupEntry, BrandIdentityFull } from '@/types/brand-identity'

interface BackupDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  brandName: string
  onRestore: (identity: BrandIdentityFull) => void
}

/**
 * BackupDialog - Dialog for viewing and restoring brand identity backups.
 *
 * This dialog allows users to:
 * - View all available backups for the current brand
 * - See when each backup was created
 * - Restore a previous backup (with confirmation)
 *
 * Backups are created automatically before regeneration and can also
 * be created manually in the future.
 */
export function BackupDialog({
  open,
  onOpenChange,
  brandName,
  onRestore,
}: BackupDialogProps) {
  // State
  const [backups, setBackups] = useState<BackupEntry[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isRestoring, setIsRestoring] = useState(false)
  const [restoreError, setRestoreError] = useState<string | null>(null)
  const [restoreSuccess, setRestoreSuccess] = useState(false)
  const [confirmRestore, setConfirmRestore] = useState<BackupEntry | null>(null)

  // Load backups when dialog opens
  const loadBackups = useCallback(async () => {
    if (!isPyWebView()) return

    setIsLoading(true)
    setError(null)

    try {
      const list = await bridge.listIdentityBackups()
      setBackups(list)
    } catch (err) {
      console.error('[BackupDialog] Failed to load backups:', err)
      setError(err instanceof Error ? err.message : 'Failed to load backups')
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Load backups when dialog opens
  useEffect(() => {
    if (open) {
      loadBackups()
    }
  }, [open, loadBackups])

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      setBackups([])
      setError(null)
      setRestoreError(null)
      setRestoreSuccess(false)
      setConfirmRestore(null)
    }
  }, [open])

  // Format timestamp for display
  const formatTimestamp = (isoString: string): string => {
    const date = new Date(isoString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / (1000 * 60))
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    // For recent backups, show relative time
    if (diffMins < 1) {
      return 'Just now'
    } else if (diffMins < 60) {
      return `${diffMins} minute${diffMins === 1 ? '' : 's'} ago`
    } else if (diffHours < 24) {
      return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`
    } else if (diffDays < 7) {
      return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`
    }

    // For older backups, show full date and time
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  // Format file size
  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  // Handle restore confirmation
  const handleRestoreConfirm = async () => {
    if (!confirmRestore || !isPyWebView()) return

    setIsRestoring(true)
    setRestoreError(null)
    setRestoreSuccess(false)
    setConfirmRestore(null)

    try {
      const identity = await bridge.restoreIdentityBackup(confirmRestore.filename)
      setRestoreSuccess(true)
      onRestore(identity)

      // Auto-dismiss success and close dialog after 2 seconds
      setTimeout(() => {
        setRestoreSuccess(false)
        onOpenChange(false)
      }, 2000)
    } catch (err) {
      console.error('[BackupDialog] Restore failed:', err)
      setRestoreError(err instanceof Error ? err.message : 'Failed to restore backup')
    } finally {
      setIsRestoring(false)
    }
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-md max-h-[70vh] flex flex-col">
          <DialogHeader className="flex-shrink-0">
            <DialogTitle className="flex items-center gap-2">
              <History className="h-5 w-5 text-muted-foreground" />
              Backup History
            </DialogTitle>
            <DialogDescription>
              Restore a previous version of {brandName}&apos;s identity
            </DialogDescription>
          </DialogHeader>

          <ScrollArea className="flex-1 min-h-0">
            <div className="pr-4 py-2">
              {/* Loading state */}
              {isLoading && (
                <div className="py-8 flex flex-col items-center gap-4">
                  <Spinner className="h-6 w-6 text-brand-500" />
                  <p className="text-sm text-muted-foreground">Loading backups...</p>
                </div>
              )}

              {/* Error state */}
              {error && !isLoading && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {/* Restore error */}
              {restoreError && !isRestoring && (
                <Alert variant="destructive" className="mb-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{restoreError}</AlertDescription>
                </Alert>
              )}

              {/* Restore success */}
              {restoreSuccess && !isRestoring && (
                <Alert className="mb-4 bg-success-a10 text-success border-success/20">
                  <CheckCircle className="h-4 w-4 text-success" />
                  <AlertDescription>
                    Backup restored successfully. AI context refreshed automatically.
                  </AlertDescription>
                </Alert>
              )}

              {/* Restoring indicator */}
              {isRestoring && (
                <div className="py-8 flex flex-col items-center gap-4">
                  <Spinner className="h-6 w-6 text-brand-500" />
                  <p className="text-sm text-muted-foreground">Restoring backup...</p>
                </div>
              )}

              {/* Empty state */}
              {!isLoading && !error && !isRestoring && backups.length === 0 && (
                <div className="py-8 text-center">
                  <FileText className="h-12 w-12 mx-auto text-muted-foreground/40 mb-3" />
                  <p className="text-sm text-muted-foreground">
                    No backups available yet.
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Backups are created automatically when you regenerate the brand identity.
                  </p>
                </div>
              )}

              {/* Backup list */}
              {!isLoading && !error && !isRestoring && backups.length > 0 && (
                <div className="space-y-2">
                  {backups.map((backup) => (
                    <div
                      key={backup.filename}
                      className="flex items-center justify-between p-3 rounded-lg border border-border hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 text-sm">
                          <Clock className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          <span className="font-medium truncate">
                            {formatTimestamp(backup.timestamp)}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5 pl-6">
                          {formatSize(backup.size_bytes)}
                        </p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setConfirmRestore(backup)}
                        disabled={isRestoring}
                        className="gap-1.5 flex-shrink-0"
                      >
                        <RotateCcw className="h-3.5 w-3.5" />
                        Restore
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>

      {/* Restore confirmation dialog */}
      <AlertDialog open={!!confirmRestore} onOpenChange={(open) => !open && setConfirmRestore(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <RotateCcw className="h-5 w-5 text-muted-foreground" />
              Restore Backup?
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-3">
              <p>
                This will replace the current brand identity with the backup from{' '}
                <strong>{confirmRestore && formatTimestamp(confirmRestore.timestamp)}</strong>.
              </p>
              <p className="text-sm text-destructive">
                Your current identity will be overwritten. Consider regenerating first to create a
                backup of the current state.
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleRestoreConfirm}>
              Restore Backup
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
