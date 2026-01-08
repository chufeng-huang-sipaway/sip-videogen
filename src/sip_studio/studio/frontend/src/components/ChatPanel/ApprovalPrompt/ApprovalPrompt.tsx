//ApprovalPrompt - modal dialog for user approval of sensitive operations
import{useState,useEffect}from'react'
import{Check,X,Edit2,CheckCheck,Clock,SkipForward}from'lucide-react'
import{Dialog,DialogContent,DialogHeader,DialogTitle,DialogDescription,DialogFooter}from'@/components/ui/dialog'
import{Button}from'@/components/ui/button'
import type{ApprovalRequest}from'@/types/approval'
interface ApprovalPromptProps{
approval:ApprovalRequest|null
onApprove:()=>void
onReject:()=>void
onEdit:(modifiedPrompt:string)=>void
onApproveAll:()=>void
onSkip?:()=>void}
export function ApprovalPrompt({approval,onApprove,onReject,onEdit,onApproveAll,onSkip}:ApprovalPromptProps){
const[editMode,setEditMode]=useState(false)
const[editedPrompt,setEditedPrompt]=useState('')
const[timeRemaining,setTimeRemaining]=useState<number|null>(null)
//Reset edit mode when approval changes
useEffect(()=>{
if(approval){setEditMode(false);setEditedPrompt(approval.prompt)}
else{setEditMode(false);setEditedPrompt('')}},[approval])
//Countdown timer
useEffect(()=>{
if(!approval?.expiresAt)return
const updateTime=()=>{
const expires=new Date(approval.expiresAt!).getTime()
const now=Date.now()
const remaining=Math.max(0,Math.floor((expires-now)/1000))
setTimeRemaining(remaining)}
updateTime()
const interval=setInterval(updateTime,1000)
return()=>clearInterval(interval)},[approval?.expiresAt])
if(!approval)return null
const handleSubmitEdit=()=>{
if(editedPrompt.trim()&&editedPrompt!==approval.prompt){onEdit(editedPrompt)}
else{setEditMode(false)}}
return(<Dialog open={!!approval} onOpenChange={()=>{}}>
<DialogContent className="sm:max-w-md" onPointerDownOutside={(e)=>e.preventDefault()} onEscapeKeyDown={(e)=>e.preventDefault()}>
<DialogHeader>
<DialogTitle className="flex items-center gap-2">
<span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"/>
Approval Required
</DialogTitle>
<DialogDescription>
The agent wants to execute <span className="font-medium text-foreground">{approval.toolName}</span>
</DialogDescription>
</DialogHeader>
<div className="py-4">
{editMode?(<textarea value={editedPrompt} onChange={(e)=>setEditedPrompt(e.target.value)} className="w-full h-32 p-3 text-sm border border-border rounded-lg bg-muted/50 focus:outline-none focus:ring-2 focus:ring-ring resize-none" placeholder="Edit the prompt..."/>):(<div className="p-3 bg-muted/50 rounded-lg border border-border">
<p className="text-sm whitespace-pre-wrap">{approval.prompt}</p>
</div>)}
{approval.previewUrl&&(<div className="mt-3">
<img src={approval.previewUrl} alt="Preview" className="max-h-48 rounded-lg border border-border"/>
</div>)}
{timeRemaining!==null&&(<div className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground">
<Clock className="h-3 w-3"/>
<span>Expires in {timeRemaining}s</span>
</div>)}
</div>
<DialogFooter className="flex-col sm:flex-row gap-2">
{editMode?(<>
<Button variant="outline" size="sm" onClick={()=>setEditMode(false)} className="gap-1.5">
<X className="h-3.5 w-3.5"/>Cancel
</Button>
<Button size="sm" onClick={handleSubmitEdit} className="gap-1.5">
<Check className="h-3.5 w-3.5"/>Submit Edit
</Button>
</>):(<>
<Button variant="ghost" size="sm" onClick={onReject} className="gap-1.5 text-destructive hover:text-destructive">
<X className="h-3.5 w-3.5"/>Reject
</Button>
{onSkip&&(<Button variant="ghost" size="sm" onClick={onSkip} className="gap-1.5">
<SkipForward className="h-3.5 w-3.5"/>Skip
</Button>)}
<Button variant="outline" size="sm" onClick={()=>setEditMode(true)} className="gap-1.5">
<Edit2 className="h-3.5 w-3.5"/>Modify
</Button>
<Button variant="outline" size="sm" onClick={onApproveAll} className="gap-1.5">
<CheckCheck className="h-3.5 w-3.5"/>Accept All Auto
</Button>
<Button size="sm" onClick={onApprove} className="gap-1.5">
<Check className="h-3.5 w-3.5"/>Approve
</Button>
</>)}
</DialogFooter>
</DialogContent>
</Dialog>)}
