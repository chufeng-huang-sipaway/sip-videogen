//Refactored aspect ratio selector with mode-aware UI
import{ChevronDown,Check}from'lucide-react'
import{cn}from'@/lib/utils'
import{DropdownMenu,DropdownMenuTrigger,DropdownMenuContent,DropdownMenuItem}from'@/components/ui/dropdown-menu'
import{type AspectRatio,ASPECT_RATIOS,DEFAULT_ASPECT_RATIO,type GenerationMode,getVideoSupportedRatios}from'@/types/aspectRatio'
interface Props{value?:AspectRatio,onChange:(r:AspectRatio)=>void,disabled?:boolean,generationMode?:GenerationMode}
//Visual rectangle representing aspect ratio
function RatioIcon({ratio,size=16,className}:{ratio:AspectRatio,size?:number,className?:string}){
const{w,h}=ASPECT_RATIOS[ratio]
const scale=size/Math.max(w,h)
const width=Math.round(w*scale),height=Math.round(h*scale)
return(<div className={cn("flex items-center justify-center",className)} style={{width:`${size}px`,height:`${size}px`}}><div className="rounded-[2px] border-[1.5px] border-current" style={{width:`${width}px`,height:`${height}px`}}/></div>)}
//Compact toggle for video mode (icon + ratio, no text labels)
function VideoRatioToggle({value,onChange,disabled}:{value:AspectRatio,onChange:(r:AspectRatio)=>void,disabled:boolean}){
const opts:AspectRatio[]=['16:9','9:16']
return(<div className={cn("inline-flex items-center gap-0.5 p-0.5 rounded-full bg-white/50 dark:bg-white/10 border border-border/40",disabled&&"opacity-50 pointer-events-none")}>
{opts.map(r=>{
const sel=value===r
return(<button key={r} type="button" onClick={()=>onChange(r)} disabled={disabled} title={r==='16:9'?'Landscape':'Portrait'} className={cn("flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium transition-all",sel?"bg-white dark:bg-white/20 shadow-sm text-foreground":"text-muted-foreground hover:text-foreground")}>
<RatioIcon ratio={r} size={14}/>
<span>{r}</span>
</button>)})}</div>)}
//Dropdown for image mode (all ratios with platform hints)
function ImageRatioDropdown({value,onChange,disabled,allowedRatios}:{value:AspectRatio,onChange:(r:AspectRatio)=>void,disabled:boolean,allowedRatios?:AspectRatio[]}){
const ratios:AspectRatio[]=allowedRatios||(['16:9','4:3','3:2','5:3','1:1','9:16','3:4','2:3','3:5'] as AspectRatio[])
return(
<DropdownMenu>
<DropdownMenuTrigger asChild>
<button type="button" disabled={disabled} className={cn("flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium transition-all","bg-white/50 dark:bg-white/10 border border-border/40","hover:bg-white dark:hover:bg-white/20",disabled&&"opacity-50 cursor-not-allowed")}>
<RatioIcon ratio={value} size={12}/>
<span>{value}</span>
<ChevronDown className="h-3 w-3 opacity-50"/>
</button>
</DropdownMenuTrigger>
<DropdownMenuContent align="start" side="top" sideOffset={8} className="w-56 p-1.5">
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
//Main component - renders VideoRatioToggle or ImageRatioDropdown based on mode
export function AspectRatioSelector({value=DEFAULT_ASPECT_RATIO,onChange,disabled=false,generationMode='image'}:Props){
const isVideo=generationMode==='video'
if(isVideo){
const videoRatios=getVideoSupportedRatios()
//Ensure value is valid for video mode
const validValue=videoRatios.includes(value)?value:videoRatios[0]
return<VideoRatioToggle value={validValue} onChange={onChange} disabled={disabled}/>}
return<ImageRatioDropdown value={value} onChange={onChange} disabled={disabled}/>}
