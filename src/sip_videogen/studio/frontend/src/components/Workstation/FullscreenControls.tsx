//FullscreenControls - auto-hide overlay with navigation and zoom display
import{useState,useEffect,useRef,useCallback}from'react'
import{useViewer}from'../../context/ViewerContext'
import{useWorkstation}from'../../context/WorkstationContext'
import{X,ChevronLeft,ChevronRight}from'lucide-react'
import{cn}from'@/lib/utils'
const HIDE_DELAY_MS=2000
export function FullscreenControls(){
const{toggleFullscreen,getDisplayPercent}=useViewer()
const{selectedIndex,setSelectedIndex,currentBatch}=useWorkstation()
const[showControls,setShowControls]=useState(true)
const hideTimerRef=useRef<number|null>(null)
const scheduleHide=useCallback(()=>{if(hideTimerRef.current)clearTimeout(hideTimerRef.current);hideTimerRef.current=window.setTimeout(()=>setShowControls(false),HIDE_DELAY_MS)},[])
const handlePointerMove=useCallback(()=>{setShowControls(true);scheduleHide()},[scheduleHide])
useEffect(()=>{scheduleHide();return()=>{if(hideTimerRef.current)clearTimeout(hideTimerRef.current)}},[scheduleHide])
const canPrev=selectedIndex>0,canNext=selectedIndex<currentBatch.length-1
const btnClass="p-2 rounded-full bg-black/50 text-white hover:bg-black/70 disabled:opacity-30 disabled:pointer-events-none"
return(<div className="absolute inset-0 z-10" onPointerMove={handlePointerMove} style={{pointerEvents:'auto'}}>
<div className={cn("transition-opacity duration-300",showControls?"opacity-100":"opacity-0 pointer-events-none")}>
<button onClick={toggleFullscreen} className={cn(btnClass,"absolute top-4 right-4")}><X className="w-5 h-5"/></button>
<button onClick={()=>canPrev&&setSelectedIndex(selectedIndex-1)} disabled={!canPrev} className={cn(btnClass,"absolute left-4 top-1/2 -translate-y-1/2")}><ChevronLeft className="w-6 h-6"/></button>
<button onClick={()=>canNext&&setSelectedIndex(selectedIndex+1)} disabled={!canNext} className={cn(btnClass,"absolute right-4 top-1/2 -translate-y-1/2")}><ChevronRight className="w-6 h-6"/></button>
<div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-black/50 px-3 py-1 rounded-full text-white text-sm">{getDisplayPercent()}%</div>
</div>
</div>)
}
