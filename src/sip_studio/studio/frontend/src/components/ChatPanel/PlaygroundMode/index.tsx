//Playground mode for quick image generation (placeholder - implemented in Phase 4)
import{Sparkles}from'lucide-react'
interface PlaygroundModeProps{brandSlug:string|null}
export function PlaygroundMode({brandSlug}:PlaygroundModeProps){
return(<div className="flex flex-col items-center justify-center h-full text-center p-8">
<div className="w-16 h-16 rounded-full bg-secondary flex items-center justify-center mb-4">
<Sparkles className="w-8 h-8 text-muted-foreground"/>
</div>
<h3 className="text-lg font-medium">Playground Mode</h3>
<p className="text-sm text-muted-foreground mt-2 max-w-xs">Quick image generation coming in Phase 4</p>
{brandSlug&&<p className="text-xs text-muted-foreground mt-4">Brand: {brandSlug}</p>}
</div>)}
