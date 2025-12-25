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
import{Trash2,Heart,LayoutGrid,Image as ImageIcon}from'lucide-react'
import{Tooltip,TooltipContent,TooltipTrigger}from'../ui/tooltip'
import{ImageGrid}from'./ImageGrid'
export function Workstation(){
const{currentBatch,selectedIndex,viewMode,setViewMode,setCurrentBatch,setSelectedIndex,removeFromUnsorted,addToUnsorted,isTrashView,setIsTrashView,bumpStatusVersion,browseMode,setBrowseMode}=useWorkstation()
const{activeBrand}=useBrand()
const hasImages=currentBatch.length>0
const currentImage=currentBatch[selectedIndex]
const isComparison=viewMode==='comparison'
const isKept=currentImage?.status==='kept'
const lastToastId=useRef<string|number|undefined>(undefined)
//Extract filename from path (use originalPath for kept images since path may be data URL)
const filename=useMemo(()=>{const p=currentImage?.originalPath||currentImage?.path;if(!p||p.startsWith('data:'))return'';const parts=p.split('/');return parts[parts.length-1]||''},[currentImage?.originalPath,currentImage?.path])
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
//Toggle browse mode (preview/grid)
const isGrid=browseMode==='grid'
const toggleBrowseMode=useCallback(()=>{setBrowseMode(isGrid?'preview':'grid')},[isGrid,setBrowseMode])
//Remove current image from batch and advance to next
const removeCurrentAndAdvance=useCallback(()=>{const newBatch=[...currentBatch];newBatch.splice(selectedIndex,1);setCurrentBatch(newBatch);if(selectedIndex>=newBatch.length&&newBatch.length>0)setSelectedIndex(newBatch.length-1)},[currentBatch,selectedIndex,setCurrentBatch,setSelectedIndex])
//Undo keep action - restore to unsorted and add back to batch
const undoKeep=useCallback(async(image:GeneratedImage)=>{if(!activeBrand)return;try{const updated=await bridge.unkeepImage(image.id,activeBrand);const restored={...image,path:updated.currentPath,prompt:updated.prompt??image.prompt,sourceTemplatePath:updated.sourceTemplatePath??image.sourceTemplatePath,timestamp:updated.timestamp||image.timestamp};addToUnsorted([restored]);setCurrentBatch([restored,...currentBatch]);setSelectedIndex(0);bumpStatusVersion();toast.success('Image restored to unsorted')}catch(e){console.error('Failed to undo keep:',e);toast.error('Failed to undo')}},[activeBrand,addToUnsorted,bumpStatusVersion,currentBatch,setCurrentBatch,setSelectedIndex])
//Undo trash action - restore to unsorted and add back to batch
const undoTrash=useCallback(async(image:GeneratedImage)=>{if(!activeBrand)return;try{const updated=await bridge.restoreImage(image.id,activeBrand);const restored={...image,path:updated.currentPath,prompt:updated.prompt??image.prompt,sourceTemplatePath:updated.sourceTemplatePath??image.sourceTemplatePath,timestamp:updated.timestamp||image.timestamp};addToUnsorted([restored]);setCurrentBatch([restored,...currentBatch]);setSelectedIndex(0);bumpStatusVersion();toast.success('Image restored to unsorted')}catch(e){console.error('Failed to undo trash:',e);toast.error('Failed to undo')}},[activeBrand,addToUnsorted,bumpStatusVersion,currentBatch,setCurrentBatch,setSelectedIndex])
//Handle swipe right (keep) - skip if already kept
const handleKeep=useCallback(async()=>{if(!currentImage||!activeBrand||currentImage.status==='kept')return;const img={...currentImage};try{await bridge.markImageKept(currentImage.id,activeBrand);removeFromUnsorted(currentImage.id);removeCurrentAndAdvance();bumpStatusVersion();if(lastToastId.current)toast.dismiss(lastToastId.current);lastToastId.current=toast('Image moved to Kept',{action:{label:'Undo',onClick:()=>undoKeep(img)}})}catch(e){console.error('Failed to mark image as kept:',e)}},[currentImage,activeBrand,removeFromUnsorted,removeCurrentAndAdvance,bumpStatusVersion,undoKeep])
//Handle swipe left (trash) - use trashByPath for project assets (have originalPath)
const handleTrash=useCallback(async()=>{
if(!currentImage){console.error('handleTrash: no currentImage');return}
if(!activeBrand){console.error('handleTrash: no activeBrand');return}
const img={...currentImage};try{
//Project assets have originalPath; use path-based trash for them
console.log('handleTrash:',{id:currentImage.id,status:currentImage.status,originalPath:currentImage.originalPath})
if(currentImage.originalPath&&currentImage.status==='kept'){
console.log('Using trashByPath for project asset');
await bridge.trashByPath(currentImage.originalPath,activeBrand)
}else{await bridge.markImageTrashed(currentImage.id,activeBrand)}
removeFromUnsorted(currentImage.id);removeCurrentAndAdvance();bumpStatusVersion();if(lastToastId.current)toast.dismiss(lastToastId.current);lastToastId.current=toast('Image moved to Trash',{action:{label:'Undo',onClick:()=>undoTrash(img)}})}catch(e){console.error('Failed to trash image:',e);toast.error('Failed to trash image')}},[currentImage,activeBrand,removeFromUnsorted,removeCurrentAndAdvance,bumpStatusVersion,undoTrash])
//Keyboard shortcuts: K=keep (only for unsorted), T=trash, Left/Right=navigate, G=toggle grid
useEffect(()=>{const handleKeyDown=(e:KeyboardEvent)=>{
//Ignore if typing in input/textarea
if(e.target instanceof HTMLInputElement||e.target instanceof HTMLTextAreaElement)return
if(isTrashView||!hasImages)return
//G toggles browse mode (works in both comparison and normal view)
if(e.key==='g'||e.key==='G'){e.preventDefault();toggleBrowseMode();return}
if(isComparison||isGrid)return
if((e.key==='k'||e.key==='K')&&!isKept){e.preventDefault();handleKeep()}
else if(e.key==='t'||e.key==='T'){e.preventDefault();handleTrash()}
else if(e.key==='ArrowLeft'&&selectedIndex>0){e.preventDefault();setSelectedIndex(selectedIndex-1)}
else if(e.key==='ArrowRight'&&selectedIndex<currentBatch.length-1){e.preventDefault();setSelectedIndex(selectedIndex+1)}}
window.addEventListener('keydown',handleKeyDown)
return()=>window.removeEventListener('keydown',handleKeyDown)},[isTrashView,hasImages,isComparison,isGrid,isKept,handleKeep,handleTrash,selectedIndex,currentBatch.length,setSelectedIndex,toggleBrowseMode])
//Show trash view
if(isTrashView)return(<div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-secondary/20 dark:bg-secondary/10"><TrashView onExit={handleExitTrash}/></div>)
return(<div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-gradient-to-b from-background to-muted/20">{hasImages?(<>{/* Clean header toolbar */}<div className="flex items-center h-12 px-4 border-b border-border/30 bg-background/80 backdrop-blur-sm">{/* Left: Export actions */}<div className="flex items-center"><ExportActions/></div>{/* Center: Filename and counter */}<div className="flex-1 flex flex-col items-center justify-center mx-4"><span className="text-sm font-medium text-foreground/90 max-w-md truncate" title={filename}>{filename||'Untitled'}</span><span className="text-xs text-muted-foreground">{imageCounter}</span></div>{/* Right: Action buttons */}<div className="flex items-center gap-2">{!isKept&&(<Tooltip><TooltipTrigger asChild><Button variant="ghost" size="sm" onClick={handleKeep} disabled={!currentImage} className="h-8 px-3 gap-1.5 text-xs font-medium hover:bg-emerald-500/10 hover:text-emerald-600 transition-colors"><Heart className="w-4 h-4"/>Keep</Button></TooltipTrigger><TooltipContent side="bottom"><p>Keep image (K)</p></TooltipContent></Tooltip>)}<Tooltip><TooltipTrigger asChild><Button variant="ghost" size="sm" onClick={handleTrash} disabled={!currentImage} className="h-8 px-3 gap-1.5 text-xs font-medium hover:bg-red-500/10 hover:text-red-600 transition-colors"><Trash2 className="w-4 h-4"/>Trash</Button></TooltipTrigger><TooltipContent side="bottom"><p>Move to trash (T)</p></TooltipContent></Tooltip><div className="w-px h-5 bg-border/50 mx-1"/><Tooltip><TooltipTrigger asChild><Button variant={isComparison?'secondary':'ghost'} size="sm" onClick={toggleComparison} className="h-8 px-3 gap-1.5 text-xs font-medium"><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"/></svg>Compare</Button></TooltipTrigger><TooltipContent side="bottom"><p>{isComparison?'Exit comparison':'Compare images'}</p></TooltipContent></Tooltip><Tooltip><TooltipTrigger asChild><Button variant={isGrid?'secondary':'ghost'} size="sm" onClick={toggleBrowseMode} className="h-8 px-3 gap-1.5 text-xs font-medium">{isGrid?<ImageIcon className="w-4 h-4"/>:<LayoutGrid className="w-4 h-4"/>}{isGrid?'Preview':'Grid'}</Button></TooltipTrigger><TooltipContent side="bottom"><p>{isGrid?'Switch to preview (G)':'Switch to grid view (G)'}</p></TooltipContent></Tooltip></div></div>{/* Main content: comparison, grid, or preview */}<div className="relative flex-1 overflow-hidden">{isComparison?(<ComparisonView/>):isGrid?(<ImageGrid/>):(<SwipeContainer onSwipeRight={handleKeep} onSwipeLeft={handleTrash} disabled={!currentImage||isKept} mode="curate"><ImageDisplay/></SwipeContainer>)}{!isGrid&&<ContextPanel/>}</div>{!isGrid&&<ThumbnailStrip/>}</>):(<EmptyState/>)}</div>)}
