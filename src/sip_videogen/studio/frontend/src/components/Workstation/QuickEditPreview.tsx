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
{isComparing&&(<div className="text-xs text-white/90 bg-black/60 px-3 py-1.5 rounded-full backdrop-blur-sm select-none mb-1 animate-pulse">Viewing Original</div>)}
{/* Compare button - always accessible */}
<button ref={btnRef} onPointerDown={onPointerDown} onPointerUp={onPointerUp} onPointerCancel={onPointerCancel} onPointerLeave={onPointerLeave} onKeyDown={onKeyDown} onKeyUp={onKeyUp} className={cn("p-2 rounded-full backdrop-blur-sm transition-all focus:outline-none focus:ring-2 focus:ring-white/50",isComparing?"bg-white/20 text-white scale-95":"bg-black/50 text-white/80 hover:bg-black/70 hover:scale-105")}><Eye className="w-4 h-4"/></button>
<span className="text-[10px] text-white/60 select-none">{isComparing?'Release to see result':'Hold to compare'}</span>
{/* Action toolbar - clean pill design with labels */}
<div className="flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-black/85 backdrop-blur-xl shadow-2xl border border-white/10">
<button onClick={handleKeep} disabled={isActionLoading} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-white hover:bg-emerald-500/30 hover:text-emerald-300 transition-all disabled:opacity-50">{isActionLoading?<Loader2 className="w-4 h-4 animate-spin"/>:<Check className="w-4 h-4"/>}<span className="text-sm font-medium">Keep</span></button>
<button onClick={handleSave} disabled={isActionLoading} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-white hover:bg-blue-500/30 hover:text-blue-300 transition-all disabled:opacity-50"><Copy className="w-4 h-4"/><span className="text-sm font-medium">Save Copy</span></button>
<div className="w-px h-5 bg-white/20"/>
<button onClick={()=>setShowEditInput(!showEditInput)} disabled={isActionLoading} className={cn("flex items-center gap-1.5 px-3 py-1.5 rounded-xl transition-all disabled:opacity-50",showEditInput?"bg-violet-500/40 text-violet-300":"text-white hover:bg-violet-500/30 hover:text-violet-300")}><Sparkles className="w-4 h-4"/><span className="text-sm font-medium">Edit More</span></button>
<div className="w-px h-5 bg-white/20"/>
<button onClick={handleDiscard} disabled={isActionLoading} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-white/60 hover:bg-red-500/30 hover:text-red-300 transition-all disabled:opacity-50"><X className="w-4 h-4"/><span className="text-sm font-medium">Discard</span></button>
</div>
{/* Continue editing input */}
{showEditInput&&(<div className="flex items-center gap-2 px-3 py-2 rounded-full bg-black/80 backdrop-blur-xl shadow-2xl border border-violet-500/30 mt-1 animate-in fade-in slide-in-from-bottom-2 duration-200">
<Sparkles className="w-4 h-4 text-violet-400 shrink-0"/>
<input ref={inputRef} type="text" value={editPrompt} onChange={e=>setEditPrompt(e.target.value)} onKeyDown={handleEditKeyDown} placeholder="Describe another edit..." className="bg-transparent text-white text-sm placeholder:text-white/40 outline-none w-56"/>
<Button variant="ghost" size="icon" onClick={handleContinueEdit} disabled={!editPrompt.trim()} className="h-8 w-8 rounded-full text-violet-300 hover:bg-violet-500/30 disabled:opacity-30"><Send className="w-4 h-4"/></Button>
</div>)}
</div>)}
</>)
}
