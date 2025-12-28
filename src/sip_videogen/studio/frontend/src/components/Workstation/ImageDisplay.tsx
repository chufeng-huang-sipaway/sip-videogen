//ImageDisplay component - displays the currently selected image with smooth crossfade transitions
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
const[isLoading,setIsLoading]=useState(false)
const[displayedSrc,setDisplayedSrc]=useState<string|null>(null)//Currently shown image
const[pendingSrc,setPendingSrc]=useState<string|null>(null)//New image loading in
const[error,setError]=useState<string|null>(null)
const prevIdRef=useRef<string|null>(null)
dbg('render',{id:currentImage?.id,selectedIndex,batchLen:currentBatch.length,isLoading,hasDisplayed:!!displayedSrc,hasPending:!!pendingSrc,error})
//Handle image transition - DON'T clear displayedSrc, just mark loading
useEffect(()=>{if(!currentImage)return;if(prevIdRef.current!==currentImage.id){dbg('id changed',prevIdRef.current,'→',currentImage.id);setIsLoading(true);setPendingSrc(null);setError(null);prevIdRef.current=currentImage.id}},[currentImage?.id])
//Resolve image source (prefer data URLs; otherwise load via bridge)
useEffect(()=>{
let cancelled=false
async function load(){
if(!currentImage){dbg('no currentImage');return}
const raw=currentImage.path
const origPath=currentImage.originalPath
dbg('load start',{raw:raw?.slice(-40),origPath:origPath?.slice(-40)})
//Check shared cache first - if cached, swap instantly
const cacheKey=origPath||np(raw||'')
if(cacheKey&&hasFullCached(cacheKey)){const cached=getFullCached(cacheKey)!;dbg('cache hit',cacheKey.slice(-40));setPendingSrc(cached);return}
dbg('cache miss',cacheKey?.slice(-40))
//Lazy loading: if path is empty but originalPath exists, load via getAssetFull
if((!raw||raw==='')&&origPath){
dbg('using getAssetFull branch')
if(!isPyWebView()){setIsLoading(false);setError('Cannot load in browser');return}
try{
const dataUrl=await bridge.getAssetFull(origPath)
dbg('getAssetFull result',{len:dataUrl?.length,cancelled})
if(cancelled)return
if(dataUrl&&dataUrl!==''){setFullCached(origPath,dataUrl);updateImagePath(currentImage.id,dataUrl);setPendingSrc(dataUrl)}
else{setIsLoading(false);setError('Image not found')}
}catch(e){dbg('getAssetFull error',e);if(!cancelled){setError(e instanceof Error?e.message:String(e));setIsLoading(false)}}
return
}
if(!raw||raw===''){dbg('missing path');setIsLoading(false);setError('Missing image path');return}
if(raw.startsWith('data:')||raw.startsWith('http://')||raw.startsWith('https://')){dbg('direct URL');setPendingSrc(raw);return}
const normalized=np(raw)
dbg('using getImageData branch',normalized.slice(-40))
if(!isPyWebView()){setPendingSrc(normalized.startsWith('/')?`file://${normalized}`:normalized);return}
try{
const dataUrl=await bridge.getImageData(normalized)
dbg('getImageData result',{len:dataUrl?.length,cancelled})
if(cancelled)return
if(dataUrl&&dataUrl!==''){setFullCached(normalized,dataUrl);setPendingSrc(dataUrl);dbg('pendingSrc set')}
else{setIsLoading(false);setError('Image not found')}
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
//When pending image loads, promote it to displayed (completes crossfade)
const handlePendingLoad=()=>{dbg('pending img onLoad - promoting to displayed');setDisplayedSrc(pendingSrc);setPendingSrc(null);setIsLoading(false)}
const handlePendingError=()=>{dbg('pending img onError');setPendingSrc(null);setIsLoading(false);setError('Failed to load image')}
//Use mousedown to initiate drag (bypasses PyWebView/WebKit HTML5 drag issues)
const handleMouseDown=(e:React.MouseEvent)=>{if(e.button!==0)return;const path=currentImage?.originalPath||currentImage?.path;if(!path||path.startsWith('data:'))return;setDragData({type:'asset',path})}
if(!currentImage)return null
const debugInfo=DEBUG?`id:${currentImage.id?.slice(-8)||'?'} idx:${selectedIndex} displayed:${displayedSrc?'Y':'N'} pending:${pendingSrc?'Y':'N'} loading:${isLoading} err:${error||'none'}`:''
const imgClass="absolute inset-0 w-full h-full object-contain rounded-xl shadow-lg cursor-grab active:cursor-grabbing select-none"
return(<div className="w-full h-full flex items-center justify-center relative">
{DEBUG&&(<div className="absolute top-2 left-2 right-2 z-50 bg-black/80 text-white text-[10px] font-mono p-2 rounded">{debugInfo}</div>)}
{/* Currently displayed image - stays visible during transition */}
{displayedSrc&&!error&&(<img draggable={false} onMouseDown={handleMouseDown} src={displayedSrc} alt="" className={`${imgClass} transition-opacity duration-300`}/>)}
{/* Pending image - fades in on top, then becomes displayed */}
{pendingSrc&&pendingSrc!==displayedSrc&&(<img draggable={false} src={pendingSrc} alt={currentImage.prompt||'Generated image'} onLoad={handlePendingLoad} onError={handlePendingError} className={`${imgClass}`} style={{animation:'fadeIn 200ms ease-out forwards'}}/>)}
{/* Loading indicator - subtle, doesn't block view */}
{isLoading&&!displayedSrc&&(<div className="absolute inset-0 flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground/30"/></div>)}
{/* Error state */}
{!isLoading&&error&&!displayedSrc&&(<div className="text-sm text-muted-foreground">{error}</div>)}
</div>)
}
