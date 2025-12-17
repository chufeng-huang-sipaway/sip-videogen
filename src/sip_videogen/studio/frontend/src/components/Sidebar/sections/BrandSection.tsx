import { Brain } from 'lucide-react'
import { DocumentsList } from '../DocumentsList'
import { AssetTree } from '../AssetTree'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { useBrand } from '@/context/BrandContext'

interface BrandSectionProps {
  onOpenBrandMemory?: () => void
}

export function BrandSection({ onOpenBrandMemory }: BrandSectionProps) {
  const { activeBrand } = useBrand()

  if (!activeBrand) {
    return <div className="text-sm text-gray-500">Select a brand to view documents and assets</div>
  }

  return (
    <div className="space-y-4">
      {/* Brand Memory button */}
      <div className="space-y-2">
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2"
          onClick={onOpenBrandMemory}
        >
          <Brain className="h-4 w-4 text-purple-500" />
          <span>Brand Memory</span>
          <span className="ml-auto text-xs text-muted-foreground">View</span>
        </Button>
      </div>
      <Separator />
      <DocumentsList />
      <Separator />
      <AssetTree />
    </div>
  )
}
