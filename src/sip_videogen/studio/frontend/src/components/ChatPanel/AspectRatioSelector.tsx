//iPhone-style aspect ratio selector for video generation
import{cn}from'@/lib/utils'
import{type AspectRatio,ASPECT_RATIOS,DEFAULT_ASPECT_RATIO}from'@/types/aspectRatio'
interface AspectRatioSelectorProps{
value?:AspectRatio
onChange:(ratio:AspectRatio)=>void
disabled?:boolean}
const RATIO_ORDER:AspectRatio[]=['1:1','16:9','9:16','4:3','3:4']
//Visual rectangle representing aspect ratio
function RatioIcon({ratio,selected}:{ratio:AspectRatio,selected:boolean}){
const{w,h}=ASPECT_RATIOS[ratio]
//Normalize to max dimension of 16px
const maxDim=16,scale=maxDim/Math.max(w,h)
const width=Math.round(w*scale),height=Math.round(h*scale)
return(<div className={cn("flex items-center justify-center w-7 h-7 rounded transition-all",selected?"bg-foreground/10 ring-1 ring-foreground/20":"hover:bg-foreground/5")}><div className={cn("rounded-[2px] border-[1.5px] transition-colors",selected?"border-foreground":"border-foreground/40")}style={{width:`${width}px`,height:`${height}px`}}/></div>)}
export function AspectRatioSelector({value=DEFAULT_ASPECT_RATIO,onChange,disabled=false}:AspectRatioSelectorProps){
const handleKeyDown=(e:React.KeyboardEvent,idx:number)=>{
if(disabled)return
let nextIdx=-1
if(e.key==='ArrowRight'||e.key==='ArrowDown')nextIdx=(idx+1)%RATIO_ORDER.length
else if(e.key==='ArrowLeft'||e.key==='ArrowUp')nextIdx=(idx-1+RATIO_ORDER.length)%RATIO_ORDER.length
if(nextIdx>=0){e.preventDefault();onChange(RATIO_ORDER[nextIdx])}}
return(<div role="radiogroup" aria-label="Video aspect ratio" className="flex items-center gap-1 px-2 py-1">{RATIO_ORDER.map((r,idx)=>{
const{label,w,h}=ASPECT_RATIOS[r],selected=r===value
return(<button key={r} type="button" role="radio" aria-checked={selected} aria-label={`${label} ${w} to ${h}`} tabIndex={selected?0:-1} disabled={disabled} onClick={()=>onChange(r)} onKeyDown={e=>handleKeyDown(e,idx)} className={cn("outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 rounded transition-opacity",disabled&&"opacity-50 cursor-not-allowed")}><RatioIcon ratio={r} selected={selected}/></button>)})}</div>)}
