//ApprovalPrompt - Displays approval request for supervised mode
import{useState,useEffect}from'react'
import{Check,ChevronDown,ChevronUp,MessageSquare}from'lucide-react'
import{cn}from'@/lib/utils'
import type{ApprovalRequestData}from'@/lib/types/approval'
interface ApprovalPromptProps{
request:ApprovalRequestData
onApproveAll:()=>void
onLetMeClarify:()=>void}
const actionLabels:Record<string,string>={generate_image:'generate an image',create_style_reference:'create a style reference'}
export function ApprovalPrompt({request,onApproveAll,onLetMeClarify}:ApprovalPromptProps){
const[expanded,setExpanded]=useState(false)
const actionLabel=actionLabels[request.actionType]||request.actionType
//Reset expanded state when request changes
useEffect(()=>{setExpanded(false)},[request.id])
const promptText=request.prompt||''
const truncated=promptText.length>120
const displayText=expanded||!truncated?promptText:promptText.slice(0,120)+'...'
return(<div className="bg-card border border-border/40 rounded-xl p-4 shadow-sm space-y-3">
<div className="text-sm font-medium text-foreground">Ready to {actionLabel}</div>
{request.description&&<div className="text-sm text-muted-foreground">{request.description}</div>}
{promptText&&(<div className="space-y-1">
<div className={cn("text-xs text-muted-foreground/80 font-mono bg-muted/50 rounded-lg p-3",!expanded&&truncated&&"line-clamp-3")}>{displayText}</div>
{truncated&&(<button type="button" onClick={()=>setExpanded(!expanded)} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors">
{expanded?<><ChevronUp className="h-3 w-3"/>Show less</>:<><ChevronDown className="h-3 w-3"/>Show full prompt</>}
</button>)}
</div>)}
<div className="flex items-center gap-3 pt-1">
<button type="button" onClick={onApproveAll} className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors" title="Accept and switch to auto mode">
<Check className="h-4 w-4"/>Accept All
</button>
<button type="button" onClick={onLetMeClarify} className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-transparent border border-border hover:bg-muted/50 text-foreground transition-colors" title="Skip this and provide new instructions">
<MessageSquare className="h-4 w-4"/>Let me clarify
</button>
</div>
</div>)}
