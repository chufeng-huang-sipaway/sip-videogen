import{useState}from'react'
import{Images}from'lucide-react'
import{ImageViewer}from'@/components/ui/image-viewer'
import{useWorkstation}from'@/context/WorkstationContext'
import type{GeneratedImage}from'@/lib/bridge'
interface ChatImageGalleryProps{images:GeneratedImage[]|string[]}
export function ChatImageGallery({images}:ChatImageGalleryProps){
const[previewSrc,setPreviewSrc]=useState<string|null>(null)
const{currentBatch,setSelectedIndex}=useWorkstation()
if(images.length===0)return null
//Normalize to GeneratedImage format for backward compatibility
const norm:GeneratedImage[]=images.map(img=>typeof img==='string'?{url:img}:img)
//Focus image in workstation navigation (find by path in existing batch)
const focusInWorkstation=(index:number)=>{
const img=norm[index];const targetPath=img.path||img.url
const foundIdx=currentBatch.findIndex(b=>b.path===targetPath||b.originalPath===targetPath||b.path?.endsWith(targetPath.split('/').pop()||'')||b.originalPath?.endsWith(targetPath.split('/').pop()||''))
if(foundIdx>=0)setSelectedIndex(foundIdx)}
//Show compact summary with tiny thumbnails
const maxThumbs=4
const shown=norm.slice(0,maxThumbs)
const extra=norm.length-maxThumbs
return(<>
<div className="mt-2 flex items-center gap-1.5">
<div className="flex items-center gap-1 text-xs text-muted-foreground"><Images className="h-3.5 w-3.5"/><span>Generated {norm.length} image{norm.length>1?'s':''}</span></div>
</div>
<div className="mt-1.5 flex flex-wrap gap-1">
{shown.map((img,i)=>(<button key={i} onClick={()=>focusInWorkstation(i)} className="w-12 h-12 rounded border border-border/60 overflow-hidden hover:ring-2 hover:ring-primary/50 transition-all" title="Focus in navigation"><img src={img.url} alt="" className="w-full h-full object-cover"/></button>))}
{extra>0&&(<button onClick={()=>focusInWorkstation(maxThumbs)} className="w-12 h-12 rounded border border-border/60 bg-muted flex items-center justify-center text-xs text-muted-foreground hover:bg-muted/80 transition-colors">+{extra}</button>)}
</div>
<ImageViewer src={previewSrc} onClose={()=>setPreviewSrc(null)}/>
</>)}
