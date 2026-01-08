//TodoControls - Pause/Resume/Stop controls for todo list
import{Pause,Play,Square}from'lucide-react'
import{Button}from'@/components/ui/button'
import{cn}from'@/lib/utils'
interface TodoControlsProps{
isPaused:boolean
isGenerating:boolean
onPause:()=>void
onResume:()=>void
onStop:()=>void
className?:string}
export function TodoControls({isPaused,isGenerating,onPause,onResume,onStop,className}:TodoControlsProps){
if(!isGenerating&&!isPaused)return null
return(<div className={cn('flex items-center gap-2',className)}>
{isPaused?(<Button variant="ghost" size="sm" onClick={onResume} className="h-7 gap-1.5 text-xs">
<Play className="h-3 w-3"/>Resume</Button>):isGenerating?(<Button variant="ghost" size="sm" onClick={onPause} className="h-7 gap-1.5 text-xs">
<Pause className="h-3 w-3"/>Pause</Button>):null}
{(isGenerating||isPaused)&&(<Button variant="ghost" size="sm" onClick={onStop} className="h-7 gap-1.5 text-xs text-destructive hover:text-destructive">
<Square className="h-3 w-3"/>Stop</Button>)}</div>)}
