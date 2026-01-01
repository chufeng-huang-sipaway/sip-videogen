//MediaDisplay component - displays images or videos with unified interface
import{useState,useEffect,useCallback}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import{useQuickEdit}from'../../context/QuickEditContext'
import{bridge,isPyWebView}from'../../lib/bridge'
import{getMediaType}from'../../lib/mediaUtils'
import{ImageDisplay}from'./ImageDisplay'
import{Loader2,ChevronLeft,ChevronRight,FolderOpen,Play}from'lucide-react'
import{cn}from'@/lib/utils'
export function MediaDisplay(){
const{currentBatch,selectedIndex,setSelectedIndex}=useWorkstation()
const{isGenerating}=useQuickEdit()
const curr=currentBatch[selectedIndex]
const isVideo=curr?getMediaType(curr)==='video':false
const[videoSrc,setVideoSrc]=useState<string|null>(null)
const[loading,setLoading]=useState(false)
const[error,setError]=useState<string|null>(null)
const[hovered,setHovered]=useState(false)
const canPrev=selectedIndex>0,canNext=selectedIndex<currentBatch.length-1
const goPrev=useCallback(()=>{if(canPrev&&!isGenerating)setSelectedIndex(selectedIndex-1)},[canPrev,selectedIndex,setSelectedIndex,isGenerating])
const goNext=useCallback(()=>{if(canNext&&!isGenerating)setSelectedIndex(selectedIndex+1)},[canNext,selectedIndex,setSelectedIndex,isGenerating])
//Load video source when current item is a video
useEffect(()=>{
if(!curr||!isVideo){setVideoSrc(null);setError(null);return}
let cancelled=false
async function loadVideo(){
setLoading(true);setError(null);setVideoSrc(null)
const path=curr.originalPath||curr.path
if(!path){setLoading(false);setError('Missing video path');return}
if(!isPyWebView()){setLoading(false);setError('Video playback requires app');return}
try{
const fileUrl=await bridge.getVideoPath(path)
if(cancelled)return
setVideoSrc(fileUrl)
}catch(e){
if(!cancelled)setError(e instanceof Error?e.message:'Video unavailable')
}finally{if(!cancelled)setLoading(false)}}
loadVideo()
return()=>{cancelled=true}},[curr?.id,curr?.originalPath,curr?.path,isVideo])
const openInFinder=useCallback(()=>{
const path=curr?.originalPath||curr?.path
if(path)bridge.openAssetInFinder(path).catch(console.warn)},[curr?.originalPath,curr?.path])
if(!curr)return null
//Render ImageDisplay for images
if(!isVideo)return<ImageDisplay/>
//Render video player
const navBtnClass="absolute top-1/2 -translate-y-1/2 z-20 p-2 rounded-full bg-black/50 text-white/90 backdrop-blur-sm transition-all hover:bg-black/70 hover:scale-110 disabled:opacity-30 disabled:pointer-events-none"
return(<div className="w-full h-full flex items-center justify-center relative" onMouseEnter={()=>setHovered(true)} onMouseLeave={()=>setHovered(false)}>
<div className="flex items-center justify-center overflow-hidden" style={{maxWidth:'calc(100% - 120px)',maxHeight:'calc(100% - 40px)'}}>
<div className="relative max-w-full max-h-full flex items-center justify-center">
{loading&&(<div className="flex flex-col items-center gap-2 text-muted-foreground"><Loader2 className="w-8 h-8 animate-spin"/><span className="text-sm">Loading video...</span></div>)}
{!loading&&error&&(<div className="flex flex-col items-center gap-3 p-6 bg-black/5 dark:bg-white/5 rounded-xl">
<Play className="w-12 h-12 text-muted-foreground/50"/>
<span className="text-sm text-muted-foreground">{error}</span>
<button onClick={openInFinder} className="flex items-center gap-2 px-3 py-1.5 text-xs bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors">
<FolderOpen className="w-3.5 h-3.5"/>Open in Finder</button></div>)}
{!loading&&!error&&videoSrc&&(<video controls autoPlay className="max-w-full max-h-full rounded-lg shadow-lg" src={videoSrc} onError={()=>setError('Playback failed')}/>)}
</div></div>
{/* Navigation buttons */}
<button onClick={goPrev} disabled={!canPrev||isGenerating} className={cn(navBtnClass,"left-2 transition-opacity duration-200",hovered?"opacity-100":"opacity-0")}><ChevronLeft className="w-6 h-6"/></button>
<button onClick={goNext} disabled={!canNext||isGenerating} className={cn(navBtnClass,"right-2 transition-opacity duration-200",hovered?"opacity-100":"opacity-0")}><ChevronRight className="w-6 h-6"/></button>
</div>)}
