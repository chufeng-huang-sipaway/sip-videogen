//IdeasThumbnailStrip - Thumbnail navigation for inspirations and images within
import{useState,useEffect,useRef}from'react'
import{bridge,isPyWebView,type Inspiration}from'@/lib/bridge'
import{ChevronLeft,ChevronRight}from'lucide-react'
import{cn}from'@/lib/utils'
interface Props{
inspirations:Inspiration[]
currentInspirationId:string|null
currentImageIndex:number
onSelectImage:(idx:number)=>void
onPrevInspiration:()=>void
onNextInspiration:()=>void
canPrevInspiration:boolean
canNextInspiration:boolean
}
interface ThumbCache{[key:string]:string}
export function IdeasThumbnailStrip({inspirations,currentInspirationId,currentImageIndex,onSelectImage,onPrevInspiration,onNextInspiration,canPrevInspiration,canNextInspiration}:Props){
const[thumbCache,setThumbCache]=useState<ThumbCache>({})
const loadingRef=useRef<Set<string>>(new Set())
const current=inspirations.find(i=>i.id===currentInspirationId)
const currentImages=current?.images.filter(img=>img.status==='ready'&&img.path)||[]
//Load thumbnails for current inspiration
useEffect(()=>{
if(!current||!isPyWebView())return
let cancelled=false
const loadThumbs=async()=>{
for(const img of currentImages){
const path=img.thumbnailPath||img.path
if(!path||thumbCache[path]||loadingRef.current.has(path))continue
loadingRef.current.add(path)
try{
const dataUrl=await bridge.getAssetThumbnail(path)
if(cancelled)return
if(dataUrl&&dataUrl!==''){setThumbCache(prev=>({...prev,[path]:dataUrl}))}
}catch{}finally{loadingRef.current.delete(path)}
}
}
loadThumbs()
return()=>{cancelled=true}
},[current?.id,currentImages,thumbCache])
const navBtnClass="flex-shrink-0 p-1.5 rounded-full bg-neutral-800/60 text-white/80 hover:bg-neutral-700/70 hover:text-white transition-all disabled:opacity-30 disabled:pointer-events-none"
const thumbClass="w-12 h-12 rounded-lg object-cover cursor-pointer transition-all hover:scale-105 border-2"
return(<div className="flex items-center gap-2 px-1">
{/* Prev inspiration */}
<button onClick={onPrevInspiration} disabled={!canPrevInspiration} className={navBtnClass}>
<ChevronLeft className="w-4 h-4"/>
</button>
{/* Thumbnail images from current inspiration */}
<div className="flex items-center gap-1.5 overflow-x-auto max-w-[300px] py-1 px-1">
{currentImages.map((img,idx)=>{
const path=img.thumbnailPath||img.path
const src=path?thumbCache[path]:null
const isActive=idx===currentImageIndex
return(<button key={idx} onClick={()=>onSelectImage(idx)} className={cn(thumbClass,isActive?"border-brand-500 ring-2 ring-brand-500/50":"border-transparent hover:border-white/30")}>
{src?(<img src={src} alt="" className="w-full h-full object-cover rounded-md"/>):(
<div className="w-full h-full bg-neutral-700/50 rounded-md animate-pulse"/>
)}
</button>)
})}
</div>
{/* Counter */}
<div className="flex-shrink-0 px-2 text-xs font-mono text-white/60">
{currentImageIndex+1}/{currentImages.length}
</div>
{/* Next inspiration */}
<button onClick={onNextInspiration} disabled={!canNextInspiration} className={navBtnClass}>
<ChevronRight className="w-4 h-4"/>
</button>
</div>)
}
