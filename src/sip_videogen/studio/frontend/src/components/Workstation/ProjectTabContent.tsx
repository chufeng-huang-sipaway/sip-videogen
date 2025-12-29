//ProjectTabContent - image viewer for project tabs (per-tab state)
import{useCallback,useRef,useEffect,useMemo,useState}from'react'
import{useBrand}from'@/context/BrandContext'
import{useWorkstation,type GeneratedImage,type BrowseMode}from'@/context/WorkstationContext'
import{useDrag}from'@/context/DragContext'
import{bridge,isPyWebView,waitForPyWebViewReady}from'@/lib/bridge'
import{toast}from'@/components/ui/toaster'
import{Button}from'@/components/ui/button'
import{Trash2,LayoutGrid,Image as ImageIcon,Loader2,ChevronLeft,ChevronRight}from'lucide-react'
import{Tooltip,TooltipContent,TooltipTrigger}from'@/components/ui/tooltip'
import{cn}from'@/lib/utils'
import{clearAllCaches}from'@/lib/thumbnailCache'
interface Props{projectSlug:string;isActive:boolean}
type LoadState='loading'|'loaded'|'error'|'not-found'
export function ProjectTabContent({projectSlug,isActive}:Props){
const{activeBrand}=useBrand()
const{bumpStatusVersion}=useWorkstation()
//Per-tab local state (not shared WorkstationContext)
const[images,setImages]=useState<GeneratedImage[]>([])
const[selectedIndex,setSelectedIndex]=useState(0)
const[browseMode,setBrowseMode]=useState<BrowseMode>('preview')
const[loadState,setLoadState]=useState<LoadState>('loading')
const[error,setError]=useState<string|null>(null)
const[toolbarVisible,setToolbarVisible]=useState(true)
const hideTimeoutRef=useRef<ReturnType<typeof setTimeout>|null>(null)
const requestIdRef=useRef(0)
const hasImages=images.length>0
const currentImage=images[selectedIndex]
//Load images on mount or when projectSlug changes
useEffect(()=>{if(!isActive)return
if(!activeBrand){setImages([]);setLoadState('loaded');return}
const thisRequestId=++requestIdRef.current
setLoadState('loading');setError(null)
async function load(){
const ready=await waitForPyWebViewReady()
if(!ready||requestIdRef.current!==thisRequestId)return
try{
const isUnsorted=projectSlug==='unsorted'
if(isUnsorted){
//Unsorted images have full metadata via getUnsortedImages
const rawImages=await bridge.getUnsortedImages(activeBrand??undefined)
if(requestIdRef.current!==thisRequestId)return
const batch:GeneratedImage[]=rawImages.map(img=>({id:img.id,path:img.currentPath,originalPath:img.originalPath,prompt:img.prompt??undefined,sourceTemplatePath:img.sourceTemplatePath??undefined,timestamp:img.timestamp,viewedAt:img.viewedAt??null}))
setImages(batch);setSelectedIndex(Math.max(0,batch.length-1));setLoadState('loaded')
}else{
//Project assets are just paths - convert to minimal GeneratedImage format
const assetPaths=await bridge.getProjectAssets(projectSlug)
if(requestIdRef.current!==thisRequestId)return
const batch:GeneratedImage[]=assetPaths.map((p,i)=>({id:`proj-${projectSlug}-${i}`,path:'',originalPath:p,timestamp:new Date().toISOString(),viewedAt:new Date().toISOString()}))
setImages(batch);setSelectedIndex(Math.max(0,batch.length-1));setLoadState('loaded')}}catch(e){if(requestIdRef.current!==thisRequestId)return;setError(e instanceof Error?e.message:'Failed to load');setLoadState('error')}}
clearAllCaches();load()
return()=>{requestIdRef.current++}},[activeBrand,projectSlug,isActive])
//Mark image as viewed when selected
useEffect(()=>{if(!isActive||!currentImage||!activeBrand||!isPyWebView())return
if(currentImage.viewedAt!==null)return
const now=new Date().toISOString()
setImages(prev=>prev.map(img=>img.id===currentImage.id?{...img,viewedAt:now}:img))
bridge.markImageViewed(currentImage.id,activeBrand).catch(e=>console.error('Failed to mark viewed:',e))},[isActive,currentImage?.id,currentImage?.viewedAt,activeBrand])
const handleMouseMove=useCallback(()=>{setToolbarVisible(true);if(hideTimeoutRef.current)clearTimeout(hideTimeoutRef.current);hideTimeoutRef.current=setTimeout(()=>setToolbarVisible(false),2500)},[])
const handleMouseLeave=useCallback(()=>{if(hideTimeoutRef.current)clearTimeout(hideTimeoutRef.current);hideTimeoutRef.current=setTimeout(()=>setToolbarVisible(false),800)},[])
const filename=useMemo(()=>{if(!currentImage)return'';const p=currentImage.originalPath||currentImage.path;if(!p||p.startsWith('data:'))return'';return p.split('/').pop()||''},[currentImage])
const imageCounter=`${selectedIndex+1} / ${images.length}`
const isGrid=browseMode==='grid'
const toggleBrowseMode=useCallback(()=>{setBrowseMode(isGrid?'preview':'grid')},[isGrid])
const handleDelete=useCallback(async()=>{if(!currentImage)return
const path=currentImage.originalPath||currentImage.path
if(!path||path.startsWith('data:')){toast.error('Cannot delete this image');return}
//Remove from UI first
const idxToRemove=images.findIndex(img=>img.id===currentImage.id)
const newBatch=images.filter((_,i)=>i!==idxToRemove)
const newLen=newBatch.length
let newIdx=selectedIndex
if(newLen===0)newIdx=0
else if(selectedIndex>idxToRemove)newIdx=selectedIndex-1
else if(selectedIndex>=newLen)newIdx=newLen-1
setImages(newBatch);setSelectedIndex(newIdx)
try{await bridge.deleteAsset(path);toast.success('Moved to Trash')}catch(e){console.warn('Delete failed:',e)}
bumpStatusVersion()},[currentImage,images,selectedIndex,bumpStatusVersion])
//Keyboard shortcuts (only when active)
useEffect(()=>{if(!isActive)return
const handleKeyDown=(e:KeyboardEvent)=>{if(e.target instanceof HTMLInputElement||e.target instanceof HTMLTextAreaElement)return
if(!hasImages)return
if(e.key==='g'||e.key==='G'){e.preventDefault();toggleBrowseMode();return}
if(isGrid)return
if(e.key==='t'||e.key==='T'||e.key==='Backspace'||e.key==='Delete'){e.preventDefault();handleDelete()}
else if(e.key==='ArrowLeft'&&selectedIndex>0){e.preventDefault();setSelectedIndex(selectedIndex-1)}
else if(e.key==='ArrowRight'&&selectedIndex<images.length-1){e.preventDefault();setSelectedIndex(selectedIndex+1)}}
window.addEventListener('keydown',handleKeyDown)
return()=>window.removeEventListener('keydown',handleKeyDown)},[isActive,hasImages,isGrid,handleDelete,selectedIndex,images.length,toggleBrowseMode])
//Pause toolbar timer when inactive
useEffect(()=>{if(!isActive&&hideTimeoutRef.current){clearTimeout(hideTimeoutRef.current);hideTimeoutRef.current=null}},[isActive])
//Loading state
if(loadState==='loading')return(<div className="flex-1 flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground/50"/></div>)
//Error state
if(loadState==='error')return(<div className="flex-1 flex flex-col items-center justify-center gap-4"><p className="text-sm text-muted-foreground">{error||'Failed to load project'}</p><Button variant="outline" size="sm" onClick={()=>{setLoadState('loading');requestIdRef.current++}}>Retry</Button></div>)
//Empty state (no images)
if(!hasImages)return(<div className="flex-1 flex items-center justify-center p-8"><div className="text-center max-w-sm"><div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-muted/50 mb-4"><ImageIcon className="w-8 h-8 text-muted-foreground/60"/></div><h2 className="text-lg font-medium text-muted-foreground mb-2">No images</h2><p className="text-sm text-muted-foreground/60 leading-relaxed">This project has no images yet</p></div></div>)
//Loaded with images
return(<div className="flex-1 flex flex-col min-w-0 overflow-hidden">
{/* Main Workspace Area */}
<div className="relative flex-1 overflow-hidden p-12 pb-32 flex flex-col items-center justify-center">
{/* Top Info */}
<div className="absolute top-8 left-1/2 -translate-x-1/2 z-20 animate-fade-in-up"><h1 className="text-sm font-bold text-foreground/80 tracking-tight max-w-2xl truncate px-4" title={filename}>{filename||'Untitled'}</h1></div>
{/* Center Content */}
<div className="w-full h-full flex items-center justify-center relative max-w-5xl mx-auto" onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave}>
{isGrid?(<div className="w-full h-full overflow-y-auto pr-2"><ImageGridLocal images={images} selectedIndex={selectedIndex} setSelectedIndex={setSelectedIndex} setBrowseMode={setBrowseMode}/></div>):(
<div className="absolute inset-4 flex items-center justify-center">
<div className="relative transition-all duration-300 transform h-full w-full flex items-center justify-center">
<ImageDisplayLocal images={images} selectedIndex={selectedIndex} setSelectedIndex={setSelectedIndex}/>
{/* Floating Action Toolbar */}
<div className={cn("absolute bottom-4 left-1/2 -translate-x-1/2 z-30 transition-opacity duration-300",toolbarVisible?"opacity-100":"opacity-0 pointer-events-none")}>
<div className="px-2 py-1.5 flex items-center gap-1 rounded-full bg-black/70 backdrop-blur-xl shadow-lg">
<Tooltip><TooltipTrigger asChild><Button variant={isGrid?'secondary':'ghost'} size="icon" onClick={toggleBrowseMode} className={cn("h-9 w-9 rounded-full text-white/90 transition-all hover:scale-105 hover:bg-white/10",isGrid&&"bg-white/20")}>{isGrid?<ImageIcon className="w-4 h-4"/>:<LayoutGrid className="w-4 h-4"/>}</Button></TooltipTrigger><TooltipContent side="top">{isGrid?'Preview':'Grid (G)'}</TooltipContent></Tooltip>
<ExportActionsLocal images={images} selectedIndex={selectedIndex} variant="dark"/>
<div className="w-px h-5 bg-white/20 mx-1"/>
<Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" onClick={handleDelete} disabled={!currentImage} className="h-9 w-9 rounded-full text-white/90 hover:bg-red-500/20 hover:text-red-400 transition-all hover:scale-110"><Trash2 className="w-4 h-4"/></Button></TooltipTrigger><TooltipContent side="top">Delete (T)</TooltipContent></Tooltip>
</div></div>
</div></div>)}
</div>
{/* Context Panel */}
{!isGrid&&currentImage&&(<div className="absolute right-8 top-1/2 -translate-y-1/2 z-10 opacity-0 hover:opacity-100 transition-opacity duration-300"><div className="glass-panel p-4 rounded-2xl max-w-xs shadow-soft bg-white/60 dark:bg-black/40 backdrop-blur-xl border-white/20"><ContextPanelLocal image={currentImage}/></div></div>)}
</div>
{/* Floating Thumbnails Dock */}
{!isGrid&&images.length>1&&(<div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-3 w-full max-w-5xl px-12">
<div className="bg-black/5 dark:bg-white/5 backdrop-blur-md px-3 py-1 rounded-full border border-black/5 dark:border-white/5 animate-fade-in-up shadow-sm"><span className="text-[10px] font-mono font-medium text-muted-foreground tracking-widest uppercase">{imageCounter}</span></div>
<div className="glass-pill p-1.5 shadow-float bg-white/40 dark:bg-black/40 backdrop-blur-xl border-white/20 dark:border-white/5 ring-1 ring-white/20 max-w-full"><ThumbnailStripLocal images={images} selectedIndex={selectedIndex} setSelectedIndex={setSelectedIndex}/></div>
</div>)}
</div>)
}
//Local versions of sub-components that use passed props instead of WorkstationContext
function ImageDisplayLocal({images,selectedIndex,setSelectedIndex}:{images:GeneratedImage[];selectedIndex:number;setSelectedIndex:(i:number)=>void}){
const{setDragData,dragData}=useDrag()
const currentImage=images[selectedIndex]
const[isLoading,setIsLoading]=useState(false)
const[displayedSrc,setDisplayedSrc]=useState<string|null>(null)
const[pendingSrc,setPendingSrc]=useState<string|null>(null)
const[error,setError]=useState<string|null>(null)
const[hovered,setHovered]=useState(false)
const prevIdRef=useRef<string|null>(null)
const canPrev=selectedIndex>0,canNext=selectedIndex<images.length-1
const goPrev=useCallback(()=>{if(canPrev)setSelectedIndex(selectedIndex-1)},[canPrev,selectedIndex,setSelectedIndex])
const goNext=useCallback(()=>{if(canNext)setSelectedIndex(selectedIndex+1)},[canNext,selectedIndex,setSelectedIndex])
useEffect(()=>{if(!currentImage)return;if(prevIdRef.current!==currentImage.id){setIsLoading(true);setPendingSrc(null);setError(null);prevIdRef.current=currentImage.id}},[currentImage?.id])
useEffect(()=>{let cancelled=false
async function load(){if(!currentImage)return
const raw=currentImage.path,origPath=currentImage.originalPath
const{hasFullCached,getFullCached,setFullCached}=await import('@/lib/thumbnailCache')
const np=(p:string)=>p.startsWith('file://')?p.slice('file://'.length):p
const cacheKey=origPath||np(raw||'')
if(cacheKey&&hasFullCached(cacheKey)){setPendingSrc(getFullCached(cacheKey)!);return}
if((!raw||raw==='')&&origPath){if(!isPyWebView()){setIsLoading(false);setError('Cannot load');return}
try{const dataUrl=await bridge.getAssetFull(origPath);if(cancelled)return;if(dataUrl&&dataUrl!==''){setFullCached(origPath,dataUrl);setPendingSrc(dataUrl)}else{setIsLoading(false);setError('Image not found')}}catch(e){if(!cancelled){setError(e instanceof Error?e.message:String(e));setIsLoading(false)}}return}
if(!raw||raw===''){setIsLoading(false);setError('Missing image path');return}
if(raw.startsWith('data:')||raw.startsWith('http://')||raw.startsWith('https://')){setPendingSrc(raw);return}
const normalized=np(raw)
if(!isPyWebView()){setPendingSrc(normalized.startsWith('/')?`file://${normalized}`:normalized);return}
try{const dataUrl=await bridge.getImageData(normalized);if(cancelled)return;if(dataUrl&&dataUrl!==''){setFullCached(normalized,dataUrl);setPendingSrc(dataUrl)}else{setIsLoading(false);setError('Image not found')}}catch(e){if(!cancelled){setError(e instanceof Error?e.message:String(e));setIsLoading(false)}}}
load();return()=>{cancelled=true}},[currentImage?.id,currentImage?.path,currentImage?.originalPath])
const handlePendingLoad=()=>{setDisplayedSrc(pendingSrc);setPendingSrc(null);setIsLoading(false)}
const handlePendingError=()=>{setPendingSrc(null);setIsLoading(false);setError('Failed to load')}
const handleMouseDown=(e:React.MouseEvent)=>{if(e.button!==0)return;const path=currentImage?.originalPath||currentImage?.path;if(!path||path.startsWith('data:'))return;setDragData({type:'asset',path,thumbnailUrl:displayedSrc||undefined})}
if(!currentImage)return null
const isDragging=!!dragData
const imgClass=cn("absolute inset-0 w-full h-full object-contain cursor-grab active:cursor-grabbing select-none transition-opacity duration-200",isDragging&&"opacity-50")
const navBtnClass="absolute top-1/2 -translate-y-1/2 z-20 p-2 rounded-full bg-black/50 text-white/90 backdrop-blur-sm transition-all hover:bg-black/70 hover:scale-110 disabled:opacity-30 disabled:pointer-events-none"
return(<div className="w-full h-full flex items-center justify-center relative" onMouseEnter={()=>setHovered(true)} onMouseLeave={()=>setHovered(false)}>
{displayedSrc&&!error&&<img draggable={false} onMouseDown={handleMouseDown} src={displayedSrc} alt="" className={imgClass}/>}
{pendingSrc&&pendingSrc!==displayedSrc&&<img draggable={false} src={pendingSrc} alt={currentImage.prompt||'Image'} onLoad={handlePendingLoad} onError={handlePendingError} className={imgClass} style={{animation:'fadeIn 200ms ease-out forwards'}}/>}
{isLoading&&!displayedSrc&&<div className="absolute inset-0 flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground/30"/></div>}
{!isLoading&&error&&!displayedSrc&&<div className="text-sm text-muted-foreground">{error}</div>}
<button onClick={goPrev} disabled={!canPrev} className={cn(navBtnClass,"left-2 transition-opacity duration-200",hovered?"opacity-100":"opacity-0")}><ChevronLeft className="w-6 h-6"/></button>
<button onClick={goNext} disabled={!canNext} className={cn(navBtnClass,"right-2 transition-opacity duration-200",hovered?"opacity-100":"opacity-0")}><ChevronRight className="w-6 h-6"/></button>
</div>)}
//Local ThumbnailStrip
function ThumbnailStripLocal({images,selectedIndex,setSelectedIndex}:{images:GeneratedImage[];selectedIndex:number;setSelectedIndex:(i:number)=>void}){
const{setDragData,clearDrag}=useDrag()
const btnRefs=useRef<(HTMLButtonElement|null)[]>([])
useEffect(()=>{requestAnimationFrame(()=>{const btn=btnRefs.current[selectedIndex];if(btn)btn.scrollIntoView({behavior:'smooth',inline:'center',block:'nearest'})})},[selectedIndex,images.length,images[0]?.id])
const handleDragStart=(e:React.DragEvent,path:string)=>{if(!path||path.startsWith('data:'))return
const btn=e.currentTarget as HTMLElement;const img=btn.querySelector('img');if(img&&img.naturalWidth>0){const size=80,canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');if(ctx){const scale=Math.min(size/img.naturalWidth,size/img.naturalHeight);canvas.width=img.naturalWidth*scale;canvas.height=img.naturalHeight*scale;ctx.drawImage(img,0,0,canvas.width,canvas.height);e.dataTransfer.setDragImage(canvas,canvas.width/2,canvas.height/2)}}
e.dataTransfer.setData('text/plain',path);try{e.dataTransfer.setData('text/uri-list',path)}catch{}try{e.dataTransfer.setData('application/x-brand-asset',path)}catch{}e.dataTransfer.effectAllowed='copy';setDragData({type:'asset',path})}
const handleDragEnd=()=>clearDrag()
if(images.length<=1)return null
return(<div className="flex-shrink-0 w-full"><div className="flex gap-1.5 overflow-x-auto scrollbar-thin scrollbar-thumb-muted-foreground/20 scrollbar-track-transparent justify-center px-1 py-0.5">
{images.map((img,i)=>{const imgPath=img.originalPath||img.path||'';const canDrag=!!imgPath&&!imgPath.startsWith('data:');return(<button key={img.id} ref={el=>{btnRefs.current[i]=el}} draggable={canDrag} onDragStart={e=>handleDragStart(e,imgPath)} onDragEnd={handleDragEnd} onClick={()=>setSelectedIndex(i)} className={cn("flex-shrink-0 w-12 h-12 rounded-lg overflow-hidden border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/50 relative cursor-grab active:cursor-grabbing",i===selectedIndex?"border-primary shadow-md ring-2 ring-primary/20 scale-105 z-10":"border-transparent opacity-70 hover:opacity-100 hover:scale-105")}><ThumbLocal path={imgPath} isUnread={img.viewedAt===null}/></button>)})}
</div></div>)}
//Local Thumb for ThumbnailStrip
function ThumbLocal({path,isUnread}:{path:string;isUnread:boolean}){
const[src,setSrc]=useState<string|null>(null)
const[loading,setLoading]=useState(true)
const containerRef=useRef<HTMLDivElement>(null)
const loadedRef=useRef(false)
const mountedRef=useRef(true)
useEffect(()=>{mountedRef.current=true;return()=>{mountedRef.current=false}},[])
useEffect(()=>{if(!path){setLoading(false);return}
const checkCache=async()=>{const{hasThumbCached,getThumbCached}=await import('@/lib/thumbnailCache');if(hasThumbCached(path)){setSrc(getThumbCached(path)!);setLoading(false);return true}return false}
checkCache().then(cached=>{if(cached||path.startsWith('data:')){if(path.startsWith('data:')){setSrc(path);setLoading(false)}return}
if(!isPyWebView()){setLoading(false);return}
const container=containerRef.current;if(!container)return
const observer=new IntersectionObserver(entries=>{if(entries[0]?.isIntersecting&&!loadedRef.current){loadedRef.current=true;observer.disconnect()
import('@/lib/thumbnailCache').then(({setThumbCached,loadWithConcurrency})=>{loadWithConcurrency(async()=>{try{const dataUrl=await bridge.getAssetThumbnail(path);if(!mountedRef.current)return;setThumbCached(path,dataUrl);setSrc(dataUrl)}catch(e){console.error('Thumb error:',e)}finally{if(mountedRef.current)setLoading(false)}})})}},{rootMargin:'100px'})
observer.observe(container);return()=>observer.disconnect()})},[path])
return(<div ref={containerRef} className="w-full h-full flex items-center justify-center bg-muted/20 relative">{loading?<Loader2 className="w-3 h-3 animate-spin text-muted-foreground/30"/>:src?<img src={src} alt="" className="w-full h-full object-cover"/>:null}{isUnread&&<div className="absolute top-0.5 right-0.5 w-2.5 h-2.5 bg-blue-500 rounded-full border-2 border-background shadow-sm"/>}</div>)}
//Local ImageGrid
function ImageGridLocal({images,selectedIndex,setSelectedIndex,setBrowseMode}:{images:GeneratedImage[];selectedIndex:number;setSelectedIndex:(i:number)=>void;setBrowseMode:(m:BrowseMode)=>void}){
const handleClick=(index:number)=>{setSelectedIndex(index);setBrowseMode('preview')}
if(images.length===0)return<div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">No images</div>
return(<div className="flex-1 overflow-auto p-4"><div className="grid grid-cols-[repeat(auto-fill,minmax(120px,1fr))] gap-3">{images.map((img,i)=><GridThumbLocal key={img.id} path={img.originalPath||img.path||''} isSelected={i===selectedIndex} isUnread={img.viewedAt===null} onClick={()=>handleClick(i)}/>)}</div></div>)}
//Local GridThumb
function GridThumbLocal({path,isSelected,isUnread,onClick}:{path:string;isSelected:boolean;isUnread:boolean;onClick:()=>void}){
const{setDragData,clearDrag}=useDrag()
const[src,setSrc]=useState<string|null>(null)
const[loading,setLoading]=useState(true)
const containerRef=useRef<HTMLDivElement>(null)
const loadedRef=useRef(false)
const mountedRef=useRef(true)
useEffect(()=>{mountedRef.current=true;return()=>{mountedRef.current=false}},[])
useEffect(()=>{if(!path||loadedRef.current){setLoading(false);return}
if(path.startsWith('data:')){setSrc(path);setLoading(false);return}
if(!isPyWebView()){setLoading(false);return}
const container=containerRef.current;if(!container)return
const observer=new IntersectionObserver(entries=>{if(entries[0]?.isIntersecting&&!loadedRef.current){loadedRef.current=true;observer.disconnect()
bridge.getAssetThumbnail(path).then(dataUrl=>{if(!mountedRef.current)return;setSrc(dataUrl)}).catch(e=>console.error('GridThumb error:',e)).finally(()=>{if(mountedRef.current)setLoading(false)})}},{rootMargin:'100px'})
observer.observe(container);return()=>observer.disconnect()},[path])
const handleDragStart=(e:React.DragEvent)=>{if(!path||path.startsWith('data:'))return
const container=e.currentTarget as HTMLElement;const img=container.querySelector('img');if(img&&img.naturalWidth>0){const size=80,canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');if(ctx){const scale=Math.min(size/img.naturalWidth,size/img.naturalHeight);canvas.width=img.naturalWidth*scale;canvas.height=img.naturalHeight*scale;ctx.drawImage(img,0,0,canvas.width,canvas.height);e.dataTransfer.setDragImage(canvas,canvas.width/2,canvas.height/2)}}
e.dataTransfer.setData('text/plain',path);try{e.dataTransfer.setData('text/uri-list',path)}catch{}try{e.dataTransfer.setData('application/x-brand-asset',path)}catch{}e.dataTransfer.effectAllowed='copy';setDragData({type:'asset',path})}
const handleDragEnd=()=>clearDrag()
return(<div ref={containerRef} draggable={!!path&&!path.startsWith('data:')} onDragStart={handleDragStart} onDragEnd={handleDragEnd} onClick={onClick} className={cn("aspect-square rounded-lg overflow-hidden cursor-grab active:cursor-grabbing transition-all duration-200 hover:ring-2 hover:ring-primary/50 relative",isSelected?"ring-2 ring-primary shadow-lg bg-primary/5":"border border-border/30 hover:border-border")}>{loading?<div className="w-full h-full flex items-center justify-center bg-muted/20"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground/30"/></div>:src?<img src={src} alt="" className="w-full h-full object-cover"/>:<div className="w-full h-full bg-muted/20"/>}{isUnread&&<div className="absolute top-1 right-1 w-3 h-3 bg-blue-500 rounded-full border-2 border-background shadow-sm"/>}</div>)}
//Local ContextPanel
function ContextPanelLocal({image}:{image:GeneratedImage}){
const[expanded,setExpanded]=useState(false)
const toggle=useCallback(()=>setExpanded(e=>!e),[])
const copyPrompt=useCallback(async()=>{if(!image?.prompt)return;try{await navigator.clipboard.writeText(image.prompt)}catch(e){console.error('Copy failed:',e)}},[image?.prompt])
if(!image)return null
const ts=image.timestamp?new Date(image.timestamp).toLocaleString():null
const src=image.sourceTemplatePath?.split('/').pop()
return(<div className="relative">{expanded?(<div className="bg-background/95 backdrop-blur-sm border border-border rounded-lg shadow-lg p-3 min-w-[220px] max-w-[320px]"><div className="flex items-center justify-between mb-2"><span className="text-xs font-medium text-muted-foreground">Image Details</span><Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={toggle}><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/></svg></Button></div>{image.prompt?(<div className="mb-3"><div className="flex items-center justify-between mb-1"><span className="text-xs text-muted-foreground">Prompt</span><Button variant="ghost" size="sm" className="h-5 px-1.5 text-xs" onClick={copyPrompt}><svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>Copy</Button></div><p className="text-xs text-foreground/90 line-clamp-4">{image.prompt}</p></div>):(<p className="text-xs text-muted-foreground mb-3">No prompt</p>)}{src&&<div className="mb-2"><span className="text-xs text-muted-foreground block mb-0.5">Source</span><span className="text-xs text-foreground/90">{src}</span></div>}{ts&&<div><span className="text-xs text-muted-foreground block mb-0.5">Generated</span><span className="text-xs text-foreground/90">{ts}</span></div>}</div>):(<Button variant="ghost" size="sm" className="h-8 w-8 p-0 bg-background/80 backdrop-blur-sm border border-border/50 shadow-sm" onClick={toggle}><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg></Button>)}</div>)}
//Local ExportActions
function ExportActionsLocal({images,selectedIndex,variant='light'}:{images:GeneratedImage[];selectedIndex:number;variant?:'light'|'dark'}){
const currentImage=images[selectedIndex]
const[copying,setCopying]=useState(false)
const[copied,setCopied]=useState(false)
const isDark=variant==='dark'
const btnClass=cn("h-9 w-9 rounded-full transition-all",isDark?"text-white/90 hover:bg-white/10":"hover:bg-black/5 dark:hover:bg-white/10")
const handleCopy=useCallback(async()=>{if(!currentImage)return;setCopying(true);setCopied(false);try{await bridge.copyImageToClipboard(currentImage.originalPath||currentImage.path);setCopied(true);setTimeout(()=>setCopied(false),2000)}catch(e){console.error('Copy failed:',e)}finally{setCopying(false)}},[currentImage])
const handleReveal=useCallback(async()=>{if(!currentImage)return;try{await bridge.shareImage(currentImage.originalPath||currentImage.path)}catch(e){console.error('Reveal failed:',e)}},[currentImage])
if(!currentImage)return null
return(<div className="flex items-center gap-1"><Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" className={btnClass} onClick={handleCopy} disabled={copying}>{copying?<svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>:copied?<svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7"/></svg>:<svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>}</Button></TooltipTrigger><TooltipContent side="top">Copy</TooltipContent></Tooltip><Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" className={btnClass} onClick={handleReveal}><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg></Button></TooltipTrigger><TooltipContent side="top">Reveal in Finder</TooltipContent></Tooltip></div>)}
