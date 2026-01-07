import { ChevronDown, Check, Building2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type { BrandEntry } from '@/lib/bridge'

interface BrandSelectorProps {
    brands: BrandEntry[]
    activeBrand: string | null
    onSelect: (slug: string) => Promise<void>
    disabled?: boolean
}

export function BrandSelector({
    brands,
    activeBrand,
    onSelect,
    disabled = false,
}: BrandSelectorProps) {
    const currentBrand = brands.find(b => b.slug === activeBrand)

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button
                    variant="ghost"
                    size="sm"
                    disabled={disabled}
                    className="gap-2 text-sm font-medium px-2 py-1 h-auto hover:bg-transparent hover:text-foreground text-foreground/80 transition-colors"
                >
                    <Building2 className="h-4 w-4 text-muted-foreground/70" />
                    <span className="truncate max-w-[140px] tracking-tight">
                        {currentBrand?.name || 'Select Brand'}
                    </span>
                    <ChevronDown className="h-3 w-3 opacity-30" />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-56">
                {brands.length > 0 ? (
                    <>
                        {brands.map((brand) => (
                            <DropdownMenuItem
                                key={brand.slug}
                                onClick={() => onSelect(brand.slug)}
                                className="gap-2"
                            >
                                <div className="flex items-center justify-center w-6 h-6 rounded bg-muted text-muted-foreground">
                                    {/* We could use brand logo if available later */}
                                    <span className="text-[10px] font-bold">{brand.name.substring(0, 1)}</span>
                                </div>
                                <span className="flex-1 truncate">{brand.name}</span>
                                {brand.slug === activeBrand && (
                                    <Check className="h-4 w-4 text-primary" />
                                )}
                            </DropdownMenuItem>
                        ))}
                    </>
                ) : (
                    <DropdownMenuItem disabled className="text-xs text-muted-foreground italic">
                        No brands available
                    </DropdownMenuItem>
                )}
            </DropdownMenuContent>
        </DropdownMenu>
    )
}
