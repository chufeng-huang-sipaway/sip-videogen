//ThumbnailStrip component - horizontal thumbnail navigation with lazy loading
import{useState,useEffect,useRef}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import type{GeneratedImage}from'../../context/WorkstationContext'
import{useDrag}from'../../context/DragContext'
import{useQuickEdit}from'../../context/QuickEditContext'
import{bridge,isPyWebView}from'../../lib/bridge'
import{cn}from'../../lib/utils'
import{Loader2,Play}from'lucide-react'
import{getThumbCached,setThumbCached,hasThumbCached,loadWithConcurrency}from'../../lib/thumbnailCache'
import{getMediaType}from'../../lib/mediaUtils'
function Thumb({media}:{media:GeneratedImage}){
const isVideo=getMediaType(media)==='video'
const path=media.originalPath||media.path||''
const isUnread=media.viewedAt===null
const[src,setSrc]=useState<string|null>(()=>getThumbCached(path)??null)
const[loading,setLoading]=useState(!hasThumbCached(path))
const containerRef=useRef<HTMLDivElement>(null)
const loadedRef=useRef(false)
const mountedRef=useRef(true)
useEffect(()=>{mountedRef.current=true;return()=>{mountedRef.current=false}},[])
//IntersectionObserver for lazy loading - videos use conceptImagePath or gradient placeholder
const thumbPath=isVideo?(media.conceptImagePath||''):path
useEffect(()=>{
if(!thumbPath){setLoading(false);return}
if(hasThumbCached(thumbPath)){setSrc(getThumbCached(thumbPath)!);setLoading(false);return}
if(thumbPath.startsWith('data:')){setSrc(thumbPath);setLoading(false);return}
if(!isPyWebView()){setLoading(false);return}
const container=containerRef.current;if(!container)return
const observer=new IntersectionObserver((entries)=>{
if(entries[0]?.isIntersecting&&!loadedRef.current){
loadedRef.current=true;observer.disconnect()
//Concurrency-limited load
void loadWithConcurrency(async()=>{
try{
const dataUrl=await bridge.getAssetThumbnail(thumbPath)
if(!mountedRef.current)return
setThumbCached(thumbPath,dataUrl);setSrc(dataUrl)
}catch(e){console.error('Thumb load error:',e)}
finally{if(mountedRef.current)setLoading(false)}
})
}},{rootMargin:'100px'})
observer.observe(container);return()=>observer.disconnect()
},[thumbPath])
return(<div ref={containerRef} className="w-full h-full flex items-center justify-center bg-muted/20 relative">{loading?(<Loader2 className="w-3 h-3 animate-spin text-muted-foreground/30"/>):src?(<img src={src} alt="" className="w-full h-full object-cover"/>):isVideo?(<div className="w-full h-full bg-gradient-to-br from-brand-500/20 to-brand-500/10"/>):null}{isVideo&&(<div className="absolute inset-0 flex items-center justify-center bg-black/20"><Play className="w-4 h-4 text-white drop-shadow-md"/></div>)}{isUnread&&<div className="absolute top-0.5 right-0.5 w-2.5 h-2.5 bg-brand-500 rounded-full border-2 border-background shadow-sm"/>}</div>)
}
export function ThumbnailStrip(){
const{currentBatch,selectedIndex,setSelectedIndex}=useWorkstation()
const{setDragData,clearDrag}=useDrag()
const{isGenerating}=useQuickEdit()
const btnRefs=useRef<(HTMLButtonElement|null)[]>([])
//Auto-center selected thumbnail (also triggers when batch changes to handle prepend)
//Use requestAnimationFrame to ensure refs are populated after render
useEffect(()=>{requestAnimationFrame(()=>{const btn=btnRefs.current[selectedIndex];if(btn)btn.scrollIntoView({behavior:'smooth',inline:'center',block:'nearest'})})},[selectedIndex,currentBatch.length,currentBatch[0]?.id])
const handleDragStart=(e:React.DragEvent,path:string)=>{if(!path||path.startsWith('data:'))return;
//Create drag image from thumbnail
const btn=e.currentTarget as HTMLElement;const img=btn.querySelector('img');if(img&&img.naturalWidth>0){const size=80,canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');if(ctx){const scale=Math.min(size/img.naturalWidth,size/img.naturalHeight);canvas.width=img.naturalWidth*scale;canvas.height=img.naturalHeight*scale;ctx.drawImage(img,0,0,canvas.width,canvas.height);e.dataTransfer.setDragImage(canvas,canvas.width/2,canvas.height/2)}}
e.dataTransfer.setData('text/plain',path);try{e.dataTransfer.setData('text/uri-list',path)}catch{/*ignore*/}try{e.dataTransfer.setData('application/x-brand-asset',path)}catch{/*ignore*/}e.dataTransfer.effectAllowed='copy';setDragData({type:'asset',path})}
const handleDragEnd=()=>clearDrag()
if(currentBatch.length<=1)return null
return(
<div className="flex-shrink-0 w-full">
<div className="flex gap-1.5 overflow-x-auto scrollbar-thin scrollbar-thumb-muted-foreground/20 scrollbar-track-transparent justify-center px-1 py-0.5">
{currentBatch.map((img,i)=>{const imgPath=img.originalPath||img.path||'';const canDrag=!!imgPath&&!imgPath.startsWith('data:')&&!isGenerating;return(
<button key={img.id} ref={el=>{btnRefs.current[i]=el}} draggable={canDrag} onDragStart={(e)=>handleDragStart(e,imgPath)} onDragEnd={handleDragEnd} onClick={()=>!isGenerating&&setSelectedIndex(i)} disabled={isGenerating} className={cn("flex-shrink-0 w-12 h-12 rounded-lg overflow-hidden border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/50 relative",isGenerating?"cursor-not-allowed opacity-50":"cursor-grab active:cursor-grabbing",i===selectedIndex?"border-primary shadow-md ring-2 ring-primary/20 scale-105 z-10":"border-transparent opacity-70 hover:opacity-100 hover:scale-105")}>
<Thumb media={img}/>
</button>)})}
</div>
</div>)
}
