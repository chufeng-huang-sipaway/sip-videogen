//ThumbnailStrip component - horizontal thumbnail navigation for image batch with animations
import{useState,useEffect,useRef}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import{bridge,isPyWebView}from'../../lib/bridge'
import{cn}from'../../lib/utils'
import{Loader2}from'lucide-react'
//Simple cache for thumbnails
const thumbCache=new Map<string,string>()
function Thumb({path}:{path:string}){
const[src,setSrc]=useState<string|null>(()=>thumbCache.get(path)??null)
const[loading,setLoading]=useState(!thumbCache.has(path))
const mountedRef=useRef(true)
useEffect(()=>{mountedRef.current=true;return()=>{mountedRef.current=false}},[])
useEffect(()=>{if(!path){setLoading(false);return}
if(thumbCache.has(path)){setSrc(thumbCache.get(path)!);setLoading(false);return}
if(path.startsWith('data:')){setSrc(path);setLoading(false);return}
if(!isPyWebView()){setLoading(false);return}
let cancelled=false
async function load(){try{const dataUrl=await bridge.getAssetThumbnail(path)
if(cancelled||!mountedRef.current)return
thumbCache.set(path,dataUrl);setSrc(dataUrl)}catch(e){console.error('Thumb load error:',e)}finally{if(!cancelled&&mountedRef.current)setLoading(false)}}
void load();return()=>{cancelled=true}},[path])
return(<div className="w-full h-full flex items-center justify-center bg-muted/20">{loading?(<Loader2 className="w-3 h-3 animate-spin text-muted-foreground/30"/>):src?(<img src={src} alt="" className="w-full h-full object-cover"/>):null}</div>)
}
export function ThumbnailStrip(){
const{currentBatch,selectedIndex,setSelectedIndex}=useWorkstation()
const btnRefs=useRef<(HTMLButtonElement|null)[]>([])
//Auto-center selected thumbnail
useEffect(()=>{const btn=btnRefs.current[selectedIndex];if(btn)btn.scrollIntoView({behavior:'smooth',inline:'center',block:'nearest'})},[selectedIndex])
if(currentBatch.length<=1)return null
return(<div className="flex-shrink-0 border-t border-border/50 bg-background/50"><div className="flex gap-1.5 p-3 overflow-x-auto scrollbar-thin scrollbar-thumb-muted-foreground/20 scrollbar-track-transparent">{currentBatch.map((img,i)=>(<button key={img.id} ref={el=>{btnRefs.current[i]=el}} onClick={()=>setSelectedIndex(i)} className={cn("flex-shrink-0 w-14 h-14 rounded-lg overflow-hidden border-2 transition-all duration-200 hover:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/50",i===selectedIndex?"border-primary shadow-lg ring-2 ring-primary/20":"border-border/30 hover:border-border")}><Thumb path={img.originalPath||img.path||''}/></button>))}</div></div>)}
