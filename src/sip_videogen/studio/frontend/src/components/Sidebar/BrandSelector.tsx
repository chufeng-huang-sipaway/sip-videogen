import { useState } from 'react'
import { ChevronDown, Plus, Check, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
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

export function BrandSelector() {
  const { brands, activeBrand, isLoading, selectBrand, refresh } = useBrand()
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const currentBrand = brands.find(b => b.slug === activeBrand)

  if (isLoading) {
    return (
      <Button variant="outline" className="w-full justify-between" disabled>
        Loading...
        <ChevronDown className="h-4 w-4" />
      </Button>
    )
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" className="w-full justify-between">
          <span className="truncate">{currentBrand?.name || 'Select Brand...'}</span>
          <ChevronDown className="h-4 w-4 ml-2" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56">
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
              className="text-red-600 focus:text-red-600"
              onClick={() => setDeleteDialogOpen(true)}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete "{currentBrand.name}"
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>

      <DeleteBrandDialog
        brand={currentBrand ?? null}
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onDeleted={refresh}
      />

      <CreateBrandDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onCreated={async (slug) => {
          await refresh()
          await selectBrand(slug)
        }}
      />
    </DropdownMenu>
  )
}
