import{ScrollArea}from'@/components/ui/scroll-area'
import{Sparkles}from'lucide-react'

interface InspirationsTabProps{brandSlug:string|null}

//Placeholder skeleton card for loading state
function SkeletonCard(){
return(
<div className="bg-white/50 dark:bg-white/5 rounded-xl p-4 space-y-3 animate-pulse">
<div className="h-4 bg-muted rounded w-3/4"/>
<div className="h-3 bg-muted rounded w-full"/>
<div className="h-3 bg-muted rounded w-2/3"/>
<div className="grid grid-cols-3 gap-2 pt-2">
<div className="aspect-square bg-muted rounded-lg"/>
<div className="aspect-square bg-muted rounded-lg"/>
<div className="aspect-square bg-muted rounded-lg"/>
</div>
</div>
)
}

export function InspirationsTab({brandSlug}:InspirationsTabProps){
//Placeholder - will be replaced in Stage 3 with actual inspiration cards
if(!brandSlug){
return(
<div className="flex-1 flex flex-col items-center justify-center px-6 py-12 text-center">
<div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
<Sparkles className="w-6 h-6 text-muted-foreground"/>
</div>
<h3 className="text-sm font-medium text-foreground mb-1">Select a Brand</h3>
<p className="text-xs text-muted-foreground">Choose a brand to see creative inspirations</p>
</div>
)
}
//Show skeleton cards during initial load (placeholder for Stage 3)
return(
<ScrollArea className="flex-1">
<div className="p-4 space-y-4">
<SkeletonCard/>
<SkeletonCard/>
<SkeletonCard/>
</div>
</ScrollArea>
)
}
