//AutonomyToggle - Segmented control for supervised vs autonomous modes
import{Bot,Shield}from'lucide-react'
import{cn}from'@/lib/utils'
interface AutonomyToggleProps{enabled:boolean;onChange:(enabled:boolean)=>void;disabled?:boolean}
export function AutonomyToggle({enabled,onChange,disabled}:AutonomyToggleProps){
return(<div className={cn("inline-flex items-center gap-0.5 p-0.5 rounded-lg bg-white/50 dark:bg-white/10 border border-border/40",disabled&&"opacity-50 pointer-events-none")}>
<button type="button" onClick={()=>onChange(false)} disabled={disabled} className={cn("flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all",!enabled?"bg-background shadow-sm text-foreground":"text-muted-foreground hover:text-foreground")}>
<Shield className="h-3.5 w-3.5"/>
<span>Supervised</span>
</button>
<button type="button" onClick={()=>onChange(true)} disabled={disabled} className={cn("flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all",enabled?"bg-background shadow-sm text-foreground":"text-muted-foreground hover:text-foreground")}>
<Bot className="h-3.5 w-3.5"/>
<span>Auto</span>
</button>
</div>)}
