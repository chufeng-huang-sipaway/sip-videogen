import { useState } from 'react'
import { Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { bridge, isPyWebView, type BrandEntry } from '@/lib/bridge'

interface DeleteBrandDialogProps {
  brand: BrandEntry | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onDeleted: () => void
}

export function DeleteBrandDialog({
  brand,
  open,
  onOpenChange,
  onDeleted,
}: DeleteBrandDialogProps) {
  const [isDeleting, setIsDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDelete = async () => {
    if (!brand) return

    setError(null)
    setIsDeleting(true)

    try {
      if (isPyWebView()) {
        await bridge.deleteBrand(brand.slug)
      }
      onDeleted()
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete brand')
    } finally {
      setIsDeleting(false)
    }
  }

  if (!brand) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Trash2 className="h-5 w-5 text-red-500" />
            Delete Brand
          </DialogTitle>
          <DialogDescription>
            Are you sure you want to delete "{brand.name}"?
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <p className="text-sm text-muted-foreground mb-3">
            This will permanently remove:
          </p>
          <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
            <li>All brand identity data</li>
            <li>All uploaded assets and documents</li>
            <li>All generated images</li>
          </ul>
          <p className="text-sm font-medium text-red-600 mt-4">
            This action cannot be undone.
          </p>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isDeleting}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={isDeleting}
          >
            {isDeleting ? 'Deleting...' : 'Delete Brand'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
