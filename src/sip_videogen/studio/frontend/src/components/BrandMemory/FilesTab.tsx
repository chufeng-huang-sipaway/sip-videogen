import { DocumentsList } from '@/components/Sidebar/DocumentsList'
import { AssetTree } from '@/components/Sidebar/AssetTree'
import { Separator } from '@/components/ui/separator'

/**
 * FilesTab - Displays Documents and Assets within the BrandMemory dialog.
 *
 * This allows users to browse and manage brand source files
 * (documents and images) from within the Brand Brain popup.
 */
export function FilesTab() {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-medium text-muted-foreground mb-2">Documents</h3>
        <DocumentsList />
      </div>
      <Separator />
      <div>
        <h3 className="text-sm font-medium text-muted-foreground mb-2">Assets</h3>
        <AssetTree />
      </div>
    </div>
  )
}
