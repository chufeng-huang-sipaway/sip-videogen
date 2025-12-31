//IdeasActionBar - Action buttons for inspiration review (Save, More Like This, Dismiss)
import{useState}from'react'
import{useInspirationContext}from'@/context/InspirationContext'
import{useProjects}from'@/context/ProjectContext'
import type{Inspiration}from'@/lib/bridge'
import{Button}from'@/components/ui/button'
import{DropdownMenu,DropdownMenuContent,DropdownMenuItem,DropdownMenuTrigger,DropdownMenuSeparator}from'@/components/ui/dropdown-menu'
import{Download,Sparkles,X,ChevronDown,FolderOpen,Check}from'lucide-react'
import{cn}from'@/lib/utils'
interface Props{
inspiration:Inspiration
imageIndex:number
onDismiss:()=>Promise<void>
isGenerating:boolean
}
export function IdeasActionBar({inspiration,imageIndex,onDismiss,isGenerating}:Props){
const{save,moreLikeThis}=useInspirationContext()
const{projects,activeProject}=useProjects()
const[saving,setSaving]=useState(false)
const[moreLoading,setMoreLoading]=useState(false)
const activeProjectName=projects.find(p=>p.slug===activeProject)?.name||'Unsorted'
const handleSave=async(projectSlug?:string|null)=>{
if(!inspiration||saving)return
setSaving(true)
try{await save(inspiration.id,imageIndex,projectSlug??activeProject)}
catch(e){console.error('Save error:',e)}
finally{setSaving(false)}
}
const handleMoreLikeThis=async()=>{
if(!inspiration||isGenerating||moreLoading)return
setMoreLoading(true)
try{await moreLikeThis(inspiration.id)}
catch(e){console.error('More like this error:',e)}
finally{setMoreLoading(false)}
}
const handleDismiss=async()=>{
if(!inspiration)return
try{await onDismiss()}
catch(e){console.error('Dismiss error:',e)}
}
return(<div className="flex items-center justify-center gap-2 px-4 py-2 rounded-full bg-neutral-900/70 dark:bg-neutral-800/80 backdrop-blur-xl shadow-float border border-neutral-700/30 dark:border-neutral-600/30">
{/* Save button with dropdown */}
<DropdownMenu>
<DropdownMenuTrigger asChild>
<Button variant="default" size="sm" className="gap-1.5 px-4" disabled={saving}>
<Download className="w-4 h-4"/>{saving?'Saving...':'Save'}
<ChevronDown className="w-3 h-3 ml-1 opacity-70"/>
</Button>
</DropdownMenuTrigger>
<DropdownMenuContent align="center" className="w-48">
{/* Quick save to active project */}
<DropdownMenuItem onClick={()=>handleSave(activeProject)} className="gap-2">
<Check className="w-4 h-4"/>Save to {activeProjectName}
</DropdownMenuItem>
<DropdownMenuSeparator/>
{/* Project list */}
<DropdownMenuItem onClick={()=>handleSave(null)} className={cn("gap-2",!activeProject&&"bg-accent")}>
<FolderOpen className="w-4 h-4"/>Unsorted
</DropdownMenuItem>
{projects.map(p=>(
<DropdownMenuItem key={p.slug} onClick={()=>handleSave(p.slug)} className={cn("gap-2",p.slug===activeProject&&"bg-accent")}>
<FolderOpen className="w-4 h-4"/>{p.name}
</DropdownMenuItem>
))}
</DropdownMenuContent>
</DropdownMenu>
{/* More Like This */}
<Button variant="ghost" size="sm" onClick={handleMoreLikeThis} disabled={isGenerating||moreLoading} className="gap-1.5 text-white/90 hover:bg-white/10 hover:text-white">
<Sparkles className="w-4 h-4"/>{moreLoading?'Generating...':'More Like This'}
</Button>
{/* Dismiss */}
<Button variant="ghost" size="sm" onClick={handleDismiss} className="gap-1.5 text-white/70 hover:bg-white/10 hover:text-white">
<X className="w-4 h-4"/>Dismiss
</Button>
</div>)
}
