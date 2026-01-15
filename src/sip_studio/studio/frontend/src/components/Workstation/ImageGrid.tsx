//ImageGrid component - grid view of all images in current batch for efficient browsing
import{useState,useEffect,useRef}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import{useDrag}from'../../context/DragContext'
import{bridge,isPyWebView}from'../../lib/bridge'
import{cn}from'../../lib/utils'
import{Skeleton}from'../ui/skeleton'
//Thumbnail cache shared across grid
const gridThumbCache=new Map<string,string>()
function GridThumb({path,isSelected,isUnread,onClick}:{path:string;isSelected:boolean;isUnread:boolean;onClick:()=>void}){
const{setDragData,clearDrag}=useDrag()
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
const handleDragStart=(e:React.DragEvent)=>{if(!path||path.startsWith('data:'))return;
//Create drag image from thumbnail
const container=e.currentTarget as HTMLElement;const img=container.querySelector('img');if(img&&img.naturalWidth>0){const size=80,canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');if(ctx){const scale=Math.min(size/img.naturalWidth,size/img.naturalHeight);canvas.width=img.naturalWidth*scale;canvas.height=img.naturalHeight*scale;ctx.drawImage(img,0,0,canvas.width,canvas.height);e.dataTransfer.setDragImage(canvas,canvas.width/2,canvas.height/2)}}
e.dataTransfer.setData('text/plain',path);try{e.dataTransfer.setData('text/uri-list',path)}catch{/*ignore*/}try{e.dataTransfer.setData('application/x-brand-asset',path)}catch{/*ignore*/}e.dataTransfer.effectAllowed='copy';setDragData({type:'asset',path})}
const handleDragEnd=()=>clearDrag()
return(<div ref={containerRef} draggable={!!path&&!path.startsWith('data:')} onDragStart={handleDragStart} onDragEnd={handleDragEnd} onClick={onClick} className={cn("aspect-square rounded-lg overflow-hidden cursor-grab active:cursor-grabbing transition-all duration-200 hover:ring-2 hover:ring-primary/50 relative",isSelected?"ring-2 ring-primary shadow-lg bg-primary/5":"border border-border/30 hover:border-border")}>{loading?(<Skeleton className="w-full h-full"/>):src?(<img src={src} alt="" className="w-full h-full object-cover"/>):(<div className="w-full h-full bg-muted/20"/>)}{isUnread&&<div className="absolute top-1 right-1 w-3 h-3 bg-brand-500 rounded-full border-2 border-background shadow-sm"/>}</div>)}
export function ImageGrid(){
const{currentBatch,selectedIndex,setSelectedIndex,setBrowseMode}=useWorkstation()
const handleClick=(index:number)=>{setSelectedIndex(index);setBrowseMode('preview')}
if(currentBatch.length===0)return(<div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">No images to display</div>)
return(<div className="flex-1 overflow-auto p-4"><div className="grid grid-cols-[repeat(auto-fill,minmax(120px,1fr))] gap-3">{currentBatch.map((img,i)=>(<GridThumb key={img.id} path={img.originalPath||img.path||''} isSelected={i===selectedIndex} isUnread={img.viewedAt===null} onClick={()=>handleClick(i)}/>))}</div></div>)}
