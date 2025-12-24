//ComparisonView component - side-by-side comparison of generated vs source image with animations
import{useState,useEffect}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import{Loader2}from'lucide-react'
export function ComparisonView(){
const{currentBatch,selectedIndex}=useWorkstation()
const currentImage=currentBatch[selectedIndex]
const[genLoaded,setGenLoaded]=useState(false)
const[srcLoaded,setSrcLoaded]=useState(false)
const[visible,setVisible]=useState(false)
useEffect(()=>{setGenLoaded(false);setSrcLoaded(false);setVisible(false);const t=setTimeout(()=>setVisible(true),50);return()=>clearTimeout(t)},[currentImage?.id])
if(!currentImage)return null
const sourcePath=currentImage.sourceTemplatePath
const genPath=currentImage.path.startsWith('/')?`file://${currentImage.path}`:currentImage.path
const srcPath=sourcePath?(sourcePath.startsWith('/')?`file://${sourcePath}`:sourcePath):null
return(<div className="flex-1 flex gap-2 p-4 bg-secondary/10 dark:bg-secondary/5"><div className="flex-1 flex flex-col items-center"><span className="text-xs text-muted-foreground mb-2 font-medium">Generated</span><div className="flex-1 flex items-center justify-center w-full relative">{!genLoaded&&<Loader2 className="absolute w-6 h-6 animate-spin text-muted-foreground/50"/>}<img src={genPath} alt={currentImage.prompt||'Generated image'} onLoad={()=>setGenLoaded(true)} className={`max-w-full max-h-full object-contain rounded-lg shadow-md transition-all duration-300 ${visible&&genLoaded?'opacity-100 scale-100':'opacity-0 scale-95'}`}/></div></div><div className="flex-1 flex flex-col items-center"><span className="text-xs text-muted-foreground mb-2 font-medium">Original</span><div className="flex-1 flex items-center justify-center w-full relative">{srcPath?(<>{!srcLoaded&&<Loader2 className="absolute w-6 h-6 animate-spin text-muted-foreground/50"/>}<img src={srcPath} alt="Source template" onLoad={()=>setSrcLoaded(true)} className={`max-w-full max-h-full object-contain rounded-lg shadow-md transition-all duration-300 ${visible&&srcLoaded?'opacity-100 scale-100':'opacity-0 scale-95'}`}/></>):(<div className={`flex flex-col items-center justify-center text-muted-foreground transition-opacity duration-300 ${visible?'opacity-100':'opacity-0'}`}><svg className="w-12 h-12 mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg><span className="text-sm">Source not available</span></div>)}</div></div></div>)}
