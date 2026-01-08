//Panel mode toggle for Creative Director vs Quick Create
import{Wand2,Zap}from'lucide-react'
import{cn}from'@/lib/utils'
export type PanelMode='assistant'|'playground'
interface PanelModeToggleProps{value:PanelMode;onChange:(m:PanelMode)=>void;disabled?:boolean}
export function PanelModeToggle({value,onChange,disabled}:PanelModeToggleProps){
const isPlayground=value==='playground'
return(<div className={cn("inline-flex items-center gap-0.5 p-0.5 rounded-full bg-white/50 dark:bg-white/10 border border-border/40",disabled&&"opacity-50 pointer-events-none")}>
<button type="button" onClick={()=>onChange('assistant')} className={cn("flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all",!isPlayground?"bg-white dark:bg-white/20 shadow-sm text-foreground":"text-muted-foreground hover:text-foreground")} disabled={disabled}><Wand2 className="w-4 h-4"/><span>Creative Director</span></button>
<button type="button" onClick={()=>onChange('playground')} className={cn("flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all",isPlayground?"bg-white dark:bg-white/20 shadow-sm text-foreground":"text-muted-foreground hover:text-foreground")} disabled={disabled}><Zap className="w-4 h-4"/><span>Quick Create</span></button>
</div>)}
