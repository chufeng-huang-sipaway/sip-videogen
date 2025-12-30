import { AlertTriangle } from 'lucide-react'
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

interface RegenerateConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
  brandName: string
}

/**
 * RegenerateConfirmDialog - Confirmation dialog for regenerating brand identity.
 *
 * This dialog warns users that regenerating will:
 * - Overwrite all current edits
 * - Create a backup before regenerating (so they can restore)
 * - Re-run the AI brand director agents on source materials
 *
 * The user must explicitly confirm before the regeneration proceeds.
 */
export function RegenerateConfirmDialog({
  open,
  onOpenChange,
  onConfirm,
  brandName,
}: RegenerateConfirmDialogProps) {
  const handleConfirm = () => {
    onConfirm()
    onOpenChange(false)
  }

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            Regenerate Brand Identity?
          </AlertDialogTitle>
          <AlertDialogDescription className="space-y-3">
            <p>
              This will re-analyze the source materials for <strong>{brandName}</strong> and
              generate a new brand identity. This action will:
            </p>
            <ul className="list-disc list-inside space-y-1 text-sm">
              <li><strong>Overwrite all current edits</strong> to the brand identity</li>
              <li>Create a backup of the current identity (can be restored from History)</li>
              <li>Re-run the AI brand director on your source documents</li>
            </ul>
            <p className="text-sm text-destructive font-medium">
              Any manual changes you&apos;ve made will be lost unless you restore from backup.
            </p>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            className="bg-destructive hover:bg-destructive/90 text-destructive-foreground"
          >
            Regenerate Identity
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
