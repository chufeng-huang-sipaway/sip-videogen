import { ChevronDown, Plus, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useBrand } from '@/context/BrandContext'

export function BrandSelector() {
  const { brands, activeBrand, isLoading, selectBrand } = useBrand()
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
        <DropdownMenuItem disabled>
          <Plus className="h-4 w-4 mr-2" />
          Create New Brand
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
