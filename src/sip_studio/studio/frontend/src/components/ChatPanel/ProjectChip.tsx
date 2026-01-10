//Project chip - subtle chip in settings row showing active project with popover selection
import{useState}from'react'
import{FolderKanban,ChevronDown,Check}from'lucide-react'
import{cn}from'@/lib/utils'
import{Popover,PopoverTrigger,PopoverContent}from'@/components/ui/popover'
import type{ProjectEntry}from'@/lib/bridge'
interface ProjectChipProps{projects:ProjectEntry[];activeProject:string|null;onSelect:(slug:string|null)=>Promise<void>;disabled?:boolean}
export function ProjectChip({projects,activeProject,onSelect,disabled=false}:ProjectChipProps){
const[open,setOpen]=useState(false)
const activeProjects=projects.filter(p=>p.status==='active')
const currentProject=projects.find(p=>p.slug===activeProject)
const handleSelect=async(slug:string|null)=>{await onSelect(slug);setOpen(false)}
return(
<Popover open={open} onOpenChange={setOpen}>
<PopoverTrigger asChild>
<button type="button" disabled={disabled} className={cn("flex items-center gap-1.5 h-8 px-2.5 rounded-full text-xs font-medium transition-all bg-white/50 dark:bg-white/10 border border-border/40","text-muted-foreground hover:text-foreground hover:bg-white/80 dark:hover:bg-white/20",disabled&&"opacity-50 cursor-not-allowed")} title={currentProject?`Project: ${currentProject.name}`:"No project selected"}>
<FolderKanban className="h-3.5 w-3.5 opacity-70"/>
<span className="truncate max-w-[120px]">{currentProject?.name||'Project'}</span>
<ChevronDown className="h-3 w-3 text-muted-foreground/50 ml-0.5"/>
</button>
</PopoverTrigger>
<PopoverContent align="start" side="top" sideOffset={8} className="w-56 p-0">
<div className="p-2 space-y-0.5">
<div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider px-2 py-1.5">Project Scope</div>
{/* No Project option */}
<button type="button" onClick={()=>handleSelect(null)} className={cn("w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm transition-all hover:bg-accent/50",!activeProject&&"bg-accent")}>
<span className="flex-1 text-left text-muted-foreground">No Project</span>
{!activeProject&&<Check className="h-4 w-4 text-primary"/>}
</button>
{/* Separator if there are projects */}
{activeProjects.length>0&&<div className="h-px bg-border/40 my-1.5"/>}
{/* Project list */}
{activeProjects.map(p=>(
<button key={p.slug} type="button" onClick={()=>handleSelect(p.slug)} className={cn("w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm transition-all hover:bg-accent/50",p.slug===activeProject&&"bg-accent")}>
<span className="flex-1 text-left truncate">{p.name}</span>
{p.slug===activeProject&&<Check className="h-4 w-4 text-primary"/>}
</button>
))}
{/* Empty state */}
{activeProjects.length===0&&(
<div className="px-2 py-1.5 text-xs text-muted-foreground/60 italic">No projects yet</div>
)}
</div>
<div className="px-3 py-2 bg-muted/30 border-t border-border/40 text-xs text-muted-foreground">
Context for project-specific knowledge
</div>
</PopoverContent>
</Popover>)
}
