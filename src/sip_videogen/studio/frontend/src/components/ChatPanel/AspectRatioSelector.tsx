//Collapsible aspect ratio selector with orientation-based selection
import{useState,useEffect,useRef}from'react'
import{ChevronDown}from'lucide-react'
import{cn}from'@/lib/utils'
import{DropdownMenu,DropdownMenuTrigger,DropdownMenuContent}from'@/components/ui/dropdown-menu'
import{type AspectRatio,ASPECT_RATIOS,DEFAULT_ASPECT_RATIO,BASE_RATIOS,type BaseRatio,type Orientation,getActualRatio,parseRatioOrientation}from'@/types/aspectRatio'
interface Props{value?:AspectRatio,onChange:(r:AspectRatio)=>void,disabled?:boolean}
type Mode='square'|'landscape'|'portrait'
//Visual rectangle representing aspect ratio
function RatioIcon({ratio,size=16}:{ratio:AspectRatio,size?:number}){
const{w,h}=ASPECT_RATIOS[ratio]
const scale=size/Math.max(w,h)
const width=Math.round(w*scale),height=Math.round(h*scale)
return(<div className="flex items-center justify-center" style={{width:`${size}px`,height:`${size}px`}}><div className="rounded-[2px] border-[1.5px] border-current" style={{width:`${width}px`,height:`${height}px`}}/></div>)}
//Mode toggle (Square / Landscape / Portrait)
function ModeToggle({v,onChange,disabled}:{v:Mode,onChange:(m:Mode)=>void,disabled:boolean}){
const modes:[Mode,string][]=[['square','Square'],['landscape','Landscape'],['portrait','Portrait']]
return(<div className="flex gap-1 p-1 bg-muted/50 rounded-lg">{modes.map(([m,label])=>{
const sel=v===m
return(<button key={m} type="button" disabled={disabled} onClick={()=>onChange(m)} className={cn("flex-1 px-4 py-2 text-xs font-medium rounded-md transition-all",sel?"bg-background text-foreground shadow-sm":"text-muted-foreground hover:text-foreground",disabled&&"opacity-50 cursor-not-allowed")}>{label}</button>)})}</div>)}
//Base ratio grid (only shown for landscape/portrait)
function RatioGrid({orientation,selected,onSelect,disabled}:{orientation:Orientation,selected:BaseRatio|null,onSelect:(r:BaseRatio)=>void,disabled:boolean}){
const labels:Record<BaseRatio,string>={'16:9':'16:9','5:3':'5:3','4:3':'4:3','3:2':'3:2'}
return(<div className="grid grid-cols-4 gap-2 p-2">{BASE_RATIOS.map(base=>{
const actual=getActualRatio(base,orientation)
const sel=selected===base
return(<button key={base} type="button" disabled={disabled} onClick={()=>onSelect(base)} className={cn("flex flex-col items-center gap-1.5 p-3 rounded-lg transition-all",sel?"bg-foreground/10 text-foreground":"text-muted-foreground hover:bg-foreground/5 hover:text-foreground",disabled&&"opacity-50 cursor-not-allowed")}><RatioIcon ratio={actual} size={18}/><span className="text-[11px] font-medium">{labels[base]}</span></button>)})}</div>)}
//Animated container for smooth height transitions
function AnimatedContent({show,children}:{show:boolean,children:React.ReactNode}){
const ref=useRef<HTMLDivElement>(null)
const[height,setHeight]=useState(0)
useEffect(()=>{if(ref.current)setHeight(show?ref.current.scrollHeight:0)},[show])
return(<div className="overflow-hidden transition-all duration-200 ease-out" style={{height:`${height}px`,opacity:show?1:0}}><div ref={ref}>{children}</div></div>)}
export function AspectRatioSelector({value=DEFAULT_ASPECT_RATIO,onChange,disabled=false}:Props){
const[open,setOpen]=useState(false)
//Derive mode from current value
const parsed=parseRatioOrientation(value)
const initialMode:Mode=value==='1:1'?'square':(parsed?.orientation||'landscape')
const[mode,setMode]=useState<Mode>(initialMode)
const currentBase=parsed?.base||null
//Sync mode when value changes externally
useEffect(()=>{
if(value==='1:1')setMode('square')
else{const p=parseRatioOrientation(value);if(p)setMode(p.orientation)}},[value])
const handleModeChange=(m:Mode)=>{
setMode(m)
if(m==='square'){onChange('1:1');setOpen(false)}}
const handleBaseSelect=(base:BaseRatio)=>{
if(mode==='square')return
onChange(getActualRatio(base,mode as Orientation))
setOpen(false)}
return(
<DropdownMenu open={open} onOpenChange={setOpen}>
<DropdownMenuTrigger asChild>
<button type="button" disabled={disabled} className={cn("flex items-center gap-2 px-2 py-1 rounded-md text-sm transition-colors","hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",disabled&&"opacity-50 cursor-not-allowed")}>
<RatioIcon ratio={value} size={14}/>
<span className="text-xs font-medium text-muted-foreground">{value}</span>
<ChevronDown className="h-3 w-3 opacity-50"/>
</button>
</DropdownMenuTrigger>
<DropdownMenuContent align="start" side="top" sideOffset={8} className="w-72 p-3">
<ModeToggle v={mode} onChange={handleModeChange} disabled={disabled}/>
<AnimatedContent show={mode!=='square'}>
<div className="pt-3 mt-3 border-t border-border/50">
<p className="text-xs text-muted-foreground px-1 mb-2">Select ratio</p>
<RatioGrid orientation={mode as Orientation} selected={currentBase} onSelect={handleBaseSelect} disabled={disabled}/>
</div>
</AnimatedContent>
</DropdownMenuContent>
</DropdownMenu>)}
