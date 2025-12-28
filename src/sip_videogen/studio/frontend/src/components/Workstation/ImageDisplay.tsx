//ImageDisplay component - displays the currently selected image with transitions and preloading
import{useState,useEffect,useRef}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import{useDrag}from'../../context/DragContext'
import{bridge,isPyWebView}from'../../lib/bridge'
import{Loader2}from'lucide-react'
import{getFullCached,setFullCached,hasFullCached}from'../../lib/thumbnailCache'
const PRELOAD_RADIUS=2
const DEBUG=false
function np(path:string):string{return path.startsWith('file://')?path.slice('file://'.length):path}
function dbg(...args:unknown[]){if(DEBUG)console.log('[ImageDisplay]',...args)}
export function ImageDisplay(){
const{currentBatch,selectedIndex,updateImagePath}=useWorkstation()
const{setDragData}=useDrag()
const currentImage=currentBatch[selectedIndex]
const[isLoading,setIsLoading]=useState(true)
const[isVisible,setIsVisible]=useState(false)
const[src,setSrc]=useState<string|null>(null)
const[error,setError]=useState<string|null>(null)
const prevIdRef=useRef<string|null>(null)
dbg('render',{id:currentImage?.id,path:currentImage?.path?.slice(-40),origPath:currentImage?.originalPath?.slice(-40),selectedIndex,batchLen:currentBatch.length,isLoading,isVisible,hasSrc:!!src,error})
//Handle image transition on selection change - use id as dependency to avoid timer cancellation from unrelated updates
useEffect(()=>{if(!currentImage)return;if(prevIdRef.current!==currentImage.id){dbg('id changed',prevIdRef.current,'→',currentImage.id);setIsVisible(false);setIsLoading(true);setSrc(null);setError(null);const t=setTimeout(()=>{dbg('visibility timer fired');setIsVisible(true)},50);prevIdRef.current=currentImage.id;return()=>clearTimeout(t)}},[currentImage?.id])
//Resolve image source (prefer data URLs; otherwise load via bridge)
useEffect(()=>{
let cancelled=false
async function load(){
if(!currentImage){dbg('no currentImage');return}
const raw=currentImage.path
const origPath=currentImage.originalPath
dbg('load start',{raw:raw?.slice(-40),origPath:origPath?.slice(-40)})
//Check shared cache first
const cacheKey=origPath||np(raw||'')
if(cacheKey&&hasFullCached(cacheKey)){dbg('cache hit',cacheKey.slice(-40));setSrc(getFullCached(cacheKey)!);return}
dbg('cache miss',cacheKey?.slice(-40))
//Lazy loading: if path is empty but originalPath exists, load via getAssetFull
if((!raw||raw==='')&&origPath){
dbg('using getAssetFull branch')
if(!isPyWebView()){setIsLoading(false);setError('Cannot load in browser');return}
try{
const dataUrl=await bridge.getAssetFull(origPath)
dbg('getAssetFull result',{len:dataUrl?.length,cancelled})
if(dataUrl&&dataUrl!==''){setFullCached(origPath,dataUrl);updateImagePath(currentImage.id,dataUrl);setSrc(dataUrl)}
else if(!cancelled){setIsLoading(false);setError('Failed to load image data')}
}catch(e){dbg('getAssetFull error',e);if(!cancelled){setError(e instanceof Error?e.message:String(e));setIsLoading(false)}}
return
}
if(!raw||raw===''){dbg('missing path');setIsLoading(false);setError('Missing image path');return}
if(raw.startsWith('data:')||raw.startsWith('http://')||raw.startsWith('https://')){dbg('direct URL');setSrc(raw);return}
const normalized=np(raw)
dbg('using getImageData branch',normalized.slice(-40))
if(!isPyWebView()){setSrc(normalized.startsWith('/')?`file://${normalized}`:normalized);return}
try{
const dataUrl=await bridge.getImageData(normalized)
dbg('getImageData result',{len:dataUrl?.length,prefix:dataUrl?.slice(0,30),cancelled})
if(dataUrl&&dataUrl!==''){setFullCached(normalized,dataUrl);setSrc(dataUrl);dbg('src set')}
else{dbg('empty dataUrl');if(!cancelled){setIsLoading(false);setError('Failed to load image data')}}
}catch(e){dbg('getImageData error',e);if(!cancelled){setError(e instanceof Error?e.message:String(e));setIsLoading(false)}}
}
void load()
return()=>{dbg('cleanup - setting cancelled');cancelled=true}
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
const handleLoad=()=>{dbg('img onLoad fired');setIsLoading(false)}
const handleError=()=>{dbg('img onError fired');setIsLoading(false);setError('Failed to load image')}
//Use mousedown to initiate drag (bypasses PyWebView/WebKit HTML5 drag issues)
const handleMouseDown=(e:React.MouseEvent)=>{if(e.button!==0)return;const path=currentImage?.originalPath||currentImage?.path;if(!path||path.startsWith('data:'))return;setDragData({type:'asset',path})}
if(!currentImage)return null
const debugInfo=DEBUG?`id:${currentImage.id?.slice(-8)||'?'} idx:${selectedIndex} batch:${currentBatch.length} path:${currentImage.path?.slice(-30)||'none'} origPath:${currentImage.originalPath?.slice(-30)||'none'} src:${src?'YES('+src.length+')':'NO'} loading:${isLoading} visible:${isVisible} err:${error||'none'}`:''
return(<div className="w-full h-full flex items-center justify-center relative">{DEBUG&&(<div className="absolute top-2 left-2 right-2 z-50 bg-black/80 text-white text-[10px] font-mono p-2 rounded overflow-x-auto whitespace-pre-wrap break-all">{debugInfo}</div>)}{isLoading&&(<div className="absolute inset-0 flex items-center justify-center z-10"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground/50"/></div>)}{!isLoading&&error&&(<div className="text-sm text-muted-foreground">{error}</div>)}{src&&(<img draggable={false} onMouseDown={handleMouseDown} src={src} alt={currentImage.prompt||'Generated image'} onLoad={handleLoad} onError={handleError} className={`max-w-full max-h-full object-contain rounded-xl shadow-lg transition-all duration-500 ease-out cursor-grab active:cursor-grabbing select-none ${isVisible&&!isLoading&&!error?'opacity-100 scale-100':'opacity-0 scale-98'}`}/>)}{!src&&!isLoading&&!error&&(<div className="text-sm text-muted-foreground">Image unavailable</div>)}</div>)
}
