//QuickEditPreview - Result overlay with hold-to-compare functionality
import{useState,useEffect,useRef,useCallback}from'react'
import{useQuickEdit}from'../../context/QuickEditContext'
import{bridge,isPyWebView}from'../../lib/bridge'
import{Eye}from'lucide-react'
export function QuickEditPreview(){
const{resultPath}=useQuickEdit()
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
if(!resultPath||!resultSrc)return null
return(<>
{/* Result image overlay - fades based on comparing state */}
<img src={resultSrc} alt="Edited result" onLoad={()=>setLoaded(true)} className="absolute inset-0 w-full h-full object-contain select-none transition-opacity duration-200" style={{zIndex:16,opacity:isComparing?0:1,pointerEvents:'none'}}/>
{/* Compare button + instruction */}
{loaded&&!isComparing&&(<div className="absolute bottom-24 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2">
<button ref={btnRef} onPointerDown={onPointerDown} onPointerUp={onPointerUp} onPointerCancel={onPointerCancel} onPointerLeave={onPointerLeave} onKeyDown={onKeyDown} onKeyUp={onKeyUp} className="p-3 rounded-full bg-black/60 text-white/90 backdrop-blur-sm transition-all hover:bg-black/80 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-white/50"><Eye className="w-5 h-5"/></button>
<span className="text-xs text-white/80 bg-black/50 px-2 py-1 rounded backdrop-blur-sm select-none">Hold to compare</span>
</div>)}
{/* Comparing indicator */}
{isComparing&&(<div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 text-xs text-white/80 bg-black/50 px-3 py-1.5 rounded backdrop-blur-sm select-none">Original</div>)}
</>)
}
