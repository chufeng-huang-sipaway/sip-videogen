import{useState,useEffect,useCallback}from'react'
import{FolderKanban}from'lucide-react'
import{Button}from'@/components/ui/button'
import{FormDialog}from'@/components/ui/form-dialog'
import{Input}from'@/components/ui/input'
import{useProjects}from'@/context/ProjectContext'
import{useAsyncAction}from'@/hooks/useAsyncAction'
import type{ProjectFull}from'@/lib/bridge'
interface EditProjectDialogProps{open:boolean;onOpenChange:(open:boolean)=>void;projectSlug:string}
export function EditProjectDialog({open,onOpenChange,projectSlug}:EditProjectDialogProps){
const{getProject,updateProject,refresh}=useProjects()
const[name,setName]=useState('')
const[instructions,setInstructions]=useState('')
const[isLoading,setIsLoading]=useState(true)
const[loadError,setLoadError]=useState<string|null>(null)
const[originalProject,setOriginalProject]=useState<ProjectFull|null>(null)
//Load project data when dialog opens
useEffect(()=>{if(!open||!projectSlug)return
let cancelled=false
async function load(){setIsLoading(true);setLoadError(null)
try{const project=await getProject(projectSlug)
if(!cancelled){setOriginalProject(project);setName(project.name);setInstructions(project.instructions||'')}
}catch(err){if(!cancelled)setLoadError(err instanceof Error?err.message:'Failed to load project')
}finally{if(!cancelled)setIsLoading(false)}}
load();return()=>{cancelled=true}},[open,projectSlug,getProject])
const{execute:save,isLoading:isSaving,error:saveError,clearError}=useAsyncAction(async()=>{
if(!name.trim())throw new Error('Please enter a project name.')
await updateProject(projectSlug,name.trim(),instructions.trim()||undefined,undefined)
await refresh();onOpenChange(false)})
const handleClose=useCallback(()=>{if(!isSaving){onOpenChange(false);clearError()}},[isSaving,onOpenChange,clearError])
const hasChanges=originalProject&&(name.trim()!==originalProject.name||(instructions.trim()||'')!==(originalProject.instructions||''))
const isWorking=isLoading||isSaving
const error=loadError||saveError
const loadingMsg=isLoading?'Loading project...':'Saving changes...'
return(<FormDialog open={open} onOpenChange={handleClose} title="Edit Project" description="Update project name and campaign instructions." icon={<FolderKanban className="h-5 w-5"/>} iconColor="text-green-600" isLoading={isWorking} loadingMessage={loadingMsg} error={error} onClearError={clearError} footer={<>
<Button variant="outline" onClick={handleClose} disabled={isSaving}>Cancel</Button>
<Button onClick={()=>save()} disabled={isWorking||!name.trim()||!hasChanges} className="bg-green-600 hover:bg-green-700">{isSaving?'Saving...':'Save Changes'}</Button>
</>}>
{/* Name Input */}
<div className="space-y-2">
<label htmlFor="edit-project-name" className="text-sm font-medium">Name <span className="text-red-500">*</span></label>
<Input id="edit-project-name" value={name} onChange={(e)=>setName(e.target.value)} placeholder="e.g., Christmas Campaign" autoFocus/>
</div>
{/* Instructions Input */}
<div className="space-y-2">
<label htmlFor="edit-project-instructions" className="text-sm font-medium">Campaign Instructions</label>
<textarea id="edit-project-instructions" value={instructions} onChange={(e)=>setInstructions(e.target.value)} placeholder="Instructions for the AI when generating content for this campaign..." rows={5} className="w-full px-3 py-2 text-sm border rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-green-500 resize-none"/>
<p className="text-xs text-muted-foreground">These instructions will guide the AI when creating images for this project.</p>
</div>
</FormDialog>)}
