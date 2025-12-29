import { useState } from 'react'
import { ChevronDown, Plus, Check, Trash2, Building2 } from 'lucide-react'
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

interface BrandSelectorProps{compact?:boolean}

export function BrandSelector({compact}:BrandSelectorProps={}){
  const { brands, activeBrand, isLoading, selectBrand, refresh } = useBrand()
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const currentBrand = brands.find(b => b.slug === activeBrand)
  //Get initials from brand name (first letter of first two words, or first two letters)
  const getInitials=(name:string)=>{const words=name.split(/\s+/);if(words.length>=2)return(words[0][0]+words[1][0]).toUpperCase();return name.slice(0,2).toUpperCase()}

  if(isLoading){
    if(compact)return(<Button variant="ghost" size="icon" className="w-10 h-10 rounded-2xl" disabled><Building2 className="w-5 h-5 animate-pulse"/></Button>)
    return(<Button variant="outline" className="w-full justify-between" disabled>Loading...<ChevronDown className="h-4 w-4"/></Button>)
  }

  const dropdownContent=(
    <DropdownMenuContent className="w-56" side={compact?"right":"bottom"} align={compact?"start":"center"}>
      {brands.length === 0 ? (
        <DropdownMenuItem disabled>No brands found</DropdownMenuItem>
      ) : (
        brands.map((brand) => (
          <DropdownMenuItem key={brand.slug} onClick={() => selectBrand(brand.slug)}>
            <span className="flex-1">{brand.name}</span>
            {brand.slug === activeBrand && <Check className="h-4 w-4 text-green-500" />}
          </DropdownMenuItem>
        ))
      )}
      <DropdownMenuSeparator />
      <DropdownMenuItem onClick={() => setCreateDialogOpen(true)}>
        <Plus className="h-4 w-4 mr-2" />
        Create New Brand
      </DropdownMenuItem>
      {currentBrand && (
        <>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            className="text-destructive focus:text-destructive"
            onClick={() => setDeleteDialogOpen(true)}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete "{currentBrand.name}"
          </DropdownMenuItem>
        </>
      )}
    </DropdownMenuContent>
  )

  const dialogs=(
    <>
      <DeleteBrandDialog brand={currentBrand??null} open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen} onDeleted={refresh}/>
      <CreateBrandDialog open={createDialogOpen} onOpenChange={setCreateDialogOpen} onCreated={async(slug)=>{await refresh();await selectBrand(slug)}}/>
    </>
  )

  //Compact mode: icon button with initials
  if(compact){
    return(
      <DropdownMenu>
        <Tooltip>
          <TooltipTrigger asChild>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon" className="w-10 h-10 rounded-2xl text-xs font-semibold">
                {currentBrand?getInitials(currentBrand.name):<Building2 className="w-5 h-5"/>}
              </Button>
            </DropdownMenuTrigger>
          </TooltipTrigger>
          <TooltipContent side="right">{currentBrand?.name||'Select Brand'}</TooltipContent>
        </Tooltip>
        {dropdownContent}
        {dialogs}
      </DropdownMenu>
    )
  }

  //Full mode: button with name
  return(
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" className="w-full justify-between">
          <span className="truncate">{currentBrand?.name || 'Select Brand...'}</span>
          <ChevronDown className="h-4 w-4 ml-2" />
        </Button>
      </DropdownMenuTrigger>
      {dropdownContent}
      {dialogs}
    </DropdownMenu>
  )
}
