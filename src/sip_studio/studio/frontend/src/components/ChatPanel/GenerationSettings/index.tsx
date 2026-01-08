//Generation settings popup - stores defaults for image and video generation
import{useState}from'react'
import{Image,Video,ChevronDown,Check}from'lucide-react'
import{cn}from'@/lib/utils'
import{Popover,PopoverTrigger,PopoverContent}from'@/components/ui/popover'
import{DropdownMenu,DropdownMenuTrigger,DropdownMenuContent,DropdownMenuItem}from'@/components/ui/dropdown-menu'
import{type AspectRatio,ASPECT_RATIOS,type VideoAspectRatio}from'@/types/aspectRatio'
interface GenerationSettingsProps{imageAspectRatio:AspectRatio;videoAspectRatio:VideoAspectRatio;onImageAspectRatioChange:(r:AspectRatio)=>void;onVideoAspectRatioChange:(r:VideoAspectRatio)=>void;disabled?:boolean}
//Visual rectangle representing aspect ratio
function RatioIcon({ratio,size=16,className}:{ratio:AspectRatio,size?:number,className?:string}){
const{w,h}=ASPECT_RATIOS[ratio]
const scale=size/Math.max(w,h)
const width=Math.round(w*scale),height=Math.round(h*scale)
return(<div className={cn("flex items-center justify-center",className)} style={{width:`${size}px`,height:`${size}px`}}><div className="rounded-[2px] border-[1.5px] border-current" style={{width:`${width}px`,height:`${height}px`}}/></div>)}
//Image aspect ratio dropdown
function ImageRatioSelect({value,onChange}:{value:AspectRatio,onChange:(r:AspectRatio)=>void}){
const ratios:AspectRatio[]=['16:9','4:3','3:2','5:4','1:1','9:16','3:4','2:3','4:5']
return(
<DropdownMenu>
<DropdownMenuTrigger asChild>
<button type="button" className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-sm font-medium bg-secondary/50 hover:bg-secondary border border-border/40 transition-all w-full justify-between">
<div className="flex items-center gap-2">
<RatioIcon ratio={value} size={14}/>
<span>{value}</span>
<span className="text-xs text-muted-foreground">{ASPECT_RATIOS[value].hint}</span>
</div>
<ChevronDown className="h-3.5 w-3.5 opacity-50"/>
</button>
</DropdownMenuTrigger>
<DropdownMenuContent align="start" side="bottom" sideOffset={4} className="w-56 p-1.5">
{ratios.map(r=>{
const{hint}=ASPECT_RATIOS[r]
const sel=value===r
return(<DropdownMenuItem key={r} onClick={()=>onChange(r)} className={cn("flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer",sel&&"bg-accent")}>
<RatioIcon ratio={r} size={16} className="shrink-0"/>
<div className="flex-1 min-w-0">
<div className="flex items-center gap-2">
<span className="text-sm font-medium">{r}</span>
<span className="text-xs text-muted-foreground">{hint}</span>
</div>
</div>
{sel&&<Check className="h-4 w-4 text-foreground shrink-0"/>}
</DropdownMenuItem>)})}</DropdownMenuContent>
</DropdownMenu>)}
//Video aspect ratio toggle
function VideoRatioToggle({value,onChange}:{value:VideoAspectRatio,onChange:(r:VideoAspectRatio)=>void}){
const opts:VideoAspectRatio[]=['16:9','9:16']
return(<div className="inline-flex items-center gap-0.5 p-0.5 rounded-lg bg-secondary/50 border border-border/40 w-full">
{opts.map(r=>{
const sel=value===r
return(<button key={r} type="button" onClick={()=>onChange(r)} className={cn("flex-1 flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-md text-sm font-medium transition-all",sel?"bg-background shadow-sm text-foreground":"text-muted-foreground hover:text-foreground")}>
<RatioIcon ratio={r} size={14}/>
<span>{r}</span>
</button>)})}</div>)}
export function GenerationSettings({imageAspectRatio,videoAspectRatio,onImageAspectRatioChange,onVideoAspectRatioChange,disabled}:GenerationSettingsProps){
const[open,setOpen]=useState(false)
return(
<Popover open={open} onOpenChange={setOpen}>
<PopoverTrigger asChild>
<button type="button" disabled={disabled} className={cn("flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all","bg-white/50 dark:bg-white/10 border border-border/40","hover:bg-white dark:hover:bg-white/20 focus:outline-none",disabled&&"opacity-50 cursor-not-allowed")} title="Generation defaults">
<RatioIcon ratio={imageAspectRatio} size={14}/>
<span className="text-muted-foreground">{imageAspectRatio}</span>
<ChevronDown className="h-3 w-3 opacity-50"/>
</button>
</PopoverTrigger>
<PopoverContent align="end" side="top" sideOffset={8} className="w-72 p-0">
<div className="p-4 space-y-4">
<div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Generation Defaults</div>
{/* Image settings */}
<div className="space-y-2">
<div className="flex items-center gap-2 text-sm font-medium">
<Image className="h-4 w-4 text-muted-foreground"/>
<span>Image</span>
</div>
<ImageRatioSelect value={imageAspectRatio} onChange={onImageAspectRatioChange}/>
</div>
{/* Video settings */}
<div className="space-y-2">
<div className="flex items-center gap-2 text-sm font-medium">
<Video className="h-4 w-4 text-muted-foreground"/>
<span>Video</span>
</div>
<VideoRatioToggle value={videoAspectRatio} onChange={onVideoAspectRatioChange}/>
</div>
</div>
<div className="px-4 py-3 bg-muted/30 border-t border-border/40 text-xs text-muted-foreground">
These defaults apply when the assistant generates content.
</div>
</PopoverContent>
</Popover>)}
