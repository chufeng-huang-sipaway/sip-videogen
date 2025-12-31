import{useState}from'react'
import{ChevronDown,Sparkles,X,Instagram,Globe,Mail,LayoutGrid}from'lucide-react'
import{Button}from'@/components/ui/button'
import{DropdownMenu,DropdownMenuTrigger,DropdownMenuContent,DropdownMenuItem,DropdownMenuSeparator}from'@/components/ui/dropdown-menu'
import{InspirationImageGrid}from'./InspirationImageGrid'
import type{Inspiration}from'@/lib/bridge'
import{cn}from'@/lib/utils'
interface InspirationCardProps{
inspiration:Inspiration
activeProject:string|null
projects:{slug:string;name:string}[]
onSaveImage:(inspirationId:string,imageIdx:number,projectSlug?:string|null)=>Promise<void>
onMoreLikeThis:(inspirationId:string)=>Promise<void>
onDismiss:(inspirationId:string)=>Promise<void>
}
//Channel badge icon and label mapping
const channelConfig:{[key:string]:{icon:React.ElementType;label:string;color:string}}={
instagram:{icon:Instagram,label:'Instagram',color:'bg-pink-500/10 text-pink-600 dark:text-pink-400'},
website:{icon:Globe,label:'Website',color:'bg-blue-500/10 text-blue-600 dark:text-blue-400'},
email:{icon:Mail,label:'Email',color:'bg-amber-500/10 text-amber-600 dark:text-amber-400'},
general:{icon:LayoutGrid,label:'General',color:'bg-slate-500/10 text-slate-600 dark:text-slate-400'}
}
export function InspirationCard({inspiration,activeProject,projects,onSaveImage,onMoreLikeThis,onDismiss}:InspirationCardProps){
const[expanded,setExpanded]=useState(false)
const[saving,setSaving]=useState(false)
const[dismissing,setDismissing]=useState(false)
const ch=channelConfig[inspiration.targetChannel]||channelConfig.general
const ChannelIcon=ch.icon
const handleSaveImage=async(idx:number,projectSlug?:string|null)=>{
setSaving(true)
try{await onSaveImage(inspiration.id,idx,projectSlug)}finally{setSaving(false)}
}
const handleMoreLike=async()=>{try{await onMoreLikeThis(inspiration.id)}catch{}}
const handleDismiss=async()=>{
setDismissing(true)
try{await onDismiss(inspiration.id)}finally{setDismissing(false)}
}
const isGenerating=inspiration.status==='generating'
return(
<div className={cn("bg-white/50 dark:bg-white/5 rounded-xl p-4 space-y-3 transition-opacity",dismissing&&"opacity-50",isGenerating&&"animate-pulse")}>
{/* Header: Title + Channel badge */}
<div className="flex items-start justify-between gap-2">
<h4 className="text-sm font-medium text-foreground line-clamp-2 flex-1">{inspiration.title}</h4>
<span className={cn("flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium shrink-0",ch.color)}>
<ChannelIcon className="w-3 h-3"/>
{ch.label}
</span>
</div>
{/* Rationale - expandable */}
<p className={cn("text-xs text-muted-foreground",expanded?"":"line-clamp-2")} onClick={()=>setExpanded(!expanded)}>
{inspiration.rationale}
</p>
{/* Image grid */}
<InspirationImageGrid images={inspiration.images} inspirationId={inspiration.id} onSaveImage={(idx)=>handleSaveImage(idx,activeProject)}/>
{/* Action row */}
<div className="flex items-center gap-2 pt-1">
{/* Save dropdown */}
<DropdownMenu>
<DropdownMenuTrigger asChild>
<Button variant="outline" size="sm" className="h-7 text-xs gap-1 flex-1" disabled={saving||isGenerating}>
Save<ChevronDown className="w-3 h-3"/>
</Button>
</DropdownMenuTrigger>
<DropdownMenuContent align="start" className="w-48">
{activeProject&&(
<DropdownMenuItem onClick={()=>handleSaveImage(0,activeProject)}>
Save to {projects.find(p=>p.slug===activeProject)?.name||activeProject}
</DropdownMenuItem>
)}
<DropdownMenuItem onClick={()=>handleSaveImage(0,null)}>
Save to General
</DropdownMenuItem>
{projects.length>0&&activeProject&&(<DropdownMenuSeparator/>)}
{projects.filter(p=>p.slug!==activeProject).slice(0,5).map(p=>(
<DropdownMenuItem key={p.slug} onClick={()=>handleSaveImage(0,p.slug)}>
{p.name}
</DropdownMenuItem>
))}
</DropdownMenuContent>
</DropdownMenu>
{/* More like this */}
<Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={handleMoreLike} disabled={isGenerating}>
<Sparkles className="w-3 h-3"/>
More
</Button>
{/* Dismiss */}
<Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={handleDismiss} disabled={dismissing||isGenerating}>
<X className="w-4 h-4"/>
</Button>
</div>
</div>
)
}
