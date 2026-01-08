//QuickGeneratorFAB - floating action button to open quick generator
import{Sparkles}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Tooltip,TooltipContent,TooltipProvider,TooltipTrigger}from'@/components/ui/tooltip'
interface QuickGeneratorFABProps{
onClick:()=>void
disabled?:boolean}
export function QuickGeneratorFAB({onClick,disabled}:QuickGeneratorFABProps){
return(<TooltipProvider delayDuration={300}>
<Tooltip>
<TooltipTrigger asChild>
<Button onClick={onClick} disabled={disabled} size="icon" className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg bg-primary hover:bg-primary/90 text-primary-foreground z-40" aria-label="Quick Generate">
<Sparkles className="h-6 w-6"/>
</Button>
</TooltipTrigger>
<TooltipContent side="left" sideOffset={8}>
<p>Quick Generate Images</p>
</TooltipContent>
</Tooltip>
</TooltipProvider>)}
