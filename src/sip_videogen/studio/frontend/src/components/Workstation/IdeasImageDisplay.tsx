//IdeasImageDisplay - Large image display with crossfade transitions for inspiration images
import{useState,useEffect,useCallback,useRef}from'react'
import{bridge,isPyWebView,type Inspiration,type InspirationImage}from'@/lib/bridge'
import{Loader2,ChevronLeft,ChevronRight,Instagram,Globe,Mail,LayoutGrid}from'lucide-react'
import{cn}from'@/lib/utils'
interface Props{
inspiration:Inspiration
image:InspirationImage|null
imageIndex:number
totalImages:number
onPrevImage:()=>void
onNextImage:()=>void
canPrev:boolean
canNext:boolean
}
//Channel config
const chCfg:{[k:string]:{icon:React.ElementType;label:string}}={
instagram:{icon:Instagram,label:'Instagram'},
website:{icon:Globe,label:'Website'},
email:{icon:Mail,label:'Email'},
general:{icon:LayoutGrid,label:'General'}
}
export function IdeasImageDisplay({inspiration,image,imageIndex,totalImages,onPrevImage,onNextImage,canPrev,canNext}:Props){
const[isLoading,setIsLoading]=useState(false)
const[displayedSrc,setDisplayedSrc]=useState<string|null>(null)
const[pendingSrc,setPendingSrc]=useState<string|null>(null)
const[error,setError]=useState<string|null>(null)
const[hovered,setHovered]=useState(false)
const loadVersionRef=useRef(0)
const ch=chCfg[inspiration.targetChannel]||chCfg.general
const ChIcon=ch.icon
//Load image when path changes
useEffect(()=>{
if(!image?.path){setDisplayedSrc(null);setPendingSrc(null);setError('No image');return}
setIsLoading(true);setError(null);setPendingSrc(null)
const version=++loadVersionRef.current
const load=async()=>{
if(!isPyWebView()){setPendingSrc(`file://${image.path}`);return}
try{
const dataUrl=await bridge.getAssetThumbnail(image.path!)
if(loadVersionRef.current!==version)return
if(dataUrl&&dataUrl!==''){setPendingSrc(dataUrl)}
else{setIsLoading(false);setError('Image not found')}
}catch(e){
if(loadVersionRef.current!==version)return
setError(e instanceof Error?e.message:String(e));setIsLoading(false)
}
}
load()
},[image?.path])
//Handle pending image load complete
const handlePendingLoad=useCallback(()=>{setDisplayedSrc(pendingSrc);setPendingSrc(null);setIsLoading(false)},[pendingSrc])
const handlePendingError=useCallback(()=>{setPendingSrc(null);setIsLoading(false);setError('Failed to load image')},[])
const navBtnClass="absolute top-1/2 -translate-y-1/2 z-20 p-2 rounded-full bg-black/50 text-white/90 backdrop-blur-sm transition-all hover:bg-black/70 hover:scale-110 disabled:opacity-30 disabled:pointer-events-none"
const imgClass="max-w-full max-h-full object-contain select-none transition-opacity duration-200"
return(<div className="w-full h-full flex flex-col items-center justify-center relative" onMouseEnter={()=>setHovered(true)} onMouseLeave={()=>setHovered(false)}>
{/* Header with channel + title */}
<div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 flex items-center gap-3 px-4 py-2 rounded-full bg-black/30 dark:bg-black/50 backdrop-blur-sm">
<span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs bg-white/10 text-white/90">
<ChIcon className="w-3.5 h-3.5"/>{ch.label}
</span>
<h2 className="text-sm font-medium text-white truncate max-w-[300px]">{inspiration.title}</h2>
</div>
{/* Image container */}
<div className="flex items-center justify-center overflow-hidden" style={{maxWidth:'calc(100% - 120px)',maxHeight:'calc(100% - 140px)'}}>
<div className="relative max-w-full max-h-full">
{/* Displayed image */}
{displayedSrc&&!error&&(<img draggable={false} src={displayedSrc} alt="" className={imgClass}/>)}
{/* Pending image - fades in */}
{pendingSrc&&pendingSrc!==displayedSrc&&(
<img draggable={false} src={pendingSrc} alt={image?.prompt||'Inspiration image'}
onLoad={handlePendingLoad} onError={handlePendingError}
className={cn(imgClass,"absolute inset-0")} style={{animation:'fadeIn 200ms ease-out forwards'}}/>
)}
</div>
</div>
{/* Loading indicator */}
{isLoading&&!displayedSrc&&(<div className="absolute inset-0 flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground/30"/></div>)}
{/* Error state */}
{!isLoading&&error&&!displayedSrc&&(<div className="text-sm text-muted-foreground">{error}</div>)}
{/* Prompt caption */}
{image?.prompt&&displayedSrc&&(
<div className="absolute bottom-20 left-1/2 -translate-x-1/2 max-w-2xl px-4">
<p className="text-white/70 text-sm italic text-center line-clamp-2 drop-shadow-md">"{image.prompt}"</p>
</div>
)}
{/* Image navigation arrows (within inspiration) */}
{totalImages>1&&(<>
<button onClick={onPrevImage} disabled={!canPrev} className={cn(navBtnClass,"left-4 transition-opacity duration-200",hovered?"opacity-100":"opacity-0")}>
<ChevronLeft className="w-6 h-6"/>
</button>
<button onClick={onNextImage} disabled={!canNext} className={cn(navBtnClass,"right-4 transition-opacity duration-200",hovered?"opacity-100":"opacity-0")}>
<ChevronRight className="w-6 h-6"/>
</button>
</>)}
{/* Image index dots */}
{totalImages>1&&(
<div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-1.5">
{Array.from({length:totalImages},(_,i)=>(
<span key={i} className={cn("w-2 h-2 rounded-full transition-colors",i===imageIndex?"bg-white":"bg-white/30")}/>
))}
</div>
)}
</div>)
}
