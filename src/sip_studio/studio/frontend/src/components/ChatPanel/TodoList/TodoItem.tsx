//TodoItem - Single todo item with status indicator
import{Loader2,CheckCircle2,AlertCircle,PauseCircle,SkipForward,XCircle}from'lucide-react'
import{cn}from'@/lib/utils'
import type{TodoItem as TodoItemType,TodoItemStatus}from'@/types/todo'
import{isTerminalStatus}from'@/types/todo'
//Status -> icon/color mapping
const STATUS_CONFIG:Record<TodoItemStatus,{icon:typeof Loader2;color:string;animate?:boolean}>={
pending:{icon:Loader2,color:'text-muted-foreground/40'},
in_progress:{icon:Loader2,color:'text-primary',animate:true},
done:{icon:CheckCircle2,color:'text-success'},
error:{icon:AlertCircle,color:'text-destructive'},
paused:{icon:PauseCircle,color:'text-warning'},
cancelled:{icon:XCircle,color:'text-muted-foreground/50'},
skipped:{icon:SkipForward,color:'text-muted-foreground/50'},}
interface TodoItemProps{item:TodoItemType;onSkip?:(id:string)=>void;disabled?:boolean}
export function TodoItem({item,onSkip,disabled}:TodoItemProps){
const cfg=STATUS_CONFIG[item.status]||STATUS_CONFIG.pending
const Icon=cfg.icon
const isTerminal=isTerminalStatus(item.status)
const canSkip=!isTerminal&&item.status!=='in_progress'&&onSkip
return(<div className={cn('flex items-start gap-2 py-1.5 text-sm group',isTerminal&&'opacity-60')}>
<Icon className={cn('h-4 w-4 mt-0.5 flex-shrink-0',cfg.color,cfg.animate&&'animate-spin')}/>
<div className="flex-1 min-w-0">
<span className={cn(item.status==='cancelled'||item.status==='skipped'?'line-through':'')}>{item.description}</span>
{item.error&&<p className="text-xs text-destructive mt-0.5">{item.error}</p>}
{item.outputs&&item.outputs.length>0&&<ul className="text-xs text-muted-foreground mt-0.5 space-y-0.5">
{item.outputs.map((o,i)=><li key={i}>• {o}</li>)}</ul>}</div>
{canSkip&&!disabled&&<button type="button" onClick={()=>onSkip(item.id)} className="opacity-0 group-hover:opacity-100 text-xs text-muted-foreground hover:text-foreground transition-opacity">Skip</button>}
</div>)}
