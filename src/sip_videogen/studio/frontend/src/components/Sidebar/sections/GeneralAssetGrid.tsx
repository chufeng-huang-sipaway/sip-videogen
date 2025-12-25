import{useEffect,useState,useCallback,useRef}from'react'
import{Image,Loader2,RefreshCw,Play,Film}from'lucide-react'
import{useBrand}from'@/context/BrandContext'
import{useWorkstation}from'@/context/WorkstationContext'
import{bridge,isPyWebView}from'@/lib/bridge'
import{VideoViewer}from'@/components/ui/video-viewer'
import{Button}from'@/components/ui/button'
//Thumbnail cache for session
const thumbnailCache=new Map<string,string>()
const VIDEO_EXTS=new Set(['.mp4','.mov','.webm'])
function isVideoAsset(path:string):boolean{const dot=path.lastIndexOf('.');return dot>=0&&VIDEO_EXTS.has(path.slice(dot).toLowerCase())}
interface AssetThumbnailProps{path:string;onClick?:()=>void}
function AssetThumbnail({path,onClick}:AssetThumbnailProps){
const[src,setSrc]=useState<string|null>(()=>thumbnailCache.get(path)??null)
const[loading,setLoading]=useState(!thumbnailCache.has(path))
const containerRef=useRef<HTMLDivElement>(null)
const loadedRef=useRef(false)
useEffect(()=>{if(!isPyWebView()||loadedRef.current||thumbnailCache.has(path)){setLoading(false);return}
const container=containerRef.current;if(!container)return
const observer=new IntersectionObserver((entries)=>{if(entries[0]?.isIntersecting&&!loadedRef.current){loadedRef.current=true;observer.disconnect()
bridge.getAssetThumbnail(path).then(dataUrl=>{thumbnailCache.set(path,dataUrl);setSrc(dataUrl)}).catch(()=>{}).finally(()=>setLoading(false))}},{rootMargin:'50px'})
observer.observe(container);return()=>observer.disconnect()},[path])
return(<div ref={containerRef} className="group relative aspect-square rounded-md overflow-hidden bg-gray-100 dark:bg-gray-800 border border-transparent hover:border-blue-500/50 hover:shadow-md transition-all duration-200 cursor-pointer" onClick={onClick} title="Click to preview">{loading?(<div className="absolute inset-0 flex items-center justify-center bg-gray-100 dark:bg-gray-800 animate-pulse"><Loader2 className="h-4 w-4 text-gray-400 animate-spin"/></div>):src?(<><img src={src} alt="" className="w-full h-full object-cover object-center transition-transform duration-300 group-hover:scale-105"/><div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors duration-200"/></>):(<div className="absolute inset-0 flex items-center justify-center text-gray-400"><Image className="h-5 w-5"/></div>)}</div>)}
function VideoThumbnail({onClick}:{path:string;onClick?:()=>void}){return(<div className="group relative aspect-square rounded-md overflow-hidden bg-gradient-to-br from-indigo-500/20 via-purple-500/20 to-pink-500/20 border-2 border-indigo-400/50 hover:border-indigo-500 hover:shadow-md transition-all duration-200 cursor-pointer" onClick={onClick} title="Click to preview video"><div className="absolute top-1 left-1 flex items-center gap-0.5 bg-black/60 text-white px-1.5 py-0.5 rounded text-[9px] font-medium"><Film className="h-2.5 w-2.5"/><span>MP4</span></div><div className="absolute inset-0 flex items-center justify-center"><div className="w-10 h-10 rounded-full bg-white/90 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform"><Play className="w-5 h-5 text-indigo-600 ml-0.5"/></div></div></div>)}
interface GeneralAssetGridProps{expectedCount?:number}
export function GeneralAssetGrid({expectedCount}:GeneralAssetGridProps){
const{activeBrand}=useBrand()
const{setCurrentBatch,setSelectedIndex,setIsTrashView}=useWorkstation()
const[assets,setAssets]=useState<string[]>([])
const[isLoading,setIsLoading]=useState(true)
const[isRefreshing,setIsRefreshing]=useState(false)
const[error,setError]=useState<string|null>(null)
const[previewVideo,setPreviewVideo]=useState<{src:string;path:string}|null>(null)
const loadAssets=useCallback(async(isBackground=false)=>{if(!activeBrand||!isPyWebView())return
if(!isBackground)setIsLoading(true);else setIsRefreshing(true)
setError(null)
try{const result=await bridge.getGeneralAssets(activeBrand);setAssets(result.assets||[])}catch(err){if(!isBackground)setError(err instanceof Error?err.message:'Failed to load')}finally{setIsLoading(false);setIsRefreshing(false)}},[activeBrand])
useEffect(()=>{loadAssets(false)},[loadAssets])
const sortedAssets=[...assets].sort((a,b)=>{const nameA=a.split('/').pop()??a;const nameB=b.split('/').pop()??b;return nameB.localeCompare(nameA)})
const handlePreview=useCallback((clickedPath:string)=>{if(!isPyWebView())return
const imageAssets=sortedAssets.filter(p=>!isVideoAsset(p))
const allImages=imageAssets.map((assetPath)=>{const filename=assetPath.split('/').pop()||assetPath
return{id:filename,path:'',originalPath:assetPath,timestamp:new Date().toISOString(),status:'kept'as const}})
const clickedIndex=imageAssets.findIndex(p=>p===clickedPath)
setIsTrashView(false);setCurrentBatch(allImages);setSelectedIndex(clickedIndex>=0?clickedIndex:0)},[sortedAssets,setCurrentBatch,setSelectedIndex,setIsTrashView])
const handlePreviewVideo=useCallback(async(path:string)=>{if(!isPyWebView())return;try{const dataUrl=await bridge.getVideoData(path);setPreviewVideo({src:dataUrl,path})}catch(err){console.error('Failed to load video:',err)}},[])
const handleRefresh=useCallback(()=>{thumbnailCache.clear();loadAssets(false)},[loadAssets])
if(isLoading)return(<div className="py-2"><div className="grid grid-cols-[repeat(auto-fill,minmax(64px,1fr))] gap-2">{Array.from({length:Math.min(expectedCount??4,8)}).map((_,i)=>(<div key={i} className="aspect-square rounded-lg bg-gray-100 dark:bg-gray-800 animate-pulse"/>))}</div></div>)
if(error)return(<div className="py-2 px-2 text-xs text-red-500 flex items-center gap-2"><span>{error}</span><Button variant="ghost" size="sm" className="h-5 px-1.5" onClick={handleRefresh}><RefreshCw className="h-3 w-3"/></Button></div>)
if(sortedAssets.length===0)return(<div className="py-4 px-2 text-xs text-center text-gray-400 italic bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-dashed border-gray-200 dark:border-gray-800"><p>No general assets yet</p><p className="mt-1 text-[10px]">Generate images without selecting a project</p></div>)
return(<><div className="flex items-center justify-between mb-1"><span className="text-[10px] text-gray-400">{sortedAssets.length} asset{sortedAssets.length!==1?'s':''}</span><div className="flex items-center gap-1">{isRefreshing&&<Loader2 className="h-3 w-3 text-gray-400 animate-spin"/>}<Button variant="ghost" size="sm" className="h-5 w-5 p-0" onClick={handleRefresh} title="Refresh"><RefreshCw className="h-3 w-3"/></Button></div></div><div className="grid grid-cols-[repeat(auto-fill,minmax(60px,1fr))] gap-1.5 py-1">{sortedAssets.map(path=>isVideoAsset(path)?(<VideoThumbnail key={path} path={path} onClick={()=>handlePreviewVideo(path)}/>):(<AssetThumbnail key={path} path={path} onClick={()=>handlePreview(path)}/>))}</div><VideoViewer src={previewVideo?.src??null} filePath={previewVideo?.path} onClose={()=>setPreviewVideo(null)}/></>)}
