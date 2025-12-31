//IdeasGalleryView - Main container for reviewing AI-generated inspirations
import{useState,useEffect,useCallback,useRef}from'react'
import{useInspirationContext}from'@/context/InspirationContext'
import{useGalleryMode}from'@/context/GalleryModeContext'
import{useBrand}from'@/context/BrandContext'
import{IdeasImageDisplay}from'./IdeasImageDisplay'
import{IdeasThumbnailStrip}from'./IdeasThumbnailStrip'
import{IdeasActionBar}from'./IdeasActionBar'
import{Button}from'@/components/ui/button'
import{Sparkles,Loader2}from'lucide-react'
interface SelectionState{inspirationId:string|null;imageIndex:number}
export function IdeasGalleryView(){
const{inspirations,isGenerating,progress,triggerGeneration,markViewed,dismiss,viewedIds}=useInspirationContext()
const{contentMode,setContentMode}=useGalleryMode()
const{activeBrand}=useBrand()
const[selection,setSelection]=useState<SelectionState>({inspirationId:null,imageIndex:0})
const selectionRef=useRef<SelectionState>(selection)
selectionRef.current=selection
//Filter to ready inspirations with at least one ready image
const readyInspirations=inspirations.filter(i=>i.status==='ready'&&i.images.some(img=>img.status==='ready'&&img.path))
const currentIndex=readyInspirations.findIndex(i=>i.id===selection.inspirationId)
const currentInspiration=currentIndex>=0?readyInspirations[currentIndex]:null
const readyImages=currentInspiration?.images.filter(img=>img.status==='ready'&&img.path)||[]
//Initialize selection when inspirations change
useEffect(()=>{
if(!selection.inspirationId&&readyInspirations.length>0){
setSelection({inspirationId:readyInspirations[0].id,imageIndex:0})
}else if(selection.inspirationId&&!readyInspirations.find(i=>i.id===selection.inspirationId)){
//Selected inspiration no longer exists (dismissed), pick next
const prevIdx=readyInspirations.findIndex(i=>i.id===selection.inspirationId)
if(readyInspirations.length>0){
const newIdx=Math.min(prevIdx,readyInspirations.length-1)
setSelection({inspirationId:readyInspirations[Math.max(0,newIdx)]?.id||null,imageIndex:0})
}else{setSelection({inspirationId:null,imageIndex:0})}
}
},[readyInspirations.length,selection.inspirationId])
//Reset selection on brand change
useEffect(()=>{setSelection({inspirationId:null,imageIndex:0})},[activeBrand])
//Mark as viewed when displayed
useEffect(()=>{
if(contentMode!=='ideas'||!currentInspiration)return
if(!viewedIds.has(currentInspiration.id)){markViewed(currentInspiration.id)}
},[contentMode,currentInspiration?.id,viewedIds,markViewed])
//Clamp image index
useEffect(()=>{
if(selection.imageIndex>=readyImages.length&&readyImages.length>0){
setSelection(prev=>({...prev,imageIndex:Math.max(0,readyImages.length-1)}))
}
},[selection.imageIndex,readyImages.length])
//Navigation callbacks
const goNextImage=useCallback(()=>{
if(selection.imageIndex<readyImages.length-1)setSelection(prev=>({...prev,imageIndex:prev.imageIndex+1}))
},[selection.imageIndex,readyImages.length])
const goPrevImage=useCallback(()=>{
if(selection.imageIndex>0)setSelection(prev=>({...prev,imageIndex:prev.imageIndex-1}))
},[selection.imageIndex])
const goNextInspiration=useCallback(()=>{
if(currentIndex<readyInspirations.length-1){
setSelection({inspirationId:readyInspirations[currentIndex+1].id,imageIndex:0})
}
},[currentIndex,readyInspirations])
const goPrevInspiration=useCallback(()=>{
if(currentIndex>0){
setSelection({inspirationId:readyInspirations[currentIndex-1].id,imageIndex:0})
}
},[currentIndex,readyInspirations])
const selectImage=useCallback((idx:number)=>{setSelection(prev=>({...prev,imageIndex:idx}))},[])
//Dismiss handler with auto-advance
const handleDismiss=useCallback(async()=>{
if(!currentInspiration)return
const dismissIdx=currentIndex
await dismiss(currentInspiration.id)
//After dismiss: same index -> prev index -> first -> empty
const remaining=readyInspirations.filter(i=>i.id!==currentInspiration.id)
if(remaining.length===0){
setSelection({inspirationId:null,imageIndex:0})
setContentMode('assets')//Auto-switch when last dismissed
}else{
const newIdx=Math.min(dismissIdx,remaining.length-1)
setSelection({inspirationId:remaining[newIdx].id,imageIndex:0})
}
},[currentInspiration,currentIndex,dismiss,readyInspirations,setContentMode])
//Keyboard navigation (only when Ideas mode is active)
useEffect(()=>{
const handleKeyDown=(e:KeyboardEvent)=>{
if(contentMode!=='ideas')return
if(e.target instanceof HTMLInputElement||e.target instanceof HTMLTextAreaElement)return
if(e.key==='ArrowLeft'){e.preventDefault();goPrevImage()}
else if(e.key==='ArrowRight'){e.preventDefault();goNextImage()}
else if(e.key==='ArrowUp'){e.preventDefault();goPrevInspiration()}
else if(e.key==='ArrowDown'){e.preventDefault();goNextInspiration()}
else if((e.key==='d'||e.key==='D'||e.key==='Delete')&&currentInspiration){e.preventDefault();handleDismiss()}
}
window.addEventListener('keydown',handleKeyDown)
return()=>window.removeEventListener('keydown',handleKeyDown)
},[contentMode,goPrevImage,goNextImage,goPrevInspiration,goNextInspiration,handleDismiss,currentInspiration])
//Empty states
if(!activeBrand){
return(<div className="flex-1 flex flex-col items-center justify-center gap-4 text-muted-foreground">
<Sparkles className="w-12 h-12 opacity-30"/>
<p className="text-sm">Select a brand to view ideas</p>
</div>)
}
if(readyInspirations.length===0){
return(<div className="flex-1 flex flex-col items-center justify-center gap-4">
{isGenerating?(
<><Loader2 className="w-10 h-10 animate-spin text-brand-500"/>
<p className="text-sm text-muted-foreground">Generating ideas... {Math.round(progress*100)}%</p></>
):(
<><Sparkles className="w-12 h-12 text-muted-foreground/30"/>
<p className="text-sm text-muted-foreground">No ideas yet</p>
<Button variant="default" size="lg" onClick={triggerGeneration} className="gap-2">
<Sparkles className="w-4 h-4"/>Generate Ideas
</Button></>
)}
</div>)
}
const currentImg=readyImages[selection.imageIndex]||null
return(<div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
{/* Main image display area */}
<div className="relative flex-1 overflow-hidden pt-8 pb-40 flex flex-col items-center justify-center">
<div className="w-full h-full flex items-center justify-center max-w-5xl mx-auto">
<div className="absolute inset-0 flex items-center justify-center">
<IdeasImageDisplay
inspiration={currentInspiration!}
image={currentImg}
imageIndex={selection.imageIndex}
totalImages={readyImages.length}
onPrevImage={goPrevImage}
onNextImage={goNextImage}
canPrev={selection.imageIndex>0}
canNext={selection.imageIndex<readyImages.length-1}
/>
</div>
</div>
</div>
{/* Bottom controls */}
<div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-3 w-full max-w-5xl px-12">
{/* Counter badge */}
<div className="bg-black/5 dark:bg-white/5 backdrop-blur-md px-3 py-1 rounded-full border border-black/5 dark:border-white/5 shadow-sm">
<span className="text-[10px] font-mono font-medium text-muted-foreground tracking-widest uppercase">
{currentIndex+1} of {readyInspirations.length}
</span>
</div>
{/* Thumbnail strip */}
<div className="glass-pill p-1.5 shadow-float bg-white/40 dark:bg-black/40 backdrop-blur-xl border-white/20 dark:border-white/5 ring-1 ring-white/20 max-w-full">
<IdeasThumbnailStrip
inspirations={readyInspirations}
currentInspirationId={selection.inspirationId}
currentImageIndex={selection.imageIndex}
onSelectImage={selectImage}
onPrevInspiration={goPrevInspiration}
onNextInspiration={goNextInspiration}
canPrevInspiration={currentIndex>0}
canNextInspiration={currentIndex<readyInspirations.length-1}
/>
</div>
{/* Action bar */}
<IdeasActionBar
inspiration={currentInspiration!}
imageIndex={selection.imageIndex}
onDismiss={handleDismiss}
isGenerating={isGenerating}
/>
</div>
</div>)
}
