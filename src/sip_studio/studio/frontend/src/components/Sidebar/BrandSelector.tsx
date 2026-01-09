import { useState } from 'react'
import { Plus, Check, Trash2, Building2, ChevronsUpDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useBrand } from '@/context/BrandContext'
import { DeleteBrandDialog } from '@/components/Brand/DeleteBrandDialog'
import { CreateBrandDialog } from '@/components/Brand/CreateBrandDialog'
import { cn } from '@/lib/utils'

const CONTENT_DURATION = 150
const WIDTH_DURATION = 250
const EASING = 'cubic-bezier(0.4, 0, 0.2, 1)'

interface BrandSelectorProps { compact?: boolean; showContent?: boolean; allowTooltips?: boolean }

export function BrandSelector({ compact, showContent = true, allowTooltips = true }: BrandSelectorProps) {
  const { brands, activeBrand, isLoading, selectBrand, refresh } = useBrand()
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const currentBrand = brands.find(b => b.slug === activeBrand)
  const getInitials = (name: string) => { const words = name.split(/\s+/); if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase(); return name.slice(0, 2).toUpperCase() }

  const contentTransition = `opacity ${CONTENT_DURATION}ms ${EASING}, visibility ${CONTENT_DURATION}ms ${EASING}, transform ${CONTENT_DURATION}ms ${EASING}`
  const sizeTransition = `width ${WIDTH_DURATION}ms ${EASING}, height ${WIDTH_DURATION}ms ${EASING}, padding ${WIDTH_DURATION}ms ${EASING}`

  if (isLoading) {
    return (<Button variant="ghost" className={cn("rounded-xl bg-primary/10", compact ? "w-12 h-12 p-0" : "w-full h-auto py-3 px-3")} style={{ transition: sizeTransition }} disabled><Building2 className="w-5 h-5 animate-pulse" /></Button>)
  }

  const dropdownContent = (
    <DropdownMenuContent className="w-60" side={compact ? "right" : "bottom"} align={compact ? "start" : "center"} sideOffset={4}>
      {brands.length === 0 ? (
        <DropdownMenuItem disabled>No brands found</DropdownMenuItem>
      ) : (
        brands.map((brand) => (
          <DropdownMenuItem key={brand.slug} onClick={() => selectBrand(brand.slug)} className="py-2.5">
            <span className="flex-1 font-medium">{brand.name}</span>
            {brand.slug === activeBrand && <Check className="h-4 w-4 text-primary" />}
          </DropdownMenuItem>
        ))
      )}
      <DropdownMenuSeparator />
      <DropdownMenuItem onClick={() => setCreateDialogOpen(true)} className="py-2.5 text-muted-foreground focus:text-foreground">
        <Plus className="h-4 w-4 mr-2" />
        Create New Brand
      </DropdownMenuItem>
      {currentBrand && (
        <>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="text-destructive focus:text-destructive py-2.5" onClick={() => setDeleteDialogOpen(true)}>
            <Trash2 className="h-4 w-4 mr-2" />
            Delete "{currentBrand.name}"
          </DropdownMenuItem>
        </>
      )}
    </DropdownMenuContent>
  )

  const dialogs = (
    <>
      <DeleteBrandDialog brand={currentBrand ?? null} open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen} onDeleted={refresh} />
      <CreateBrandDialog open={createDialogOpen} onOpenChange={setCreateDialogOpen} onCreated={async (slug) => { await refresh(); await selectBrand(slug) }} />
    </>
  )

  //Unified structure - same DOM, CSS handles compact/expanded with sequenced timing
  return (
    <DropdownMenu>
      <Tooltip open={compact && allowTooltips ? undefined : false}>
        <TooltipTrigger asChild>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className={cn("justify-start rounded-2xl bg-gradient-to-br from-white to-neutral-50 dark:from-neutral-900 dark:to-neutral-950 border border-white/20 shadow-sm hover:shadow-md transition-all duration-300 overflow-hidden", compact ? "w-12 h-12 p-0" : "w-full h-auto py-3.5 px-3")} style={{ transition: sizeTransition }}>
              <div className="flex items-center gap-3 text-left">
                <div className={cn("rounded-xl bg-brand-500/10 text-brand-600 flex items-center justify-center font-bold shrink-0 shadow-inner", compact ? "w-12 h-12 text-base" : "w-10 h-10 text-sm")} style={{ transition: sizeTransition }}>{currentBrand ? getInitials(currentBrand.name) : <Building2 className="w-5 h-5" />}</div>
                <div className="flex-1 min-w-0" style={{ transition: contentTransition, opacity: showContent && !compact ? 1 : 0, visibility: showContent && !compact ? 'visible' : 'hidden', transform: showContent && !compact ? 'translateX(0)' : 'translateX(-8px)', position: showContent && !compact ? 'relative' : 'absolute' }}>
                  <div className="font-semibold text-sm truncate leading-none mb-1">{currentBrand?.name || 'Select Brand'}</div>
                  <div className="text-[10px] text-muted-foreground/70 font-medium">Brand Workspace</div>
                </div>
              </div>
              <ChevronsUpDown className="h-4 w-4 text-muted-foreground/40" style={{ transition: contentTransition, opacity: showContent && !compact ? 1 : 0, visibility: showContent && !compact ? 'visible' : 'hidden', position: showContent && !compact ? 'relative' : 'absolute' }} />
            </Button>
          </DropdownMenuTrigger>
        </TooltipTrigger>
        {compact && <TooltipContent side="right" className="font-semibold">{currentBrand?.name || 'Select Brand'}</TooltipContent>}
      </Tooltip>
      {dropdownContent}
      {dialogs}
    </DropdownMenu>
  )
}
