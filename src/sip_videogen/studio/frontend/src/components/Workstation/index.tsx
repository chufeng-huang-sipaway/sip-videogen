//Workstation component - image viewer workspace
import{useCallback,useRef,useEffect,useMemo,useState}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import{useBrand}from'../../context/BrandContext'
import{QuickEditProvider,useQuickEdit}from'../../context/QuickEditContext'
import{bridge,isPyWebView,waitForPyWebViewReady}from'../../lib/bridge'
import{toast}from'../ui/toaster'
import{ImageDisplay}from'./ImageDisplay'
import{ThumbnailStrip}from'./ThumbnailStrip'
import{EmptyState}from'./EmptyState'
import{ContextPanel}from'./ContextPanel'
import{ExportActions}from'./ExportActions'
import{QuickEditButton}from'./QuickEditButton'
import{Button}from'../ui/button'
import{Trash2,LayoutGrid,Image as ImageIcon}from'lucide-react'
import{Tooltip,TooltipContent,TooltipTrigger}from'../ui/tooltip'
import{ImageGrid}from'./ImageGrid'
import{cn}from'@/lib/utils'
import{clearAllCaches}from'../../lib/thumbnailCache'

//Inner content that can access QuickEditContext
function WorkstationContent(){
const{currentBatch,selectedIndex,setCurrentBatch,setSelectedIndex,bumpStatusVersion,browseMode,setBrowseMode,removeFromBatchByPath,markAsViewed}=useWorkstation()
const{activeBrand}=useBrand()
const{resultPath,isGenerating}=useQuickEdit()
const hasImages=currentBatch.length>0
const currentImage=currentBatch[selectedIndex]
const[toolbarVisible,setToolbarVisible]=useState(true)
const hideTimeoutRef=useRef<ReturnType<typeof setTimeout>|null>(null)
const handleMouseMove=useCallback(()=>{setToolbarVisible(true);if(hideTimeoutRef.current)clearTimeout(hideTimeoutRef.current);hideTimeoutRef.current=setTimeout(()=>setToolbarVisible(false),2500)},[])
const handleMouseLeave=useCallback(()=>{if(hideTimeoutRef.current)clearTimeout(hideTimeoutRef.current);hideTimeoutRef.current=setTimeout(()=>setToolbarVisible(false),800)},[])
const filename=useMemo(()=>{if(!currentImage)return'';const p=currentImage.originalPath||currentImage.path;if(!p||p.startsWith('data:'))return'';return p.split('/').pop()||''},[currentImage])
const imageCounter=`${selectedIndex+1} / ${currentBatch.length}`
//Hide toolbar when Quick Edit result is showing
const showOriginalToolbar=!resultPath&&!isGenerating
//Load images on brand change
useEffect(()=>{clearAllCaches();let cancelled=false;async function loadImages(){if(!activeBrand){setCurrentBatch([]);return}const ready=await waitForPyWebViewReady();if(!ready||cancelled)return;try{const images=await bridge.getUnsortedImages(activeBrand);if(cancelled)return;const batch=images.map((img)=>({id:img.id,path:img.currentPath,originalPath:img.originalPath,prompt:img.prompt??undefined,sourceTemplatePath:img.sourceTemplatePath??undefined,timestamp:img.timestamp,viewedAt:img.viewedAt??null}));setCurrentBatch(batch)}catch(e){console.error('Failed to load images:',e)}}loadImages();return()=>{cancelled=true}},[activeBrand,setCurrentBatch])
//Mark image as viewed
useEffect(()=>{if(!currentImage||!activeBrand||!isPyWebView())return;if(currentImage.viewedAt!==null)return;const now=new Date().toISOString();markAsViewed(currentImage.id,now);bridge.markImageViewed(currentImage.id,activeBrand).catch(e=>console.error('Failed to mark viewed:',e))},[currentImage?.id,currentImage?.viewedAt,activeBrand,markAsViewed])
const isGrid=browseMode==='grid'
const toggleBrowseMode=useCallback(()=>{setBrowseMode(isGrid?'preview':'grid')},[isGrid,setBrowseMode])
const handleDelete=useCallback(async()=>{if(!currentImage)return;const path=currentImage.originalPath||currentImage.path;if(!path||path.startsWith('data:')){toast.error('Cannot delete this image');return}removeFromBatchByPath(path);try{await bridge.deleteAsset(path);toast.success('Moved to Trash')}catch(e){console.warn('Delete failed:',e)}bumpStatusVersion()},[currentImage,removeFromBatchByPath,bumpStatusVersion])
useEffect(()=>{const handleKeyDown=(e:KeyboardEvent)=>{if(e.target instanceof HTMLInputElement||e.target instanceof HTMLTextAreaElement)return;if(!hasImages||isGenerating)return;if(e.key==='g'||e.key==='G'){e.preventDefault();toggleBrowseMode();return}if(isGrid)return;if(e.key==='t'||e.key==='T'||e.key==='Backspace'||e.key==='Delete'){e.preventDefault();handleDelete()}else if(e.key==='ArrowLeft'&&selectedIndex>0){e.preventDefault();setSelectedIndex(selectedIndex-1)}else if(e.key==='ArrowRight'&&selectedIndex<currentBatch.length-1){e.preventDefault();setSelectedIndex(selectedIndex+1)}};window.addEventListener('keydown',handleKeyDown);return()=>window.removeEventListener('keydown',handleKeyDown)},[hasImages,isGrid,handleDelete,selectedIndex,currentBatch.length,setSelectedIndex,toggleBrowseMode,isGenerating])
return(<div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-gradient-to-br from-gray-50 to-gray-200 dark:from-gray-900 dark:to-black relative">
{hasImages?(<>
<div className="relative flex-1 overflow-hidden p-12 pb-32 flex flex-col items-center justify-center">
<div className="absolute top-8 left-1/2 -translate-x-1/2 z-20 animate-fade-in-up"><h1 className="text-sm font-bold text-foreground/80 tracking-tight max-w-2xl truncate px-4" title={filename}>{filename||'Untitled'}</h1></div>
<div className="w-full h-full flex items-center justify-center relative max-w-5xl mx-auto" onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave}>
{isGrid?(<div className="w-full h-full overflow-y-auto pr-2"><ImageGrid/></div>):(<div className="absolute inset-4 flex items-center justify-center"><div className="relative transition-all duration-300 transform h-full w-full flex items-center justify-center">
<ImageDisplay/>
{/* Original toolbar - hidden when Quick Edit result/generating */}
{showOriginalToolbar&&(<div className={cn("absolute bottom-4 left-1/2 -translate-x-1/2 z-30 transition-opacity duration-300",toolbarVisible?"opacity-100":"opacity-0 pointer-events-none")}><div className="px-2 py-1.5 flex items-center gap-1 rounded-full bg-black/70 backdrop-blur-xl shadow-lg">
<Tooltip><TooltipTrigger asChild><Button variant={isGrid?'secondary':'ghost'} size="icon" onClick={toggleBrowseMode} className={cn("h-9 w-9 rounded-full text-white/90 transition-all hover:scale-105 hover:bg-white/10",isGrid&&"bg-white/20")}>{isGrid?<ImageIcon className="w-4 h-4"/>:<LayoutGrid className="w-4 h-4"/>}</Button></TooltipTrigger><TooltipContent side="top">{isGrid?'Preview':'Grid (G)'}</TooltipContent></Tooltip>
<ExportActions variant="dark"/>
<QuickEditButton variant="dark"/>
<div className="w-px h-5 bg-white/20 mx-1"/>
<Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" onClick={handleDelete} disabled={!currentImage} className="h-9 w-9 rounded-full text-white/90 hover:bg-destructive/20 hover:text-destructive transition-all hover:scale-110"><Trash2 className="w-4 h-4"/></Button></TooltipTrigger><TooltipContent side="top">Delete (T)</TooltipContent></Tooltip>
</div></div>)}
</div></div>)}
</div>
{!isGrid&&(<div className="absolute right-8 top-1/2 -translate-y-1/2 z-10 opacity-0 hover:opacity-100 transition-opacity duration-300"><div className="glass-panel p-4 rounded-2xl max-w-xs shadow-soft bg-white/60 dark:bg-black/40 backdrop-blur-xl border-white/20"><ContextPanel/></div></div>)}
</div>
{!isGrid&&(<div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-3 w-full max-w-5xl px-12">
<div className="bg-black/5 dark:bg-white/5 backdrop-blur-md px-3 py-1 rounded-full border border-black/5 dark:border-white/5 animate-fade-in-up shadow-sm"><span className="text-[10px] font-mono font-medium text-muted-foreground tracking-widest uppercase">{imageCounter}</span></div>
<div className="glass-pill p-1.5 shadow-float bg-white/40 dark:bg-black/40 backdrop-blur-xl border-white/20 dark:border-white/5 ring-1 ring-white/20 max-w-full"><ThumbnailStrip/></div>
</div>)}
</>):(<EmptyState/>)}
</div>)
}
export function Workstation(){return(<QuickEditProvider><WorkstationContent/></QuickEditProvider>)}
