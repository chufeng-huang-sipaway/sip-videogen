//ComparisonView component - side-by-side comparison of generated vs source image with animations
import{useState,useEffect}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import{bridge,isPyWebView}from'../../lib/bridge'
import{Loader2}from'lucide-react'
function normalizeImagePath(path:string):string{return path.startsWith('file://')?path.slice('file://'.length):path}
async function resolveFullImageSrc(rawPath:string):Promise<string>{
if(rawPath.startsWith('data:')||rawPath.startsWith('http://')||rawPath.startsWith('https://'))return rawPath
const normalized=normalizeImagePath(rawPath)
if(!isPyWebView())return normalized.startsWith('/')?`file://${normalized}`:normalized
return await bridge.getImageData(normalized)
}
export function ComparisonView(){
const{currentBatch,selectedIndex}=useWorkstation()
const currentImage=currentBatch[selectedIndex]
const[genLoaded,setGenLoaded]=useState(false)
const[srcLoaded,setSrcLoaded]=useState(false)
const[visible,setVisible]=useState(false)
const[genSrc,setGenSrc]=useState<string|null>(null)
const[srcSrc,setSrcSrc]=useState<string|null>(null)
const[genError,setGenError]=useState<string|null>(null)
const[srcError,setSrcError]=useState<string|null>(null)
useEffect(()=>{setGenLoaded(false);setSrcLoaded(false);setVisible(false);const t=setTimeout(()=>setVisible(true),50);return()=>clearTimeout(t)},[currentImage?.id])
useEffect(()=>{let cancelled=false
async function load(){if(!currentImage)return
setGenSrc(null);setGenError(null)
try{const resolved=await resolveFullImageSrc(currentImage.path);if(cancelled)return;setGenSrc(resolved)}catch(e){if(cancelled)return;setGenError(e instanceof Error?e.message:String(e))}}
void load()
return()=>{cancelled=true}},[currentImage?.id,currentImage?.path])
useEffect(()=>{let cancelled=false
async function load(){const sourcePath=currentImage?.sourceTemplatePath
setSrcSrc(null);setSrcError(null)
if(!sourcePath)return
try{const resolved=await resolveFullImageSrc(sourcePath);if(cancelled)return;setSrcSrc(resolved)}catch(e){if(cancelled)return;setSrcError(e instanceof Error?e.message:String(e))}}
void load()
return()=>{cancelled=true}},[currentImage?.sourceTemplatePath])
if(!currentImage)return null
return(<div className="absolute inset-0 flex gap-2 p-4 bg-secondary/10 dark:bg-secondary/5 overflow-hidden"><div className="flex-1 flex flex-col items-center min-h-0"><span className="text-xs text-muted-foreground mb-2 font-medium shrink-0">Generated</span><div className="flex-1 flex items-center justify-center w-full relative min-h-0">{(!genLoaded||!genSrc)&&!genError&&<Loader2 className="absolute w-6 h-6 animate-spin text-muted-foreground/50"/>}{genError&&<div className="text-sm text-muted-foreground">{genError}</div>}{genSrc&&(<img src={genSrc} alt={currentImage.prompt||'Generated image'} onLoad={()=>setGenLoaded(true)} onError={()=>{setGenLoaded(false);setGenError('Failed to load image')}} className={`max-w-full max-h-full object-contain rounded-lg shadow-md transition-all duration-300 ${visible&&genLoaded&&!genError?'opacity-100 scale-100':'opacity-0 scale-95'}`}/>)}</div></div><div className="flex-1 flex flex-col items-center min-h-0"><span className="text-xs text-muted-foreground mb-2 font-medium shrink-0">Original</span><div className="flex-1 flex items-center justify-center w-full relative min-h-0">{srcSrc?(<>{(!srcLoaded||!srcSrc)&&!srcError&&<Loader2 className="absolute w-6 h-6 animate-spin text-muted-foreground/50"/>}{srcError&&<div className="text-sm text-muted-foreground">{srcError}</div>}<img src={srcSrc} alt="Source template" onLoad={()=>setSrcLoaded(true)} onError={()=>{setSrcLoaded(false);setSrcError('Failed to load source')}} className={`max-w-full max-h-full object-contain rounded-lg shadow-md transition-all duration-300 ${visible&&srcLoaded&&!srcError?'opacity-100 scale-100':'opacity-0 scale-95'}`}/></>):(<div className={`flex flex-col items-center justify-center text-muted-foreground transition-opacity duration-300 ${visible?'opacity-100':'opacity-0'}`}><svg className="w-12 h-12 mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg><span className="text-sm">{srcError||'Source not available'}</span></div>)}</div></div></div>)}
