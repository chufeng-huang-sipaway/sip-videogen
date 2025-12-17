import { DocumentsList } from '../DocumentsList'
import { AssetTree } from '../AssetTree'
import { Separator } from '@/components/ui/separator'
import { useBrand } from '@/context/BrandContext'

export function BrandSection() {
  const { activeBrand } = useBrand()

  if (!activeBrand) {
    return <div className="text-sm text-gray-500">Select a brand to view documents and assets</div>
  }

  return (
    <div className="space-y-4">
      <DocumentsList />
      <Separator />
      <AssetTree />
    </div>
  )
}
