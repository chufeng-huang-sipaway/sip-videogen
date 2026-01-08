//AutonomyToggle - Toggle between supervised and autonomous modes
import{Bot,Shield}from'lucide-react'
import{cn}from'@/lib/utils'
import'./AutonomyToggle.css'
interface AutonomyToggleProps{enabled:boolean;onChange:(enabled:boolean)=>void;disabled?:boolean}
export function AutonomyToggle({enabled,onChange,disabled}:AutonomyToggleProps){
return(<div className={cn("autonomy-toggle",disabled&&"autonomy-toggle--disabled")}>
<label className="toggle-label">
<span className={cn("toggle-text",enabled?"toggle-text--auto":"toggle-text--supervised")}>
{enabled?<Bot className="toggle-icon"/>:<Shield className="toggle-icon"/>}
{enabled?'Auto':'Supervised'}
</span>
<input type="checkbox" checked={enabled} onChange={e=>onChange(e.target.checked)} disabled={disabled} className="toggle-checkbox"/>
<span className="toggle-slider"/>
</label>
<span className="toggle-hint">{enabled?'Agent executes without asking':'Agent asks before each generation'}</span>
</div>)}
