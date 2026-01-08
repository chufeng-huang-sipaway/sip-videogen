//ApprovalPrompt - Displays approval request for supervised mode
import{useState,useEffect}from'react'
import{Check,FastForward,Pencil,X}from'lucide-react'
import type{ApprovalRequestData}from'@/lib/types/approval'
import'./ApprovalPrompt.css'
interface ApprovalPromptProps{
  request:ApprovalRequestData
  onApprove:()=>void
  onApproveAll:()=>void
  onModify:(newPrompt:string)=>void
  onSkip:()=>void
}
const actionLabels:Record<string,string>={generate_image:'generate an image',create_style_reference:'create a style reference'}
export function ApprovalPrompt({request,onApprove,onApproveAll,onModify,onSkip}:ApprovalPromptProps){
const [editing,setEditing]=useState(false)
const [editedPrompt,setEditedPrompt]=useState(request.prompt||'')
//Reset edited prompt when request changes
useEffect(()=>{setEditedPrompt(request.prompt||'');setEditing(false)},[request.id])
const actionLabel=actionLabels[request.actionType]||request.actionType
return(<div className="approval-prompt">
<div className="approval-header">I'm about to {actionLabel}:</div>
<div className="approval-description">{request.description}</div>
{request.prompt&&(<div className="approval-prompt-text">
{editing?(<textarea value={editedPrompt} onChange={e=>setEditedPrompt(e.target.value)} rows={4} className="approval-textarea"/>
):(<code className="approval-code">{request.prompt}</code>)}
</div>)}
<div className="approval-actions">
{editing?(<>
<button className="approval-btn approval-btn--primary" onClick={()=>{onModify(editedPrompt);setEditing(false)}}><Check className="btn-icon"/>Apply</button>
<button className="approval-btn approval-btn--secondary" onClick={()=>{setEditing(false);setEditedPrompt(request.prompt||'')}}><X className="btn-icon"/>Cancel</button>
</>):(<>
<button className="approval-btn approval-btn--primary" onClick={onApprove}><Check className="btn-icon"/>Approve</button>
<button className="approval-btn approval-btn--success" onClick={onApproveAll} title="Approve this and all future actions (switches to Auto mode)"><FastForward className="btn-icon"/>Approve All</button>
{request.prompt&&<button className="approval-btn approval-btn--secondary" onClick={()=>setEditing(true)}><Pencil className="btn-icon"/>Edit</button>}
<button className="approval-btn approval-btn--danger" onClick={onSkip}><X className="btn-icon"/>Skip</button>
</>)}
</div>
</div>)}
