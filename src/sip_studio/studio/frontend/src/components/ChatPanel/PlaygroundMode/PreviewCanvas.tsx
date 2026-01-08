//Preview canvas for Playground mode - shows aspect-ratio placeholder or generated image
import{ImageIcon}from'lucide-react'
import{type AspectRatio,ASPECT_RATIOS}from'@/types/aspectRatio'
import{cn}from'@/lib/utils'
interface Props{aspectRatio:AspectRatio,isLoading:boolean,result:{path:string;data?:string}|null,onStop?:()=>void}
export function PreviewCanvas({aspectRatio,isLoading,result,onStop}:Props){
const d=ASPECT_RATIOS[aspectRatio]||{w:1,h:1}
const imgSrc=result?.data||null
//Calculate dimensions based on aspect ratio - constrain by height for portrait, width for landscape
const isPortrait=d.h>d.w
const maxH=420,maxW=380
const w=isPortrait?Math.round(maxH*(d.w/d.h)):maxW
const h=isPortrait?maxH:Math.round(maxW*(d.h/d.w))
return(
<div className="flex-1 flex items-center justify-center p-4">
<div className="relative rounded-2xl overflow-hidden transition-all duration-300 ease-out" style={{width:w,height:h}}>
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
</div>
</div>)}
