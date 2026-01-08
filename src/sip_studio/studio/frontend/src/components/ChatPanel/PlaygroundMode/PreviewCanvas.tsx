//Preview canvas for Playground mode - shows aspect-ratio placeholder or generated image
import{useState,useRef,useLayoutEffect,useEffect}from'react'
import{ImageIcon,Check}from'lucide-react'
import{type AspectRatio,ASPECT_RATIOS}from'@/types/aspectRatio'
import{cn}from'@/lib/utils'
interface Props{aspectRatio:AspectRatio,isLoading:boolean,result:{path:string;data?:string}|null,onStop?:()=>void,showSaved?:boolean}
//Safe margins for the preview area
const MARGIN_X=32,MARGIN_Y=48
export function PreviewCanvas({aspectRatio,isLoading,result,onStop,showSaved}:Props){
const containerRef=useRef<HTMLDivElement>(null)
const[dims,setDims]=useState({w:300,h:300})
const[badgeVisible,setBadgeVisible]=useState(false)
const d=ASPECT_RATIOS[aspectRatio]||{w:1,h:1}
const imgSrc=result?.data||null
//Scale to fit: maximize preview within container minus margins
useLayoutEffect(()=>{
const el=containerRef.current;if(!el)return
const calc=()=>{const{width:cw,height:ch}=el.getBoundingClientRect();const availW=cw-MARGIN_X,availH=ch-MARGIN_Y;const scale=Math.min(availW/d.w,availH/d.h);setDims({w:Math.round(d.w*scale),h:Math.round(d.h*scale)})}
calc()
const ro=new ResizeObserver(calc);ro.observe(el)
return()=>ro.disconnect()},[d.w,d.h])
//Badge animation: show then auto-hide after 5s
useEffect(()=>{
if(showSaved){setBadgeVisible(true);const t=setTimeout(()=>setBadgeVisible(false),5000);return()=>clearTimeout(t)}
setBadgeVisible(false)},[showSaved])
return(
<div ref={containerRef} className="flex-1 flex items-center justify-center p-4 w-full h-full">
<div className="relative rounded-2xl overflow-hidden transition-all duration-300 ease-out" style={{width:dims.w,height:dims.h}}>
{imgSrc?(
<img src={imgSrc} className="w-full h-full object-cover" alt="Generated"/>
):(
<div className={cn("absolute inset-0 flex items-center justify-center","bg-neutral-50 dark:bg-neutral-900","border border-dashed border-neutral-300 dark:border-neutral-700 rounded-2xl")}>
<ImageIcon className="w-6 h-6 text-neutral-300 dark:text-neutral-600"/>
</div>
)}
{isLoading&&(<>
<div className="shimmer-overlay rounded-2xl"/>
<div className="shimmer-sparkles rounded-2xl">{Array.from({length:38},(_,i)=><span key={i} className={`sparkle${i%3===1?' brand':''}`}/>)}</div>
<button onClick={onStop} className="magic-stop-btn" style={{pointerEvents:'auto'}}><span className="magic-stop-icon"/></button>
</>)}
{badgeVisible&&(<div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-black/60 backdrop-blur-sm text-white text-xs font-medium animate-in fade-in slide-in-from-bottom-2 duration-300"><Check className="w-3 h-3"/>Saved</div>)}
</div>
</div>)}
