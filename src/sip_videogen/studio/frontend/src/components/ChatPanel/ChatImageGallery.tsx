import{useState}from'react'
import{Images}from'lucide-react'
import{ImageViewer}from'@/components/ui/image-viewer'
import{useWorkstation}from'@/context/WorkstationContext'
import type{GeneratedImage}from'@/lib/bridge'
interface ChatImageGalleryProps{images:GeneratedImage[]|string[]}
export function ChatImageGallery({images}:ChatImageGalleryProps){
const[previewSrc,setPreviewSrc]=useState<string|null>(null)
const{setCurrentBatch,setSelectedIndex}=useWorkstation()
if(images.length===0)return null
//Normalize to GeneratedImage format for backward compatibility
const norm:GeneratedImage[]=images.map(img=>typeof img==='string'?{url:img}:img)
//Open image in workstation
const openInWorkstation=(index:number)=>{
const batch=norm.map((img,i)=>({id:`chat-${i}`,path:img.url,prompt:img.metadata?.prompt,sourceTemplatePath:img.metadata?.reference_image||undefined,timestamp:new Date().toISOString()}))
setCurrentBatch(batch)
setSelectedIndex(index)}
//Show compact summary with tiny thumbnails
const maxThumbs=4
const shown=norm.slice(0,maxThumbs)
const extra=norm.length-maxThumbs
return(<>
<div className="mt-2 flex items-center gap-1.5">
<div className="flex items-center gap-1 text-xs text-muted-foreground"><Images className="h-3.5 w-3.5"/><span>Generated {norm.length} image{norm.length>1?'s':''}</span></div>
</div>
<div className="mt-1.5 flex flex-wrap gap-1">
{shown.map((img,i)=>(<button key={i} onClick={()=>openInWorkstation(i)} className="w-12 h-12 rounded border border-border/60 overflow-hidden hover:ring-2 hover:ring-primary/50 transition-all" title="View in Workstation"><img src={img.url} alt="" className="w-full h-full object-cover"/></button>))}
{extra>0&&(<button onClick={()=>openInWorkstation(maxThumbs)} className="w-12 h-12 rounded border border-border/60 bg-muted flex items-center justify-center text-xs text-muted-foreground hover:bg-muted/80 transition-colors">+{extra}</button>)}
</div>
<ImageViewer src={previewSrc} onClose={()=>setPreviewSrc(null)}/>
</>)}
