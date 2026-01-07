import{useState,useCallback}from'react'
import{FolderKanban}from'lucide-react'
import{Button}from'@/components/ui/button'
import{FormDialog}from'@/components/ui/form-dialog'
import{Input}from'@/components/ui/input'
import{useProjects}from'@/context/ProjectContext'
import{useAsyncAction}from'@/hooks/useAsyncAction'
interface CreateProjectDialogProps{open:boolean;onOpenChange:(open:boolean)=>void}
export function CreateProjectDialog({open,onOpenChange}:CreateProjectDialogProps){
const{createProject}=useProjects()
const[name,setName]=useState('')
const[instructions,setInstructions]=useState('')
const{execute,isLoading,error,clearError}=useAsyncAction(async()=>{
if(!name.trim())throw new Error('Please enter a project name.')
await createProject(name.trim(),instructions.trim()||undefined)
setName('');setInstructions('');onOpenChange(false)
})
const handleClose=useCallback(()=>{if(!isLoading){onOpenChange(false);clearError();setName('');setInstructions('')}},[isLoading,onOpenChange,clearError])
const handleKeyDown=(e:React.KeyboardEvent)=>{if(e.key==='Enter'&&!e.shiftKey&&name.trim()){e.preventDefault();execute()}}
return(<FormDialog open={open} onOpenChange={handleClose} title="New Project" description="Create a new campaign project to organize generated assets." icon={<FolderKanban className="h-5 w-5"/>} iconColor="text-success" isLoading={isLoading} loadingMessage="Creating project..." error={error} onClearError={clearError} footer={<>
<Button variant="outline" onClick={handleClose} disabled={isLoading}>Cancel</Button>
<Button onClick={()=>execute()} disabled={isLoading||!name.trim()} className="bg-success hover:bg-success/90">{isLoading?'Creating...':'Create Project'}</Button>
</>}>
{/* Name Input */}
<div className="space-y-2">
<label htmlFor="create-project-name" className="text-sm font-medium">Name <span className="text-destructive">*</span></label>
<Input id="create-project-name" value={name} onChange={(e)=>setName(e.target.value)} onKeyDown={handleKeyDown} placeholder="e.g., Christmas Campaign" autoFocus/>
</div>
{/* Instructions Input */}
<div className="space-y-2">
<label htmlFor="create-project-instructions" className="text-sm font-medium">Campaign Instructions <span className="text-muted-foreground text-xs">(optional)</span></label>
<textarea id="create-project-instructions" value={instructions} onChange={(e)=>setInstructions(e.target.value)} placeholder="Instructions for the AI when generating content for this campaign..." rows={4} className="w-full px-3 py-2 text-sm border rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-success resize-none"/>
<p className="text-xs text-muted-foreground">These instructions will guide the AI when creating images for this project.</p>
</div>
</FormDialog>)}
