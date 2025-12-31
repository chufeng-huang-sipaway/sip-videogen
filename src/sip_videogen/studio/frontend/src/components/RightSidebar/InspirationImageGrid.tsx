import{useState,useCallback}from'react'
import{Loader2,AlertCircle,Download}from'lucide-react'
import{bridge,type InspirationImage}from'@/lib/bridge'
import{cn}from'@/lib/utils'
interface InspirationImageGridProps{images:InspirationImage[];inspirationId:string;onSaveImage:(idx:number)=>void}
//Single image cell in the grid
function ImageCell({img,idx,onSave,onLoad}:{img:InspirationImage;idx:number;onSave:(idx:number)=>void;onLoad:(idx:number,url:string)=>void}){
const[thumbUrl,setThumbUrl]=useState<string|null>(null)
const[loading,setLoading]=useState(false)
const[error,setError]=useState(false)
const[hovered,setHovered]=useState(false)
//Load thumbnail on mount or when path changes
const loadThumbnail=useCallback(async()=>{
if(!img.thumbnailPath||img.status!=='ready')return
if(thumbUrl)return
setLoading(true);setError(false)
try{const url=await bridge.getAssetThumbnail(img.thumbnailPath);setThumbUrl(url);onLoad(idx,url)}
catch{setError(true)}
finally{setLoading(false)}
},[img.thumbnailPath,img.status,thumbUrl,idx,onLoad])
//Load on first render
useState(()=>{loadThumbnail()})
if(img.status==='generating'){
return(<div className="aspect-square bg-muted rounded-lg flex items-center justify-center animate-pulse"><Loader2 className="w-5 h-5 text-muted-foreground animate-spin"/></div>)}
if(img.status==='failed'||error){
return(<div className="aspect-square bg-muted rounded-lg flex flex-col items-center justify-center gap-1"><AlertCircle className="w-5 h-5 text-destructive/60"/><span className="text-[10px] text-muted-foreground">Failed</span></div>)}
return(
<div className={cn("aspect-square rounded-lg overflow-hidden relative cursor-pointer group",hovered&&"ring-2 ring-primary")} onMouseEnter={()=>setHovered(true)} onMouseLeave={()=>setHovered(false)} onClick={()=>onSave(idx)}>
{loading||!thumbUrl?(<div className="w-full h-full bg-muted animate-pulse"/>):(
<img src={thumbUrl} alt={`Variation ${idx+1}`} className="w-full h-full object-cover transition-transform group-hover:scale-105"/>)}
{/* Save overlay on hover */}
<div className={cn("absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 transition-opacity",hovered&&"opacity-100")}>
<Download className="w-5 h-5 text-white"/>
</div>
</div>)
}
export function InspirationImageGrid({images,inspirationId,onSaveImage}:InspirationImageGridProps){
const[,setLoadedUrls]=useState<Record<number,string>>({})
const handleLoad=useCallback((idx:number,url:string)=>{setLoadedUrls(prev=>({...prev,[idx]:url}))},[])
//Ensure we have 3 images (pad with placeholder if needed)
const displayImages=images.length>=3?images:images.concat(Array(3-images.length).fill({path:null,thumbnailPath:null,prompt:'',generatedAt:'',status:'generating'as const}))
return(
<div className="grid grid-cols-3 gap-2">
{displayImages.slice(0,3).map((img,idx)=>(
<ImageCell key={`${inspirationId}-${idx}`} img={img} idx={idx} onSave={onSaveImage} onLoad={handleLoad}/>
))}
</div>)
}
