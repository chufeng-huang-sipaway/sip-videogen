//QuickEditPreview - Result overlay with hold-to-compare + action buttons
import{useState,useEffect,useRef,useCallback}from'react'
import{useQuickEdit}from'../../context/QuickEditContext'
import{bridge,isPyWebView}from'../../lib/bridge'
import{toast}from'../ui/toaster'
import{Eye,Check,Copy,RotateCcw,X,Loader2}from'lucide-react'
import{Button}from'../ui/button'
import{Tooltip,TooltipContent,TooltipTrigger}from'../ui/tooltip'
export function QuickEditPreview(){
const{resultPath,isActionLoading,keepAndOverride,saveAsCopy,rerun,discardResult}=useQuickEdit()
const[resultSrc,setResultSrc]=useState<string|null>(null)
const[isComparing,setIsComparing]=useState(false)
const[loaded,setLoaded]=useState(false)
const btnRef=useRef<HTMLButtonElement>(null)
//Load result image
useEffect(()=>{
if(!resultPath){setResultSrc(null);setLoaded(false);return}
const rp=resultPath
let cancelled=false
async function load(){
if(!isPyWebView()){setResultSrc(rp);return}
try{
const dataUrl=await bridge.getAssetFull(rp)
if(!cancelled&&dataUrl)setResultSrc(dataUrl)
}catch(e){console.warn('Failed to load result:',e)}
}
void load()
return()=>{cancelled=true}
},[resultPath])
//Focus compare button when result loads
useEffect(()=>{if(loaded&&btnRef.current)btnRef.current.focus()},[loaded])
//Handle window blur - reset comparing state
useEffect(()=>{
const onBlur=()=>setIsComparing(false)
window.addEventListener('blur',onBlur)
return()=>window.removeEventListener('blur',onBlur)
},[])
//Pointer handlers with capture
const onPointerDown=useCallback((e:React.PointerEvent<HTMLButtonElement>)=>{
e.currentTarget.setPointerCapture(e.pointerId)
setIsComparing(true)
},[])
const onPointerUp=useCallback((e:React.PointerEvent<HTMLButtonElement>)=>{
e.currentTarget.releasePointerCapture(e.pointerId)
setIsComparing(false)
},[])
const onPointerCancel=useCallback(()=>setIsComparing(false),[])
const onPointerLeave=useCallback(()=>setIsComparing(false),[])
//Keyboard handlers
const onKeyDown=useCallback((e:React.KeyboardEvent)=>{
if(e.code==='Space'){e.preventDefault();setIsComparing(true)}
},[])
const onKeyUp=useCallback((e:React.KeyboardEvent)=>{
if(e.code==='Space'){e.preventDefault();setIsComparing(false)}
},[])
//Action handlers
const handleKeep=useCallback(async()=>{
const res=await keepAndOverride()
if(res.success)toast.success('Replaced original')
else toast.error(res.error||'Failed to replace')
},[keepAndOverride])
const handleSave=useCallback(()=>{saveAsCopy();toast.success('Saved as copy')},[saveAsCopy])
const handleRerun=useCallback(()=>{rerun()},[rerun])
const handleDiscard=useCallback(async()=>{await discardResult()},[discardResult])
if(!resultPath||!resultSrc)return null
return(<>
{/* Result image overlay - fades based on comparing state */}
<img src={resultSrc} alt="Edited result" onLoad={()=>setLoaded(true)} className="absolute inset-0 w-full h-full object-contain select-none transition-opacity duration-200" style={{zIndex:16,opacity:isComparing?0:1,pointerEvents:'none'}}/>
{/* Controls - compare button + action buttons */}
{loaded&&!isComparing&&(<div className="absolute bottom-24 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-3">
{/* Compare button */}
<div className="flex flex-col items-center gap-1">
<button ref={btnRef} onPointerDown={onPointerDown} onPointerUp={onPointerUp} onPointerCancel={onPointerCancel} onPointerLeave={onPointerLeave} onKeyDown={onKeyDown} onKeyUp={onKeyUp} className="p-2.5 rounded-full bg-black/60 text-white/90 backdrop-blur-sm transition-all hover:bg-black/80 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-white/50"><Eye className="w-4 h-4"/></button>
<span className="text-[10px] text-white/70 bg-black/40 px-1.5 py-0.5 rounded backdrop-blur-sm select-none">Hold to compare</span>
</div>
{/* Action buttons */}
<div className="flex items-center gap-1 px-2 py-1.5 rounded-full bg-black/70 backdrop-blur-xl shadow-lg">
<Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" onClick={handleKeep} disabled={isActionLoading} className="h-9 w-9 rounded-full text-white/90 hover:bg-emerald-500/30 hover:text-emerald-400 transition-all">{isActionLoading?<Loader2 className="w-4 h-4 animate-spin"/>:<Check className="w-4 h-4"/>}</Button></TooltipTrigger><TooltipContent side="top">Keep & Replace</TooltipContent></Tooltip>
<Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" onClick={handleSave} disabled={isActionLoading} className="h-9 w-9 rounded-full text-white/90 hover:bg-blue-500/30 hover:text-blue-400 transition-all"><Copy className="w-4 h-4"/></Button></TooltipTrigger><TooltipContent side="top">Save as Copy</TooltipContent></Tooltip>
<Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" onClick={handleRerun} disabled={isActionLoading} className="h-9 w-9 rounded-full text-white/90 hover:bg-amber-500/30 hover:text-amber-400 transition-all"><RotateCcw className="w-4 h-4"/></Button></TooltipTrigger><TooltipContent side="top">Rerun</TooltipContent></Tooltip>
<div className="w-px h-5 bg-white/20 mx-0.5"/>
<Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" onClick={handleDiscard} disabled={isActionLoading} className="h-9 w-9 rounded-full text-white/90 hover:bg-red-500/30 hover:text-red-400 transition-all"><X className="w-4 h-4"/></Button></TooltipTrigger><TooltipContent side="top">Discard</TooltipContent></Tooltip>
</div>
</div>)}
{/* Comparing indicator */}
{isComparing&&(<div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 text-xs text-white/80 bg-black/50 px-3 py-1.5 rounded backdrop-blur-sm select-none">Original</div>)}
</>)
}
