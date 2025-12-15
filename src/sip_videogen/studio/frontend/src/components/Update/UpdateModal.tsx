import { useState, useEffect, useCallback } from 'react'
import { Download, ExternalLink, CheckCircle, AlertCircle } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { bridge } from '@/lib/bridge'
import type { UpdateCheckResult, UpdateProgress } from '@/lib/bridge'

interface UpdateModalProps {
  updateInfo: UpdateCheckResult | null
  onClose: () => void
  onSkipVersion?: (version: string) => void
}

type UpdateState = 'available' | 'downloading' | 'installing' | 'restarting' | 'error' | 'success'

export function UpdateModal({ updateInfo, onClose, onSkipVersion }: UpdateModalProps) {
  const [state, setState] = useState<UpdateState>('available')
  const [progress, setProgress] = useState<UpdateProgress | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Poll for progress updates during download
  useEffect(() => {
    if (state !== 'downloading' && state !== 'installing') return

    const interval = setInterval(async () => {
      try {
        const progressData = await bridge.getUpdateProgress()
        setProgress(progressData)

        if (progressData.status === 'installing') {
          setState('installing')
        } else if (progressData.status === 'restarting') {
          setState('restarting')
        } else if (progressData.status === 'error') {
          setState('error')
          setError(progressData.error || 'Update failed')
        }
      } catch {
        // Ignore polling errors
      }
    }, 500)

    return () => clearInterval(interval)
  }, [state])

  const handleUpdate = useCallback(async () => {
    if (!updateInfo?.download_url || !updateInfo.new_version) return

    setState('downloading')
    setError(null)

    try {
      await bridge.downloadAndInstallUpdate(updateInfo.download_url, updateInfo.new_version)
      // If we get here, the app is about to restart
      setState('restarting')
    } catch (err) {
      setState('error')
      setError(err instanceof Error ? err.message : 'Update failed')
    }
  }, [updateInfo])

  const handleSkip = useCallback(() => {
    if (updateInfo?.new_version && onSkipVersion) {
      onSkipVersion(updateInfo.new_version)
    }
    onClose()
  }, [updateInfo, onSkipVersion, onClose])

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
  }

  const formatChangelog = (changelog: string) => {
    // Simple markdown-like formatting for changelog
    return changelog
      .split('\n')
      .filter(line => line.trim())
      .slice(0, 10) // Limit to first 10 lines
      .map((line, i) => (
        <li key={i} className="text-sm text-muted-foreground">
          {line.replace(/^[-*]\s*/, '')}
        </li>
      ))
  }

  if (!updateInfo) return null

  const isOpen = true // Always open when updateInfo is provided

  return (
    <Dialog open={isOpen} onOpenChange={() => state === 'available' && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          {state === 'available' && (
            <>
              <DialogTitle className="flex items-center gap-2">
                <Download className="h-5 w-5 text-primary" />
                Update Available
              </DialogTitle>
              <DialogDescription>
                Version {updateInfo.new_version} is ready to install.
                You are currently on version {updateInfo.current_version}.
              </DialogDescription>
            </>
          )}

          {state === 'downloading' && (
            <>
              <DialogTitle className="flex items-center gap-2">
                <Download className="h-5 w-5 text-primary animate-pulse" />
                Downloading Update...
              </DialogTitle>
              <DialogDescription>
                Please wait while the update is being downloaded.
              </DialogDescription>
            </>
          )}

          {state === 'installing' && (
            <>
              <DialogTitle className="flex items-center gap-2">
                <Download className="h-5 w-5 text-primary animate-spin" />
                Installing Update...
              </DialogTitle>
              <DialogDescription>
                The update is being installed. The app will restart shortly.
              </DialogDescription>
            </>
          )}

          {state === 'restarting' && (
            <>
              <DialogTitle className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-500" />
                Restarting...
              </DialogTitle>
              <DialogDescription>
                Update installed successfully! The app is restarting...
              </DialogDescription>
            </>
          )}

          {state === 'error' && (
            <>
              <DialogTitle className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-destructive" />
                Update Failed
              </DialogTitle>
              <DialogDescription>
                {error || 'An error occurred while updating.'}
              </DialogDescription>
            </>
          )}
        </DialogHeader>

        {/* Progress bar during download/install */}
        {(state === 'downloading' || state === 'installing') && (
          <div className="space-y-2">
            <Progress value={progress?.percent || 0} />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>
                {progress?.downloaded && progress?.total
                  ? `${formatBytes(progress.downloaded)} / ${formatBytes(progress.total)}`
                  : 'Preparing...'}
              </span>
              <span>{Math.round(progress?.percent || 0)}%</span>
            </div>
          </div>
        )}

        {/* Changelog when update is available */}
        {state === 'available' && updateInfo.changelog && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium">What's new:</h4>
            <ul className="list-disc list-inside space-y-1 max-h-32 overflow-y-auto">
              {formatChangelog(updateInfo.changelog)}
            </ul>
          </div>
        )}

        <DialogFooter className="flex-col sm:flex-row gap-2">
          {state === 'available' && (
            <>
              <Button variant="outline" onClick={handleSkip} className="sm:order-1">
                Skip This Version
              </Button>
              <Button variant="ghost" onClick={onClose} className="sm:order-2">
                Later
              </Button>
              <Button onClick={handleUpdate} className="sm:order-3">
                <Download className="h-4 w-4 mr-2" />
                Update Now
              </Button>
            </>
          )}

          {state === 'error' && (
            <>
              <Button variant="outline" onClick={onClose}>
                Close
              </Button>
              <Button onClick={handleUpdate}>
                Try Again
              </Button>
              {updateInfo.release_url && (
                <Button
                  variant="ghost"
                  onClick={() => window.open(updateInfo.release_url, '_blank')}
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Manual Download
                </Button>
              )}
            </>
          )}

          {state === 'restarting' && (
            <div className="text-sm text-muted-foreground text-center w-full">
              Please wait...
            </div>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
