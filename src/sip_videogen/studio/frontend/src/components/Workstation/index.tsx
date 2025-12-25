//Workstation component - image review and curation workspace
import{useCallback,useRef,useEffect,useMemo}from'react'
import{useWorkstation,type GeneratedImage}from'../../context/WorkstationContext'
import{useBrand}from'../../context/BrandContext'
import{bridge,waitForPyWebViewReady,type ImageStatusEntry}from'../../lib/bridge'
import{toast}from'../ui/toaster'
import{ImageDisplay}from'./ImageDisplay'
import{ThumbnailStrip}from'./ThumbnailStrip'
import{SwipeContainer}from'./SwipeContainer'
import{EmptyState}from'./EmptyState'
import{ComparisonView}from'./ComparisonView'
import{ContextPanel}from'./ContextPanel'
import{ExportActions}from'./ExportActions'
import{TrashView}from'./TrashView'
import{Button}from'../ui/button'
import{Trash2,Heart}from'lucide-react'
import{Tooltip,TooltipContent,TooltipTrigger}from'../ui/tooltip'
export function Workstation(){
const{currentBatch,selectedIndex,viewMode,setViewMode,setCurrentBatch,setSelectedIndex,removeFromUnsorted,addToUnsorted,isTrashView,setIsTrashView,bumpStatusVersion}=useWorkstation()
const{activeBrand}=useBrand()
const hasImages=currentBatch.length>0
const currentImage=currentBatch[selectedIndex]
const isComparison=viewMode==='comparison'
const lastToastId=useRef<string|number|undefined>(undefined)
//Extract filename from path
const filename=useMemo(()=>{if(!currentImage?.path)return'';const parts=currentImage.path.split('/');return parts[parts.length-1]||''},[currentImage?.path])
const imageCounter=`${selectedIndex+1} of ${currentBatch.length}`
//Load unsorted backlog on brand change
useEffect(()=>{let cancelled=false
async function loadUnsorted(){if(!activeBrand){setCurrentBatch([]);setIsTrashView(false);return}
const ready=await waitForPyWebViewReady()
if(!ready||cancelled)return
try{const images=await bridge.getUnsortedImages(activeBrand);if(cancelled)return
const batch=images.map((img:ImageStatusEntry)=>({id:img.id,path:img.currentPath,prompt:img.prompt||undefined,sourceTemplatePath:img.sourceTemplatePath||undefined,timestamp:img.timestamp}))
setCurrentBatch(batch)
}catch(e){console.error('Failed to load unsorted images:',e)}}
loadUnsorted()
return()=>{cancelled=true}},[activeBrand,setCurrentBatch,setIsTrashView])
//Exit trash view
const handleExitTrash=useCallback(()=>{setIsTrashView(false);setCurrentBatch([])},[setIsTrashView,setCurrentBatch])
//Toggle comparison view
const toggleComparison=useCallback(()=>{setViewMode(isComparison?'single':'comparison')},[isComparison,setViewMode])
//Remove current image from batch and advance to next
const removeCurrentAndAdvance=useCallback(()=>{const newBatch=[...currentBatch];newBatch.splice(selectedIndex,1);setCurrentBatch(newBatch);if(selectedIndex>=newBatch.length&&newBatch.length>0)setSelectedIndex(newBatch.length-1)},[currentBatch,selectedIndex,setCurrentBatch,setSelectedIndex])
//Undo keep action - restore to unsorted and add back to batch
const undoKeep=useCallback(async(image:GeneratedImage)=>{if(!activeBrand)return;try{const updated=await bridge.unkeepImage(image.id,activeBrand);const restored={...image,path:updated.currentPath,prompt:updated.prompt??image.prompt,sourceTemplatePath:updated.sourceTemplatePath??image.sourceTemplatePath,timestamp:updated.timestamp||image.timestamp};addToUnsorted([restored]);setCurrentBatch([restored,...currentBatch]);setSelectedIndex(0);bumpStatusVersion();toast.success('Image restored to unsorted')}catch(e){console.error('Failed to undo keep:',e);toast.error('Failed to undo')}},[activeBrand,addToUnsorted,bumpStatusVersion,currentBatch,setCurrentBatch,setSelectedIndex])
//Undo trash action - restore to unsorted and add back to batch
const undoTrash=useCallback(async(image:GeneratedImage)=>{if(!activeBrand)return;try{const updated=await bridge.restoreImage(image.id,activeBrand);const restored={...image,path:updated.currentPath,prompt:updated.prompt??image.prompt,sourceTemplatePath:updated.sourceTemplatePath??image.sourceTemplatePath,timestamp:updated.timestamp||image.timestamp};addToUnsorted([restored]);setCurrentBatch([restored,...currentBatch]);setSelectedIndex(0);bumpStatusVersion();toast.success('Image restored to unsorted')}catch(e){console.error('Failed to undo trash:',e);toast.error('Failed to undo')}},[activeBrand,addToUnsorted,bumpStatusVersion,currentBatch,setCurrentBatch,setSelectedIndex])
//Handle swipe right (keep)
const handleKeep=useCallback(async()=>{if(!currentImage||!activeBrand)return;const img={...currentImage};try{await bridge.markImageKept(currentImage.id,activeBrand);removeFromUnsorted(currentImage.id);removeCurrentAndAdvance();bumpStatusVersion();if(lastToastId.current)toast.dismiss(lastToastId.current);lastToastId.current=toast('Image moved to Kept',{action:{label:'Undo',onClick:()=>undoKeep(img)}})}catch(e){console.error('Failed to mark image as kept:',e)}},[currentImage,activeBrand,removeFromUnsorted,removeCurrentAndAdvance,bumpStatusVersion,undoKeep])
//Handle swipe left (trash)
const handleTrash=useCallback(async()=>{if(!currentImage||!activeBrand)return;const img={...currentImage};try{await bridge.markImageTrashed(currentImage.id,activeBrand);removeFromUnsorted(currentImage.id);removeCurrentAndAdvance();bumpStatusVersion();if(lastToastId.current)toast.dismiss(lastToastId.current);lastToastId.current=toast('Image moved to Trash',{action:{label:'Undo',onClick:()=>undoTrash(img)}})}catch(e){console.error('Failed to trash image:',e)}},[currentImage,activeBrand,removeFromUnsorted,removeCurrentAndAdvance,bumpStatusVersion,undoTrash])
//Keyboard shortcuts: K=keep, T=trash, Left/Right=navigate
useEffect(()=>{const handleKeyDown=(e:KeyboardEvent)=>{
//Ignore if typing in input/textarea
if(e.target instanceof HTMLInputElement||e.target instanceof HTMLTextAreaElement)return
if(isTrashView||!hasImages||isComparison)return
if(e.key==='k'||e.key==='K'){e.preventDefault();handleKeep()}
else if(e.key==='t'||e.key==='T'){e.preventDefault();handleTrash()}
else if(e.key==='ArrowLeft'&&selectedIndex>0){e.preventDefault();setSelectedIndex(selectedIndex-1)}
else if(e.key==='ArrowRight'&&selectedIndex<currentBatch.length-1){e.preventDefault();setSelectedIndex(selectedIndex+1)}}
window.addEventListener('keydown',handleKeyDown)
return()=>window.removeEventListener('keydown',handleKeyDown)},[isTrashView,hasImages,isComparison,handleKeep,handleTrash,selectedIndex,currentBatch.length,setSelectedIndex])
//Show trash view
if(isTrashView)return(<div className="flex-1 flex flex-col bg-secondary/20 dark:bg-secondary/10"><TrashView onExit={handleExitTrash}/></div>)
return(<div className="flex-1 flex flex-col bg-secondary/20 dark:bg-secondary/10">{hasImages?(<>{/* Header with export actions, image info, curation buttons, and compare toggle */}<div className="flex items-center justify-between px-4 py-2 border-b border-border/50"><ExportActions/>{/* Center: Image info and curation buttons */}<div className="flex items-center gap-3">{/* Filename and counter */}<div className="flex flex-col items-center min-w-0"><span className="text-xs font-medium text-foreground/80 truncate max-w-[200px]" title={filename}>{filename}</span><span className="text-[10px] text-muted-foreground">{imageCounter}</span></div>{/* Curation buttons */}<div className="flex items-center gap-1.5 ml-2"><Tooltip><TooltipTrigger asChild><Button variant="ghost" size="sm" onClick={handleTrash} disabled={!currentImage} className="h-8 px-3 gap-1.5 text-xs hover:bg-red-500/10 hover:text-red-500 border border-transparent hover:border-red-500/30"><Trash2 className="w-3.5 h-3.5"/>Trash</Button></TooltipTrigger><TooltipContent side="bottom"><p>Move to trash (swipe left or press T)</p></TooltipContent></Tooltip><Tooltip><TooltipTrigger asChild><Button variant="ghost" size="sm" onClick={handleKeep} disabled={!currentImage} className="h-8 px-3 gap-1.5 text-xs hover:bg-green-500/10 hover:text-green-500 border border-transparent hover:border-green-500/30"><Heart className="w-3.5 h-3.5"/>Keep</Button></TooltipTrigger><TooltipContent side="bottom"><p>Keep image (swipe right or press K)</p></TooltipContent></Tooltip></div></div><Button variant={isComparison?'secondary':'ghost'} size="sm" onClick={toggleComparison} className="gap-1.5 text-xs"><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"/></svg>{isComparison?'Single View':'Compare'}</Button></div>{/* Main content: comparison or swipe view */}<div className="relative flex-1 overflow-hidden">{isComparison?(<ComparisonView/>):(<SwipeContainer onSwipeRight={handleKeep} onSwipeLeft={handleTrash} disabled={!currentImage}><ImageDisplay/></SwipeContainer>)}<ContextPanel/></div><ThumbnailStrip/></>):(<EmptyState/>)}</div>)}
