import { useState } from 'react'
import { FileText, ImageIcon } from 'lucide-react'
import { DocumentsList } from '@/components/Sidebar/DocumentsList'
import { AssetTree } from '@/components/Sidebar/AssetTree'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'

// Section definitions for vertical tabs navigation
const FILE_SECTIONS = [
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'assets', label: 'Assets', icon: ImageIcon },
] as const

type FileSectionId = (typeof FILE_SECTIONS)[number]['id']

/**
 * FilesTab - Displays Documents and Assets within the BrandMemory dialog.
 *
 * Uses the same vertical tabs layout as the Memory tab for consistency.
 * Users can browse and manage brand source files (documents and images).
 */
export function FilesTab() {
  const [activeSection, setActiveSection] = useState<FileSectionId>('documents')

  return (
    <div className="h-full flex gap-0">
      {/* Vertical navigation sidebar */}
      <nav className="w-44 flex-shrink-0 border-r border-border pr-2 py-2">
        <ul className="space-y-1">
          {FILE_SECTIONS.map((section) => {
            const Icon = section.icon
            const isActive = activeSection === section.id
            return (
              <li key={section.id}>
                <button
                  onClick={() => setActiveSection(section.id)}
                  className={cn(
                    'w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                    'hover:bg-muted/50',
                    isActive
                      ? 'bg-brand-a10 text-brand-600 dark:text-brand-500'
                      : 'text-muted-foreground hover:text-foreground'
                  )}
                >
                  <Icon className={cn('h-4 w-4', isActive && 'text-brand-600 dark:text-brand-500')} />
                  {section.label}
                </button>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Section content area */}
      <div className="flex-1 min-w-0 min-h-0 pl-4 flex flex-col">
        {/* Section header */}
        <div className="pb-4 border-b border-border">
          <h3 className="text-base font-semibold">
            {activeSection === 'documents' ? 'Documents' : 'Assets'}
          </h3>
          <p className="text-sm text-muted-foreground mt-0.5">
            {activeSection === 'documents'
              ? 'Brand guidelines and reference documents'
              : 'Images and visual assets for this brand'}
          </p>
        </div>

        {/* Scrollable content */}
        <ScrollArea className="flex-1 min-h-0">
          <div className="pr-4 pt-4 pb-4">
            {activeSection === 'documents' && <DocumentsList />}
            {activeSection === 'assets' && <AssetTree />}
          </div>
        </ScrollArea>
      </div>
    </div>
  )
}
