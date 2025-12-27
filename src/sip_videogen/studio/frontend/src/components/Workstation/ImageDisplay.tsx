//ImageDisplay component - displays the currently selected image with transitions and preloading
import{useState,useEffect,useRef}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import{useDrag}from'../../context/DragContext'
import{bridge,isPyWebView}from'../../lib/bridge'
import{Loader2}from'lucide-react'
import{getFullCached,setFullCached,hasFullCached}from'../../lib/thumbnailCache'
const PRELOAD_RADIUS=2
function np(path:string):string{return path.startsWith('file://')?path.slice('file://'.length):path}
export function ImageDisplay(){
const{currentBatch,selectedIndex,updateImagePath}=useWorkstation()
const{setDragData}=useDrag()
const currentImage=currentBatch[selectedIndex]
const[isLoading,setIsLoading]=useState(true)
const[isVisible,setIsVisible]=useState(false)
const[src,setSrc]=useState<string|null>(null)
const[error,setError]=useState<string|null>(null)
const prevIdRef=useRef<string|null>(null)
//Handle image transition on selection change
useEffect(()=>{if(!currentImage)return;if(prevIdRef.current!==currentImage.id){setIsVisible(false);setIsLoading(true);setSrc(null);setError(null);const t=setTimeout(()=>setIsVisible(true),50);prevIdRef.current=currentImage.id;return()=>clearTimeout(t)}},[currentImage])
//Resolve image source (prefer data URLs; otherwise load via bridge)
useEffect(()=>{
let cancelled=false
async function load(){
if(!currentImage)return
const raw=currentImage.path
const origPath=currentImage.originalPath
//Check shared cache first
const cacheKey=origPath||np(raw||'')
if(cacheKey&&hasFullCached(cacheKey)){setSrc(getFullCached(cacheKey)!);return}
//Lazy loading: if path is empty but originalPath exists, load via getAssetFull
if((!raw||raw==='')&&origPath){
if(!isPyWebView()){setIsLoading(false);setError('Cannot load in browser');return}
try{
const dataUrl=await bridge.getAssetFull(origPath)
if(cancelled)return
if(!dataUrl||dataUrl===''){setIsLoading(false);setError('Failed to load image data');return}
setFullCached(origPath,dataUrl);updateImagePath(currentImage.id,dataUrl);setSrc(dataUrl)
}catch(e){if(cancelled)return;setError(e instanceof Error?e.message:String(e));setIsLoading(false)}
return
}
if(!raw||raw===''){setIsLoading(false);setError('Missing image path');return}
if(raw.startsWith('data:')||raw.startsWith('http://')||raw.startsWith('https://')){setSrc(raw);return}
const normalized=np(raw)
if(!isPyWebView()){setSrc(normalized.startsWith('/')?`file://${normalized}`:normalized);return}
try{
const dataUrl=await bridge.getImageData(normalized)
if(cancelled)return
setFullCached(normalized,dataUrl);setSrc(dataUrl)
}catch(e){if(cancelled)return;setError(e instanceof Error?e.message:String(e));setIsLoading(false)}
}
void load()
return()=>{cancelled=true}
},[currentImage?.id,currentImage?.path,currentImage?.originalPath,updateImagePath])
//Preload adjacent images after current loads
useEffect(()=>{
if(!currentImage||!isPyWebView()||isLoading)return
let cancelled=false
async function preload(){
for(let offset=-PRELOAD_RADIUS;offset<=PRELOAD_RADIUS;offset++){
if(offset===0||cancelled)continue
const idx=selectedIndex+offset
if(idx<0||idx>=currentBatch.length)continue
const img=currentBatch[idx]
const path=img.originalPath||img.path
if(!path||path.startsWith('data:'))continue
const key=img.originalPath||np(path)
if(hasFullCached(key))continue
try{
const dataUrl=img.originalPath?await bridge.getAssetFull(img.originalPath):await bridge.getImageData(np(path))
if(!cancelled)setFullCached(key,dataUrl)
}catch{}
}
}
void preload()
return()=>{cancelled=true}
},[selectedIndex,currentBatch,currentImage,isLoading])
const handleLoad=()=>{setIsLoading(false)}
const handleError=()=>{setIsLoading(false);setError('Failed to load image')}
//Use mousedown to initiate drag (bypasses PyWebView/WebKit HTML5 drag issues)
const handleMouseDown=(e:React.MouseEvent)=>{if(e.button!==0)return;const path=currentImage?.originalPath||currentImage?.path;if(!path||path.startsWith('data:'))return;setDragData({type:'asset',path})}
if(!currentImage)return null
return(<div className="w-full h-full flex items-center justify-center relative">{isLoading&&(<div className="absolute inset-0 flex items-center justify-center z-10"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground/50"/></div>)}{!isLoading&&error&&(<div className="text-sm text-muted-foreground">{error}</div>)}{src&&(<img draggable={false} onMouseDown={handleMouseDown} src={src} alt={currentImage.prompt||'Generated image'} onLoad={handleLoad} onError={handleError} className={`max-w-full max-h-full object-contain rounded-xl shadow-lg transition-all duration-500 ease-out cursor-grab active:cursor-grabbing select-none ${isVisible&&!isLoading&&!error?'opacity-100 scale-100':'opacity-0 scale-98'}`}/>)}{!src&&!isLoading&&!error&&(<div className="text-sm text-muted-foreground">Image unavailable</div>)}</div>)
}
