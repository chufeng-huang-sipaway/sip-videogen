//QuickEditPreview - Result overlay with hold-to-compare + action buttons
import{useState,useEffect,useRef,useCallback}from'react'
import{useQuickEdit}from'../../context/QuickEditContext'
import{bridge,isPyWebView}from'../../lib/bridge'
import{toast}from'../ui/toaster'
import{Eye,Check,Copy,X,Loader2,Sparkles,Send}from'lucide-react'
import{cn}from'@/lib/utils'
import{Button}from'../ui/button'
//Result image overlay - renders inside image wrapper to match original image bounds
export function QuickEditResultImage(){
const{resultPath,isComparing}=useQuickEdit()
const[resultSrc,setResultSrc]=useState<string|null>(null)
const[loaded,setLoaded]=useState(false)
//Load result image
useEffect(()=>{
if(!resultPath){setResultSrc(null);setLoaded(false);return}
const rp=resultPath;let cancelled=false
async function load(){
if(!isPyWebView()){setResultSrc(rp);return}
try{const dataUrl=await bridge.getAssetFull(rp);if(!cancelled&&dataUrl)setResultSrc(dataUrl)}catch(e){console.warn('Failed to load result:',e)}
}
void load();return()=>{cancelled=true}
},[resultPath])
if(!resultPath||!resultSrc)return null
return(<img src={resultSrc} alt="Edited result" onLoad={()=>setLoaded(true)} className={cn("absolute inset-0 w-full h-full object-contain select-none transition-opacity duration-200",!loaded&&"opacity-0")} style={{zIndex:16,opacity:loaded?(isComparing?0:1):0,pointerEvents:'none'}}/>)
}
//Controls panel - renders outside image wrapper to avoid clipping
export function QuickEditPreview(){
const{resultPath,isActionLoading,isComparing,setIsComparing,keepAndOverride,saveAsCopy,discardResult,submitEdit}=useQuickEdit()
const[resultSrc,setResultSrc]=useState<string|null>(null)
const[loaded,setLoaded]=useState(false)
const[editPrompt,setEditPrompt]=useState('')
const[showEditInput,setShowEditInput]=useState(false)
const btnRef=useRef<HTMLButtonElement>(null)
const inputRef=useRef<HTMLInputElement>(null)
//Load result image (for loaded state tracking)
useEffect(()=>{
if(!resultPath){setResultSrc(null);setLoaded(false);setShowEditInput(false);setEditPrompt('');return}
const rp=resultPath;let cancelled=false
async function load(){
if(!isPyWebView()){setResultSrc(rp);setLoaded(true);return}
try{const dataUrl=await bridge.getAssetFull(rp);if(!cancelled&&dataUrl){setResultSrc(dataUrl);setLoaded(true)}}catch(e){console.warn('Failed to load result:',e)}
}
void load();return()=>{cancelled=true}
},[resultPath])
//Focus compare button when result loads
useEffect(()=>{if(loaded&&btnRef.current&&!showEditInput)btnRef.current.focus()},[loaded,showEditInput])
//Focus input when edit mode opens
useEffect(()=>{if(showEditInput&&inputRef.current)setTimeout(()=>inputRef.current?.focus(),50)},[showEditInput])
//Handle window blur - reset comparing state
useEffect(()=>{const onBlur=()=>setIsComparing(false);window.addEventListener('blur',onBlur);return()=>window.removeEventListener('blur',onBlur)},[setIsComparing])
//Pointer handlers with capture for compare button
const onPointerDown=useCallback((e:React.PointerEvent<HTMLButtonElement>)=>{e.currentTarget.setPointerCapture(e.pointerId);setIsComparing(true)},[setIsComparing])
const onPointerUp=useCallback((e:React.PointerEvent<HTMLButtonElement>)=>{e.currentTarget.releasePointerCapture(e.pointerId);setIsComparing(false)},[setIsComparing])
const onPointerCancel=useCallback(()=>setIsComparing(false),[setIsComparing])
const onPointerLeave=useCallback(()=>setIsComparing(false),[setIsComparing])
//Keyboard handlers for compare
const onKeyDown=useCallback((e:React.KeyboardEvent)=>{if(e.code==='Space'){e.preventDefault();setIsComparing(true)}},[setIsComparing])
const onKeyUp=useCallback((e:React.KeyboardEvent)=>{if(e.code==='Space'){e.preventDefault();setIsComparing(false)}},[setIsComparing])
//Action handlers
const handleKeep=useCallback(async()=>{const res=await keepAndOverride();if(res.success)toast.success('Replaced original');else toast.error(res.error||'Failed to replace')},[keepAndOverride])
const handleSave=useCallback(()=>{saveAsCopy();toast.success('Saved as copy')},[saveAsCopy])
const handleDiscard=useCallback(async()=>{await discardResult()},[discardResult])
//Continue editing handler
const handleContinueEdit=useCallback(async()=>{const trimmed=editPrompt.trim();if(!trimmed)return;setShowEditInput(false);setEditPrompt('');await submitEdit(trimmed)},[editPrompt,submitEdit])
const handleEditKeyDown=useCallback((e:React.KeyboardEvent<HTMLInputElement>)=>{if(e.key==='Enter'){e.preventDefault();handleContinueEdit()}else if(e.key==='Escape'){setShowEditInput(false);setEditPrompt('')}},[handleContinueEdit])
if(!resultPath||!resultSrc||!loaded)return null
return(<>
{/* Controls panel - ALWAYS visible when loaded (not hidden during compare) */}
<div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2">
{/* Comparing indicator - shows above controls */}
{isComparing&&(<div className="text-[10px] text-neutral-900 dark:text-white bg-white/80 dark:bg-neutral-800/80 px-3 py-1 rounded-full backdrop-blur-xl select-none mb-1 border border-neutral-200 dark:border-neutral-700 font-medium tracking-wide shadow-sm">Viewing Original</div>)}
{/* Compare button - always accessible */}
<button ref={btnRef} onPointerDown={onPointerDown} onPointerUp={onPointerUp} onPointerCancel={onPointerCancel} onPointerLeave={onPointerLeave} onKeyDown={onKeyDown} onKeyUp={onKeyUp} className={cn("p-3 rounded-full backdrop-blur-xl transition-all focus:outline-none focus:ring-2 focus:ring-brand-500/30",isComparing?"bg-neutral-900/70 dark:bg-white/20 text-white scale-95 shadow-lg":"bg-neutral-900/50 dark:bg-neutral-800/70 text-white/90 hover:bg-neutral-900/70 dark:hover:bg-neutral-700/70 hover:scale-105 border border-neutral-700/50 dark:border-neutral-600/50 shadow-md")}><Eye className="w-4 h-4"/></button>
<span className="text-[10px] text-neutral-600 dark:text-neutral-400 select-none font-medium tracking-wide">{isComparing?'Release':'Hold to compare'}</span>
{/* Action toolbar - glass-pill matching main toolbar */}
<div className="flex items-center gap-0.5 px-1.5 py-1 rounded-full bg-neutral-900/70 dark:bg-neutral-800/80 backdrop-blur-xl shadow-float border border-neutral-700/30 dark:border-neutral-600/30">
<button onClick={handleKeep} disabled={isActionLoading} className="group flex items-center gap-1.5 px-3 py-2 rounded-full text-white/90 hover:bg-white/10 active:scale-95 transition-all disabled:opacity-40">{isActionLoading?<Loader2 className="w-3.5 h-3.5 animate-spin"/>:<Check className="w-3.5 h-3.5 group-hover:text-success transition-colors"/>}<span className="text-xs font-medium">Keep</span></button>
<button onClick={handleSave} disabled={isActionLoading} className="group flex items-center gap-1.5 px-3 py-2 rounded-full text-white/90 hover:bg-white/10 active:scale-95 transition-all disabled:opacity-40"><Copy className="w-3.5 h-3.5 group-hover:text-white transition-colors"/><span className="text-xs font-medium">Save Copy</span></button>
<button onClick={()=>setShowEditInput(!showEditInput)} disabled={isActionLoading} className={cn("group flex items-center gap-1.5 px-3 py-2 rounded-full active:scale-95 transition-all disabled:opacity-40",showEditInput?"bg-brand-500/20 text-brand-400":"text-white/90 hover:bg-white/10")}><Sparkles className={cn("w-3.5 h-3.5 transition-colors",showEditInput?"text-brand-400":"group-hover:text-brand-400")}/><span className="text-xs font-medium">Edit</span></button>
<div className="w-px h-5 bg-white/20 mx-0.5"/>
<button onClick={handleDiscard} disabled={isActionLoading} className="group flex items-center gap-1.5 px-3 py-2 rounded-full text-white/50 hover:bg-brand-500/10 hover:text-brand-400 active:scale-95 transition-all disabled:opacity-40"><X className="w-3.5 h-3.5 group-hover:text-brand-400 transition-colors"/><span className="text-xs font-medium">Discard</span></button>
</div>
{/* Continue editing input */}
{showEditInput&&(<div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-neutral-900/70 dark:bg-neutral-800/80 backdrop-blur-xl shadow-float border border-neutral-700/30 dark:border-neutral-600/30 mt-1 animate-in fade-in slide-in-from-bottom-2 duration-200">
<Sparkles className="w-3.5 h-3.5 text-brand-400 shrink-0"/>
<input ref={inputRef} type="text" value={editPrompt} onChange={e=>setEditPrompt(e.target.value)} onKeyDown={handleEditKeyDown} placeholder="Describe another edit..." className="bg-transparent text-white text-xs placeholder:text-neutral-400 outline-none w-48 font-medium"/>
<Button variant="ghost" size="icon" onClick={handleContinueEdit} disabled={!editPrompt.trim()} className="h-7 w-7 rounded-full text-brand-400 hover:bg-white/10 disabled:opacity-30"><Send className="w-3.5 h-3.5"/></Button>
</div>)}
</div>
</>)
}
