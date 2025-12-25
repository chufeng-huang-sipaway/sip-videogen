//ThumbnailStrip component - horizontal thumbnail navigation for image batch with animations
import{useCallback}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import{useThumbnailLoader}from'../../hooks/useThumbnailLoader'
import{bridge,isPyWebView}from'../../lib/bridge'
import{cn}from'../../lib/utils'
function normalizeImagePath(path:string):string{return path.startsWith('file://')?path.slice('file://'.length):path}
function Thumb({path,alt}:{path:string;alt:string}){
const normalized=normalizeImagePath(path)
const loadFn=useCallback(async(p:string)=>{
if(p.startsWith('data:')||p.startsWith('http://')||p.startsWith('https://'))return p
if(!isPyWebView())return p.startsWith('/')?`file://${p}`:p
return await bridge.getImageThumbnail(p)
},[])
const{src,isLoading,hasError,containerRef}=useThumbnailLoader(normalized,loadFn)
return(<div ref={containerRef} className="w-full h-full">{src&&!hasError?(<img src={src} alt={alt} className={cn("w-full h-full object-cover transition-opacity duration-200",!isLoading?"opacity-100":"opacity-0")}/>):(<div className="w-full h-full bg-muted/30"/>)}</div>)
}
export function ThumbnailStrip(){
const{currentBatch,selectedIndex,setSelectedIndex}=useWorkstation()
if(currentBatch.length<=1)return null
return(<div className="flex-shrink-0 border-t border-border/50 bg-secondary/5"><div className="flex gap-2 p-2 overflow-x-auto scrollbar-thin scrollbar-thumb-muted-foreground/20 scrollbar-track-transparent">{currentBatch.map((img,i)=>(<button key={img.id} onClick={()=>setSelectedIndex(i)} className={cn("flex-shrink-0 w-16 h-16 rounded-md overflow-hidden border-2 transition-all duration-200 hover:border-primary/50 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-primary/50 bg-muted/30",i===selectedIndex?"border-primary shadow-md scale-105":"border-transparent")}><Thumb path={img.path} alt={img.prompt||`Image ${i+1}`}/></button>))}</div></div>)}
