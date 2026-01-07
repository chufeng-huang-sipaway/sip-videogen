//Mode toggle for image vs video generation
import{Image,Video}from'lucide-react'
import{cn}from'@/lib/utils'
import type{GenerationMode}from'@/types/aspectRatio'
interface ModeToggleProps{value:GenerationMode;onChange:(m:GenerationMode)=>void;disabled?:boolean}
export function ModeToggle({value,onChange,disabled}:ModeToggleProps){
const isVideo=value==='video'
return(<div className={cn("inline-flex items-center gap-0.5 p-0.5 rounded-full bg-white/50 dark:bg-white/10 border border-border/40",disabled&&"opacity-50 pointer-events-none")}>
<button type="button" onClick={()=>onChange('image')} className={cn("flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all",!isVideo?"bg-white dark:bg-white/20 shadow-sm text-foreground":"text-muted-foreground hover:text-foreground")} disabled={disabled}><Image className="w-3.5 h-3.5"/><span>Image</span></button>
<button type="button" onClick={()=>onChange('video')} className={cn("flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all",isVideo?"bg-white dark:bg-white/20 shadow-sm text-foreground":"text-muted-foreground hover:text-foreground")} disabled={disabled}><Video className="w-3.5 h-3.5"/><span>Video</span></button>
</div>)}
