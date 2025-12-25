import{useState,useEffect,useCallback}from'react'
import{Image,Loader2,RotateCcw}from'lucide-react'
import{ContextMenu,ContextMenuContent,ContextMenuItem,ContextMenuTrigger}from'@/components/ui/context-menu'
import{useBrand}from'@/context/BrandContext'
import{useWorkstation}from'@/context/WorkstationContext'
import{bridge,isPyWebView,type ImageStatusEntry}from'@/lib/bridge'
//Thumbnail component for kept images
function KeptThumbnail({path,onClick}:{path:string;onClick:()=>void}){
const[src,setSrc]=useState<string|null>(null)
const[loading,setLoading]=useState(true)
useEffect(()=>{let cancelled=false
async function load(){if(!path){if(!cancelled)setLoading(false);return}
if(path.startsWith('data:')){if(!cancelled){setSrc(path);setLoading(false)};return}
const normalized=path.startsWith('file://')?path.slice('file://'.length):path
if(!isPyWebView()){if(!cancelled){if(normalized.startsWith('/'))setSrc(`file://${normalized}`);setLoading(false)};return}
try{
  if(normalized.startsWith('/')){
    const dataUrl=await bridge.getImageThumbnail(normalized)
    if(!cancelled)setSrc(dataUrl)
  }else{
    try{
      const dataUrl=await bridge.getAssetThumbnail(normalized)
      if(!cancelled)setSrc(dataUrl)
    }catch{
      const dataUrl=await bridge.getImageThumbnail(normalized)
      if(!cancelled)setSrc(dataUrl)
    }
  }
}catch{}finally{if(!cancelled)setLoading(false)}}
load();return()=>{cancelled=true}},[path])
if(loading)return(<div className="h-12 w-12 rounded bg-muted flex items-center justify-center shrink-0"><Loader2 className="h-4 w-4 text-muted-foreground animate-spin"/></div>)
if(!src)return(<div className="h-12 w-12 rounded bg-muted flex items-center justify-center shrink-0"><Image className="h-4 w-4 text-muted-foreground"/></div>)
return<img src={src} alt="" className="h-12 w-12 rounded object-cover shrink-0 cursor-pointer hover:ring-2 hover:ring-primary transition-all" onClick={onClick}/>}
//Individual kept image card
interface KeptImageCardProps{image:ImageStatusEntry;onView:()=>void;onUnkeep:()=>void}
function KeptImageCard({image,onView,onUnkeep}:KeptImageCardProps){
return(<ContextMenu><ContextMenuTrigger asChild><div className="relative"><KeptThumbnail path={image.currentPath} onClick={onView}/></div></ContextMenuTrigger><ContextMenuContent><ContextMenuItem onClick={onView}>View in Workstation</ContextMenuItem><ContextMenuItem onClick={onUnkeep}><RotateCcw className="h-4 w-4 mr-2"/>Return to Unsorted</ContextMenuItem></ContextMenuContent></ContextMenu>)}
//Main KeptSection component
export function KeptSection(){
const{activeBrand}=useBrand()
const{setCurrentBatch,setSelectedIndex,setIsTrashView,statusVersion,bumpStatusVersion}=useWorkstation()
const[keptImages,setKeptImages]=useState<ImageStatusEntry[]>([])
const[isLoading,setIsLoading]=useState(false)
const[error,setError]=useState<string|null>(null)
//Load kept images
const loadKeptImages=useCallback(async()=>{if(!activeBrand||!isPyWebView())return
setIsLoading(true);setError(null)
try{const images=await bridge.getImagesByStatus(activeBrand,'kept');setKeptImages(images)}catch(err){setError(err instanceof Error?err.message:'Failed to load kept images')}finally{setIsLoading(false)}},[activeBrand])
//Load on mount, brand change, and status updates
useEffect(()=>{loadKeptImages()},[loadKeptImages,statusVersion])
//Handle viewing image in workstation
const handleView=(image:ImageStatusEntry)=>{
const img={id:image.id,path:image.currentPath,prompt:image.prompt||undefined,sourceTemplatePath:image.sourceTemplatePath||undefined,timestamp:image.timestamp}
setIsTrashView(false)
setCurrentBatch([img]);setSelectedIndex(0)}
//Handle unkeep action
const handleUnkeep=async(imageId:string)=>{if(!isPyWebView())return
try{await bridge.unkeepImage(imageId);setKeptImages(prev=>prev.filter(img=>img.id!==imageId));bumpStatusVersion()}catch(err){console.error('Failed to unkeep image:',err)}}
if(!activeBrand)return<div className="text-xs text-muted-foreground px-2">Select a brand</div>
if(error)return<div className="text-xs text-destructive px-2">{error}</div>
if(isLoading)return(<div className="flex items-center gap-2 text-xs text-muted-foreground px-2"><Loader2 className="h-3 w-3 animate-spin"/>Loading...</div>)
if(keptImages.length===0)return<div className="text-xs text-muted-foreground italic px-2">No kept images yet</div>
return(<div className="space-y-2 px-2"><div className="text-xs text-muted-foreground">{keptImages.length} kept image{keptImages.length!==1?'s':''}</div><div className="flex flex-wrap gap-2">{keptImages.map(image=>(<KeptImageCard key={image.id} image={image} onView={()=>handleView(image)} onUnkeep={()=>handleUnkeep(image.id)}/>))}</div></div>)}
