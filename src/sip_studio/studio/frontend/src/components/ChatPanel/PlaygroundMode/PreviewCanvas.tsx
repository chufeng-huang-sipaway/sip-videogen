//Preview canvas for Playground mode - shows aspect-ratio placeholder or generated image
import{Mountain,Loader2}from'lucide-react'
import{type AspectRatio,ASPECT_RATIOS}from'@/types/aspectRatio'
interface Props{aspectRatio:AspectRatio,isLoading:boolean,result:{path:string;data?:string}|null}
export function PreviewCanvas({aspectRatio,isLoading,result}:Props){
const d=ASPECT_RATIOS[aspectRatio]||{w:1,h:1}
//Use data URL directly (bridge.quickGenerate returns base64 data URL in .data field)
const imgSrc=result?.data||null
return(
<div className="relative w-full max-w-md flex items-center justify-center p-4">
<div className="relative w-full bg-blue-50 dark:bg-blue-900/20 rounded-xl overflow-hidden border-2 border-dashed border-blue-200 dark:border-blue-800" style={{aspectRatio:`${d.w}/${d.h}`,maxHeight:'400px'}}>
{imgSrc?(<img src={imgSrc} className="w-full h-full object-cover" alt="Generated"/>):(
<div className="absolute inset-0 flex items-center justify-center">
<Mountain className="w-16 h-16 text-blue-300 dark:text-blue-700"/>
</div>)}
{isLoading&&(<div className="absolute inset-0 bg-white/50 dark:bg-black/50 flex items-center justify-center">
<Loader2 className="w-8 h-8 animate-spin text-blue-500"/>
</div>)}
<div className="absolute top-2 right-2 text-xs text-muted-foreground bg-background/80 px-2 py-0.5 rounded">Image · {aspectRatio}</div>
</div>
</div>)}
