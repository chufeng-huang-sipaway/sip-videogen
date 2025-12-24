//ThumbnailStrip component - horizontal thumbnail navigation for image batch with animations
import{useState}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import{cn}from'../../lib/utils'
export function ThumbnailStrip(){
const{currentBatch,selectedIndex,setSelectedIndex}=useWorkstation()
const[loadedIds,setLoadedIds]=useState<Set<string>>(new Set())
if(currentBatch.length<=1)return null
const handleLoad=(id:string)=>setLoadedIds(s=>new Set(s).add(id))
return(<div className="flex-shrink-0 border-t border-border/50 bg-secondary/5"><div className="flex gap-2 p-2 overflow-x-auto scrollbar-thin scrollbar-thumb-muted-foreground/20 scrollbar-track-transparent">{currentBatch.map((img,i)=>{const src=img.path.startsWith('/')?`file://${img.path}`:img.path;const isLoaded=loadedIds.has(img.id)
return(<button key={img.id} onClick={()=>setSelectedIndex(i)} className={cn("flex-shrink-0 w-16 h-16 rounded-md overflow-hidden border-2 transition-all duration-200 hover:border-primary/50 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-primary/50 bg-muted/30",i===selectedIndex?"border-primary shadow-md scale-105":"border-transparent")}><img src={src} alt={img.prompt||`Image ${i+1}`} onLoad={()=>handleLoad(img.id)} className={cn("w-full h-full object-cover transition-opacity duration-200",isLoaded?"opacity-100":"opacity-0")}/></button>)})}</div></div>)}
