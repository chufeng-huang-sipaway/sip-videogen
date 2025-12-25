//ImageGrid component - grid view of all images in current batch for efficient browsing
import{useState,useEffect,useRef}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import{bridge,isPyWebView}from'../../lib/bridge'
import{cn}from'../../lib/utils'
import{Loader2}from'lucide-react'
//Thumbnail cache shared across grid
const gridThumbCache=new Map<string,string>()
function GridThumb({path,isSelected,onClick}:{path:string;isSelected:boolean;onClick:()=>void}){
const[src,setSrc]=useState<string|null>(()=>gridThumbCache.get(path)??null)
const[loading,setLoading]=useState(!gridThumbCache.has(path))
const containerRef=useRef<HTMLDivElement>(null)
const loadedRef=useRef(false)
const mountedRef=useRef(true)
useEffect(()=>{mountedRef.current=true;return()=>{mountedRef.current=false}},[])
//IntersectionObserver for lazy loading
useEffect(()=>{if(!path||loadedRef.current||gridThumbCache.has(path)){setLoading(false);return}
if(path.startsWith('data:')){setSrc(path);setLoading(false);return}
if(!isPyWebView()){setLoading(false);return}
const container=containerRef.current;if(!container)return
const observer=new IntersectionObserver((entries)=>{
if(entries[0]?.isIntersecting&&!loadedRef.current){loadedRef.current=true;observer.disconnect()
bridge.getAssetThumbnail(path).then(dataUrl=>{if(!mountedRef.current)return;gridThumbCache.set(path,dataUrl);setSrc(dataUrl)}).catch(e=>console.error('GridThumb load error:',e)).finally(()=>{if(mountedRef.current)setLoading(false)})}},{rootMargin:'100px'})
observer.observe(container);return()=>observer.disconnect()},[path])
return(<div ref={containerRef} onClick={onClick} className={cn("aspect-square rounded-lg overflow-hidden cursor-pointer transition-all duration-200 hover:ring-2 hover:ring-primary/50",isSelected?"ring-2 ring-primary shadow-lg bg-primary/5":"border border-border/30 hover:border-border")}>{loading?(<div className="w-full h-full flex items-center justify-center bg-muted/20"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground/30"/></div>):src?(<img src={src} alt="" className="w-full h-full object-cover"/>):(<div className="w-full h-full bg-muted/20"/>)}</div>)}
export function ImageGrid(){
const{currentBatch,selectedIndex,setSelectedIndex,setBrowseMode}=useWorkstation()
const handleClick=(index:number)=>{setSelectedIndex(index);setBrowseMode('preview')}
if(currentBatch.length===0)return(<div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">No images to display</div>)
return(<div className="flex-1 overflow-auto p-4"><div className="grid grid-cols-[repeat(auto-fill,minmax(120px,1fr))] gap-3">{currentBatch.map((img,i)=>(<GridThumb key={img.id} path={img.originalPath||img.path||''} isSelected={i===selectedIndex} onClick={()=>handleClick(i)}/>))}</div></div>)}
