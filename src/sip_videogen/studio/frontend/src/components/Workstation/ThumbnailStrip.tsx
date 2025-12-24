//ThumbnailStrip component - horizontal thumbnail navigation for image batch
import{useWorkstation}from'../../context/WorkstationContext'
import{cn}from'../../lib/utils'
export function ThumbnailStrip(){
const{currentBatch,selectedIndex,setSelectedIndex}=useWorkstation()
if(currentBatch.length<=1)return null
return(<div className="flex-shrink-0 border-t border-border/50 bg-secondary/5"><div className="flex gap-2 p-2 overflow-x-auto scrollbar-thin scrollbar-thumb-muted-foreground/20 scrollbar-track-transparent">{currentBatch.map((img,i)=>{const src=img.path.startsWith('/')?`file://${img.path}`:img.path
return(<button key={img.id} onClick={()=>setSelectedIndex(i)} className={cn("flex-shrink-0 w-16 h-16 rounded-md overflow-hidden border-2 transition-all hover:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/50",i===selectedIndex?"border-primary shadow-md":"border-transparent")}><img src={src} alt={img.prompt||`Image ${i+1}`} className="w-full h-full object-cover"/></button>)})}</div></div>)}
