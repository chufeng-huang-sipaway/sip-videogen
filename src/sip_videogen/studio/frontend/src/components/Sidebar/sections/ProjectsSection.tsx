import{useState,useEffect}from'react'
import{FolderOpen,X,Archive,Inbox}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Alert,AlertDescription}from'@/components/ui/alert'
import{useProjects}from'@/context/ProjectContext'
import{useBrand}from'@/context/BrandContext'
import{useTabs}from'@/context/TabContext'
import{bridge,isPyWebView,type ProjectEntry}from'@/lib/bridge'
import{makeTabId}from'@/types/tabs'
//Simple project row component
interface ProjectRowProps{project:ProjectEntry;isTabOpen:boolean;onClick:()=>void}
function ProjectRow({project,isTabOpen,onClick}:ProjectRowProps){
const isArchived=project.status==='archived'
return(<div onClick={onClick} className={`flex items-center gap-2.5 py-1.5 px-2 rounded-md cursor-pointer group transition-all duration-200 overflow-hidden ${isTabOpen?'bg-sidebar-accent text-foreground shadow-sm font-medium':'text-muted-foreground/80 hover:bg-sidebar-accent/50 hover:text-foreground'} ${isArchived?'opacity-60':''}`} title="Open project tab">
<FolderOpen className={`h-4 w-4 shrink-0 transition-colors ${isTabOpen?'text-foreground':'text-muted-foreground/70 group-hover:text-foreground'}`} strokeWidth={1.5}/>
<div className="flex-1 min-w-0 overflow-hidden">
<div className="flex items-center gap-1.5"><span className="truncate flex-1">{project.name}</span>{isArchived&&<Archive className="h-3 w-3 text-muted-foreground shrink-0"/>}</div>
<span className={`text-[10px] truncate block mt-0.5 ${isTabOpen?'text-muted-foreground':'text-muted-foreground/60'}`}>{project.asset_count} asset{project.asset_count!==1?'s':''}</span>
</div></div>)}
export function ProjectsSection(){
const{activeBrand}=useBrand()
const{projects,isLoading,error,refresh}=useProjects()
const{tabs,openTab}=useTabs()
const[generalCount,setGeneralCount]=useState(0)
const[actionError,setActionError]=useState<string|null>(null)
//Load general assets count
useEffect(()=>{if(!activeBrand||!isPyWebView()){setGeneralCount(0);return}
bridge.getGeneralAssets(activeBrand).then(r=>setGeneralCount(r.count||0)).catch(()=>setGeneralCount(0))},[activeBrand])
useEffect(()=>{if(actionError){const timer=setTimeout(()=>setActionError(null),5000);return()=>clearTimeout(timer)}},[actionError])
//Check if a project tab is open
const isProjectTabOpen=(slug:string)=>{if(!activeBrand)return false;const tabId=makeTabId(activeBrand,'project',slug);return tabs.some(t=>t.id===tabId)}
//Check if unsorted tab is active
const isUnsortedTabOpen=()=>{if(!activeBrand)return false;const tabId=makeTabId(activeBrand,'project','unsorted');return tabs.some(t=>t.id===tabId)}
//Handle click to open tab
const handleProjectClick=(slug:string,name:string)=>{openTab('project',slug,name)}
const handleUnsortedClick=()=>{openTab('project','unsorted','Unsorted')}
if(!activeBrand){return<div className="text-sm text-muted-foreground">Select a brand</div>}
if(error){return(<div className="text-sm text-red-500">Error: {error}<Button variant="ghost" size="sm" onClick={refresh}>Retry</Button></div>)}
//Sort projects: active projects first, then by name
const sortedProjects=[...projects].sort((a,b)=>{if(a.status!==b.status)return a.status==='active'?-1:1;return a.name.localeCompare(b.name)})
return(<div className="space-y-2 pl-2 pr-1">
{actionError&&(<Alert variant="destructive" className="py-2 px-3"><AlertDescription className="flex items-center justify-between text-xs"><span>{actionError}</span><Button variant="ghost" size="icon" className="h-4 w-4 shrink-0" onClick={()=>setActionError(null)}><X className="h-3 w-3"/></Button></AlertDescription></Alert>)}
{/*Unsorted (non-project) assets section*/}
<div className="mb-2"><div onClick={handleUnsortedClick} className={`flex items-center gap-1.5 py-2 px-1.5 rounded-lg cursor-pointer group transition-all overflow-hidden ${isUnsortedTabOpen()?'bg-sidebar-accent text-foreground shadow-sm':'hover:bg-muted/50 text-muted-foreground hover:text-foreground'}`} title="Open unsorted assets tab">
<Inbox className={`h-3.5 w-3.5 shrink-0 ${isUnsortedTabOpen()?'text-foreground':'text-muted-foreground/70 group-hover:text-foreground'}`}/>
<div className="flex-1 min-w-0 overflow-hidden">
<div className="flex items-center gap-1"><span className={`text-sm truncate italic ${isUnsortedTabOpen()?'font-medium text-foreground':'font-medium text-foreground/90'}`}>Unsorted</span></div>
<span className={`text-[10px] truncate block ${isUnsortedTabOpen()?'text-muted-foreground':'text-muted-foreground/60'}`}>{generalCount} asset{generalCount!==1?'s':''}</span>
</div></div></div>
{sortedProjects.length===0?(<p className="text-sm text-muted-foreground italic">{isLoading?'Loading...':'No projects yet. Click + to create a campaign.'}</p>):(<div className="space-y-1">{sortedProjects.map((project)=>(<ProjectRow key={project.slug} project={project} isTabOpen={isProjectTabOpen(project.slug)} onClick={()=>handleProjectClick(project.slug,project.name)}/>))}</div>)}
</div>)}
