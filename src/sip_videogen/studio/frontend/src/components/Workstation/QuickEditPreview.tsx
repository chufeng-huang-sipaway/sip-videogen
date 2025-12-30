//QuickEditPreview - Result overlay with hold-to-compare + action buttons
import{useState,useEffect,useRef,useCallback}from'react'
import{useQuickEdit}from'../../context/QuickEditContext'
import{bridge,isPyWebView}from'../../lib/bridge'
import{toast}from'../ui/toaster'
import{Eye,Check,Copy,X,Loader2,Sparkles,Send}from'lucide-react'
import{cn}from'@/lib/utils'
import{Button}from'../ui/button'
export function QuickEditPreview(){
const{resultPath,isActionLoading,keepAndOverride,saveAsCopy,discardResult,submitEdit}=useQuickEdit()
const[resultSrc,setResultSrc]=useState<string|null>(null)
const[isComparing,setIsComparing]=useState(false)
const[loaded,setLoaded]=useState(false)
const[editPrompt,setEditPrompt]=useState('')
const[showEditInput,setShowEditInput]=useState(false)
const btnRef=useRef<HTMLButtonElement>(null)
const inputRef=useRef<HTMLInputElement>(null)
//Load result image
useEffect(()=>{
if(!resultPath){setResultSrc(null);setLoaded(false);setShowEditInput(false);setEditPrompt('');return}
const rp=resultPath;let cancelled=false
async function load(){
if(!isPyWebView()){setResultSrc(rp);return}
try{const dataUrl=await bridge.getAssetFull(rp);if(!cancelled&&dataUrl)setResultSrc(dataUrl)}catch(e){console.warn('Failed to load result:',e)}
}
void load();return()=>{cancelled=true}
},[resultPath])
//Focus compare button when result loads
useEffect(()=>{if(loaded&&btnRef.current&&!showEditInput)btnRef.current.focus()},[loaded,showEditInput])
//Focus input when edit mode opens
useEffect(()=>{if(showEditInput&&inputRef.current)setTimeout(()=>inputRef.current?.focus(),50)},[showEditInput])
//Handle window blur - reset comparing state
useEffect(()=>{const onBlur=()=>setIsComparing(false);window.addEventListener('blur',onBlur);return()=>window.removeEventListener('blur',onBlur)},[])
//Pointer handlers with capture for compare button
const onPointerDown=useCallback((e:React.PointerEvent<HTMLButtonElement>)=>{e.currentTarget.setPointerCapture(e.pointerId);setIsComparing(true)},[])
const onPointerUp=useCallback((e:React.PointerEvent<HTMLButtonElement>)=>{e.currentTarget.releasePointerCapture(e.pointerId);setIsComparing(false)},[])
const onPointerCancel=useCallback(()=>setIsComparing(false),[])
const onPointerLeave=useCallback(()=>setIsComparing(false),[])
//Keyboard handlers for compare
const onKeyDown=useCallback((e:React.KeyboardEvent)=>{if(e.code==='Space'){e.preventDefault();setIsComparing(true)}},[])
const onKeyUp=useCallback((e:React.KeyboardEvent)=>{if(e.code==='Space'){e.preventDefault();setIsComparing(false)}},[])
//Action handlers
const handleKeep=useCallback(async()=>{const res=await keepAndOverride();if(res.success)toast.success('Replaced original');else toast.error(res.error||'Failed to replace')},[keepAndOverride])
const handleSave=useCallback(()=>{saveAsCopy();toast.success('Saved as copy')},[saveAsCopy])
const handleDiscard=useCallback(async()=>{await discardResult()},[discardResult])
//Continue editing handler
const handleContinueEdit=useCallback(async()=>{
const trimmed=editPrompt.trim();if(!trimmed)return
setShowEditInput(false);setEditPrompt('')
await submitEdit(trimmed)
},[editPrompt,submitEdit])
const handleEditKeyDown=useCallback((e:React.KeyboardEvent<HTMLInputElement>)=>{if(e.key==='Enter'){e.preventDefault();handleContinueEdit()}else if(e.key==='Escape'){setShowEditInput(false);setEditPrompt('')}},[handleContinueEdit])
if(!resultPath||!resultSrc)return null
return(<>
{/* Result image overlay - fades based on comparing state */}
<img src={resultSrc} alt="Edited result" onLoad={()=>setLoaded(true)} className="absolute inset-0 w-full h-full object-contain select-none transition-opacity duration-200" style={{zIndex:16,opacity:isComparing?0:1,pointerEvents:'none'}}/>
{/* Controls panel - ALWAYS visible when loaded (not hidden during compare) */}
{loaded&&(<div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2">
{/* Comparing indicator - shows above controls */}
{isComparing&&(<div className="text-[10px] text-white/80 bg-white/15 px-3 py-1 rounded-full backdrop-blur-2xl select-none mb-1 border border-white/20 font-medium tracking-wide">Viewing Original</div>)}
{/* Compare button - always accessible */}
<button ref={btnRef} onPointerDown={onPointerDown} onPointerUp={onPointerUp} onPointerCancel={onPointerCancel} onPointerLeave={onPointerLeave} onKeyDown={onKeyDown} onKeyUp={onKeyUp} className={cn("p-2.5 rounded-full backdrop-blur-2xl transition-all focus:outline-none focus:ring-2 focus:ring-white/30",isComparing?"bg-white/25 text-white scale-95":"bg-white/10 text-white/70 hover:bg-white/20 hover:text-white hover:scale-105 border border-white/20")}><Eye className="w-4 h-4"/></button>
<span className="text-[10px] text-white/50 select-none font-medium tracking-wide">{isComparing?'Release':'Hold to compare'}</span>
{/* Action toolbar - minimalist glass design */}
<div className="flex items-center gap-1 p-1.5 rounded-full bg-white/10 backdrop-blur-2xl shadow-lg border border-white/20">
<button onClick={handleKeep} disabled={isActionLoading} className="group flex items-center gap-1.5 px-3.5 py-2 rounded-full text-white/90 hover:bg-white/15 active:scale-95 transition-all disabled:opacity-40">{isActionLoading?<Loader2 className="w-3.5 h-3.5 animate-spin"/>:<Check className="w-3.5 h-3.5 group-hover:text-emerald-400 transition-colors"/>}<span className="text-xs font-medium tracking-wide">Keep</span></button>
<button onClick={handleSave} disabled={isActionLoading} className="group flex items-center gap-1.5 px-3.5 py-2 rounded-full text-white/90 hover:bg-white/15 active:scale-95 transition-all disabled:opacity-40"><Copy className="w-3.5 h-3.5 group-hover:text-blue-400 transition-colors"/><span className="text-xs font-medium tracking-wide">Save Copy</span></button>
<button onClick={()=>setShowEditInput(!showEditInput)} disabled={isActionLoading} className={cn("group flex items-center gap-1.5 px-3.5 py-2 rounded-full active:scale-95 transition-all disabled:opacity-40",showEditInput?"bg-white/20 text-violet-300":"text-white/90 hover:bg-white/15")}><Sparkles className={cn("w-3.5 h-3.5 transition-colors",showEditInput?"text-violet-300":"group-hover:text-violet-400")}/><span className="text-xs font-medium tracking-wide">Edit</span></button>
<button onClick={handleDiscard} disabled={isActionLoading} className="group flex items-center gap-1.5 px-3.5 py-2 rounded-full text-white/50 hover:bg-white/10 hover:text-white/70 active:scale-95 transition-all disabled:opacity-40"><X className="w-3.5 h-3.5 group-hover:text-rose-400 transition-colors"/><span className="text-xs font-medium tracking-wide">Discard</span></button>
</div>
{/* Continue editing input */}
{showEditInput&&(<div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 backdrop-blur-2xl shadow-lg border border-white/20 mt-1 animate-in fade-in slide-in-from-bottom-2 duration-200">
<Sparkles className="w-3.5 h-3.5 text-violet-400 shrink-0"/>
<input ref={inputRef} type="text" value={editPrompt} onChange={e=>setEditPrompt(e.target.value)} onKeyDown={handleEditKeyDown} placeholder="Describe another edit..." className="bg-transparent text-white text-xs placeholder:text-white/40 outline-none w-48 font-medium"/>
<Button variant="ghost" size="icon" onClick={handleContinueEdit} disabled={!editPrompt.trim()} className="h-7 w-7 rounded-full text-violet-400 hover:bg-white/15 disabled:opacity-30"><Send className="w-3.5 h-3.5"/></Button>
</div>)}
</div>)}
</>)
}
