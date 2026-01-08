//TodoControls - Pause/Resume/Stop/NewDirection controls for todo list
import{useState,useCallback}from'react'
import{Pause,Play,Square,MessageSquare,Send,X}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Input}from'@/components/ui/input'
import{cn}from'@/lib/utils'
interface TodoControlsProps{
isPaused:boolean
isGenerating:boolean
onPause:()=>void
onResume:()=>void
onStop:()=>void
onNewDirection?:(message:string)=>void
className?:string}
export function TodoControls({isPaused,isGenerating,onPause,onResume,onStop,onNewDirection,className}:TodoControlsProps){
const[showInput,setShowInput]=useState(false)
const[message,setMessage]=useState('')
const handleSubmitNewDirection=useCallback(()=>{
if(!message.trim()||!onNewDirection)return
onNewDirection(message.trim())
setShowInput(false)
setMessage('')
},[message,onNewDirection])
if(!isGenerating&&!isPaused)return null
//Show input mode for new direction
if(showInput){return(<div className={cn('flex items-center gap-2',className)}>
<Input value={message} onChange={(e)=>setMessage(e.target.value)} placeholder="New direction..." className="h-7 text-xs flex-1" autoFocus onKeyDown={(e)=>{if(e.key==='Enter')handleSubmitNewDirection();if(e.key==='Escape'){setShowInput(false);setMessage('')}}}/>
<Button variant="ghost" size="sm" onClick={handleSubmitNewDirection} disabled={!message.trim()} className="h-7 w-7 p-0">
<Send className="h-3 w-3"/></Button>
<Button variant="ghost" size="sm" onClick={()=>{setShowInput(false);setMessage('')}} className="h-7 w-7 p-0">
<X className="h-3 w-3"/></Button>
</div>)}
//Normal controls
return(<div className={cn('flex items-center gap-2',className)}>
{isPaused?(<Button variant="ghost" size="sm" onClick={onResume} className="h-7 gap-1.5 text-xs">
<Play className="h-3 w-3"/>Resume</Button>):isGenerating?(<Button variant="ghost" size="sm" onClick={onPause} className="h-7 gap-1.5 text-xs">
<Pause className="h-3 w-3"/>Pause</Button>):null}
{(isGenerating||isPaused)&&(<>
<Button variant="ghost" size="sm" onClick={onStop} className="h-7 gap-1.5 text-xs text-destructive hover:text-destructive">
<Square className="h-3 w-3"/>Stop</Button>
{onNewDirection&&(<Button variant="ghost" size="sm" onClick={()=>setShowInput(true)} className="h-7 gap-1.5 text-xs">
<MessageSquare className="h-3 w-3"/>New Direction</Button>)}
</>)}</div>)}
