//TrashView component - displays trashed images with restore/delete options and animations
import{useCallback,useMemo,useState,useEffect,useRef}from'react'
import{useWorkstation,type GeneratedImage}from'../../context/WorkstationContext'
import{useBrand}from'../../context/BrandContext'
import{bridge,isPyWebView}from'../../lib/bridge'
import{Button}from'../ui/button'
import{Tooltip,TooltipContent,TooltipProvider,TooltipTrigger}from'../ui/tooltip'
import{RotateCcw,Trash2,ArrowLeft,Loader2}from'lucide-react'
import{cn}from'../../lib/utils'
function normalizeImagePath(path:string):string{return path.startsWith('file://')?path.slice('file://'.length):path}
async function resolveFullImageSrc(rawPath:string):Promise<string>{
if(rawPath.startsWith('data:')||rawPath.startsWith('http://')||rawPath.startsWith('https://'))return rawPath
const normalized=normalizeImagePath(rawPath)
if(!isPyWebView())return normalized.startsWith('/')?`file://${normalized}`:normalized
return await bridge.getImageData(normalized)
}
//Session-level cache for thumbnails
const thumbCache=new Map<string,string>()
function Thumb({path}:{path:string}){
const[src,setSrc]=useState<string|null>(()=>thumbCache.get(path)??null)
const[loading,setLoading]=useState(!thumbCache.has(path))
const mountedRef=useRef(true)
useEffect(()=>{mountedRef.current=true;return()=>{mountedRef.current=false}},[])
useEffect(()=>{if(!path){setLoading(false);return}
if(thumbCache.has(path)){setSrc(thumbCache.get(path)!);setLoading(false);return}
if(path.startsWith('data:')){setSrc(path);setLoading(false);return}
if(!isPyWebView()){setLoading(false);return}
let cancelled=false
async function load(){try{const dataUrl=await bridge.getImageThumbnail(path)
if(cancelled||!mountedRef.current)return
thumbCache.set(path,dataUrl);setSrc(dataUrl)}catch(e){console.error('Thumb load error:',e)}finally{if(!cancelled&&mountedRef.current)setLoading(false)}}
void load();return()=>{cancelled=true}},[path])
return(<div className="w-full h-full flex items-center justify-center bg-muted/20">{loading?(<Loader2 className="w-3 h-3 animate-spin text-muted-foreground/30"/>):src?(<img src={src} alt="" className="w-full h-full object-cover"/>):null}</div>)
}
interface TrashViewProps{onExit:()=>void}
export function TrashView({onExit}:TrashViewProps){
const{currentBatch,selectedIndex,setCurrentBatch,setSelectedIndex,bumpStatusVersion}=useWorkstation()
const{activeBrand}=useBrand()
const currentImage=currentBatch[selectedIndex]
const[isLoading,setIsLoading]=useState(true)
const[isVisible,setIsVisible]=useState(false)
const[src,setSrc]=useState<string|null>(null)
const[error,setError]=useState<string|null>(null)
//Handle image load transition
useEffect(()=>{if(!currentImage)return;setIsVisible(false);setIsLoading(true);setSrc(null);setError(null);const t=setTimeout(()=>setIsVisible(true),50);return()=>clearTimeout(t)},[currentImage?.id])
useEffect(()=>{let cancelled=false
async function load(){if(!currentImage)return
try{const resolved=await resolveFullImageSrc(currentImage.originalPath||currentImage.path);if(cancelled)return;setSrc(resolved)}catch(e){if(cancelled)return;setError(e instanceof Error?e.message:String(e));setIsLoading(false)}}
void load()
return()=>{cancelled=true}},[currentImage?.id,currentImage?.originalPath,currentImage?.path])
const handleLoad=()=>setIsLoading(false)
const handleError=()=>{setIsLoading(false);setError('Failed to load image')}
//Calculate days until deletion (30 days from trashedAt)
const daysRemaining=useMemo(()=>{if(!currentImage)return null
const img=currentImage as GeneratedImage&{trashedAt?:string}
if(!img.trashedAt)return null
try{const trashedDate=new Date(img.trashedAt);const now=new Date();const diffMs=now.getTime()-trashedDate.getTime();const daysPassed=Math.floor(diffMs/(1000*60*60*24));return Math.max(0,30-daysPassed)}catch{return null}},[currentImage])
//Restore current image
const handleRestore=useCallback(async()=>{if(!currentImage||!activeBrand)return
try{await bridge.restoreImage(currentImage.id,activeBrand)
const newBatch=[...currentBatch];newBatch.splice(selectedIndex,1);setCurrentBatch(newBatch)
if(selectedIndex>=newBatch.length&&newBatch.length>0)setSelectedIndex(newBatch.length-1)
if(newBatch.length===0)onExit()
bumpStatusVersion()}catch(e){console.error('Failed to restore image:',e)}},[currentImage,activeBrand,currentBatch,selectedIndex,setCurrentBatch,setSelectedIndex,onExit,bumpStatusVersion])
//Empty all trash
const handleEmptyTrash=useCallback(async()=>{if(!activeBrand)return
if(!window.confirm('Permanently delete all trashed images? This cannot be undone.'))return
try{await bridge.emptyTrash(activeBrand);setCurrentBatch([]);onExit();bumpStatusVersion()}catch(e){console.error('Failed to empty trash:',e)}},[activeBrand,setCurrentBatch,onExit,bumpStatusVersion])
if(currentBatch.length===0)return(<div className="flex-1 flex flex-col items-center justify-center text-muted-foreground animate-in fade-in duration-300"><Trash2 className="w-12 h-12 mb-4 opacity-50"/><p className="text-sm font-medium">Recycle Bin is empty</p><Button variant="ghost" size="sm" className="mt-4 gap-2" onClick={onExit}><ArrowLeft className="w-4 h-4"/>Back to Workstation</Button></div>)
return(<TooltipProvider><div className="flex-1 flex flex-col h-full min-h-0 overflow-hidden">
{/* Header */}
<div className="flex items-center justify-between px-4 py-2 border-b border-border/50 bg-background/50">
<div className="flex items-center gap-3"><Button variant="ghost" size="icon" className="h-8 w-8 transition-transform hover:scale-105" onClick={onExit}><ArrowLeft className="w-4 h-4"/></Button><div className="flex items-center gap-2"><Trash2 className="w-4 h-4 text-muted-foreground"/><span className="text-sm font-medium">Recycle Bin</span><span className="text-xs text-muted-foreground">({currentBatch.length} items)</span></div></div>
<div className="flex items-center gap-2">
<Tooltip><TooltipTrigger asChild><Button variant="outline" size="sm" className="gap-1.5 transition-transform hover:scale-105" onClick={handleRestore} disabled={!currentImage}><RotateCcw className="w-3.5 h-3.5"/>Restore</Button></TooltipTrigger><TooltipContent>Restore to unsorted</TooltipContent></Tooltip>
<Tooltip><TooltipTrigger asChild><Button variant="destructive" size="sm" className="gap-1.5 transition-transform hover:scale-105" onClick={handleEmptyTrash}><Trash2 className="w-3.5 h-3.5"/>Empty Recycle Bin</Button></TooltipTrigger><TooltipContent>Permanently delete all</TooltipContent></Tooltip>
</div></div>
{/* Main image display */}
<div className="flex-1 relative flex items-center justify-center p-4 bg-secondary/20 overflow-hidden min-h-0">
{currentImage&&(<>{isLoading&&<Loader2 className="absolute w-8 h-8 animate-spin text-muted-foreground/50"/>}{!isLoading&&error&&<div className="text-sm text-muted-foreground">{error}</div>}{src&&(<img src={src} alt="Trashed image" onLoad={handleLoad} onError={handleError} className={`max-w-full max-h-full object-contain rounded-lg shadow-lg transition-all duration-300 ${isVisible&&!isLoading&&!error?'opacity-100 scale-100':'opacity-0 scale-95'}`}/>)}
{/* Days remaining badge */}
{daysRemaining!==null&&(<div className={`absolute bottom-6 left-1/2 -translate-x-1/2 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-300 ${isVisible&&!isLoading?'opacity-100 translate-y-0':'opacity-0 translate-y-2'} ${daysRemaining<=7?'bg-destructive/90 text-destructive-foreground':'bg-muted/90 text-muted-foreground'}`}>{daysRemaining===0?'Deleting today':daysRemaining===1?'1 day until deletion':`${daysRemaining} days until deletion`}</div>)}</>)}
</div>
{/* Thumbnail strip */}
{currentBatch.length>1&&(<div className="flex-shrink-0 flex gap-2 p-3 overflow-x-auto border-t border-border/50 bg-background/50">{currentBatch.map((img,i)=>(<button key={img.id} onClick={()=>setSelectedIndex(i)} className={cn("flex-shrink-0 w-16 h-16 rounded-lg overflow-hidden border-2 transition-all duration-200 hover:scale-105 bg-muted/30",i===selectedIndex?'border-primary shadow-md scale-105':'border-transparent hover:border-muted-foreground/30')}><Thumb path={img.originalPath||img.path||''}/></button>))}</div>)}
</div></TooltipProvider>)}
