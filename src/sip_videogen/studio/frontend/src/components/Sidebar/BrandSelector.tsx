import { useState } from 'react'
import { ChevronDown, Plus, Check, Trash2, Building2, ChevronsUpDown } from 'lucide-react'
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

interface BrandSelectorProps { compact?: boolean }

export function BrandSelector({ compact }: BrandSelectorProps = {}) {
  const { brands, activeBrand, isLoading, selectBrand, refresh } = useBrand()
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const currentBrand = brands.find(b => b.slug === activeBrand)
  //Get initials from brand name (first letter of first two words, or first two letters)
  const getInitials = (name: string) => { const words = name.split(/\s+/); if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase(); return name.slice(0, 2).toUpperCase() }

  if (isLoading) {
    if (compact) return (<Button variant="ghost" size="icon" className="w-10 h-10 rounded-xl" disabled><Building2 className="w-5 h-5 animate-pulse" /></Button>)
    return (<div className="px-2"><Button variant="ghost" className="w-full justify-between h-12" disabled>Loading...<ChevronDown className="h-4 w-4" /></Button></div>)
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
          <DropdownMenuItem
            className="text-destructive focus:text-destructive py-2.5"
            onClick={() => setDeleteDialogOpen(true)}
          >
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

  //Compact mode: icon button with initials
  if (compact) {
    return (
      <DropdownMenu>
        <Tooltip>
          <TooltipTrigger asChild>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 hover:from-primary/30 hover:to-primary/10 text-primary font-bold">
                {currentBrand ? getInitials(currentBrand.name) : <Building2 className="w-5 h-5" />}
              </Button>
            </DropdownMenuTrigger>
          </TooltipTrigger>
          <TooltipContent side="right" className="font-semibold">{currentBrand?.name || 'Select Brand'}</TooltipContent>
        </Tooltip>
        {dropdownContent}
        {dialogs}
      </DropdownMenu>
    )
  }

  //Full mode: button with name
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="w-full justify-between h-auto py-3 px-3 hover:bg-sidebar-accent groupe rounded-xl">
          <div className="flex items-center gap-3 text-left">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-primary font-bold text-xs shrink-0">
              {currentBrand ? getInitials(currentBrand.name) : <Building2 className="w-4 h-4" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-sm truncate leading-none mb-1">{currentBrand?.name || 'Select Brand'}</div>
              <div className="text-[10px] text-muted-foreground font-medium">Brand Workspace</div>
            </div>
          </div>
          <ChevronsUpDown className="h-4 w-4 text-muted-foreground/50" />
        </Button>
      </DropdownMenuTrigger>
      {dropdownContent}
      {dialogs}
    </DropdownMenu>
  )
}
