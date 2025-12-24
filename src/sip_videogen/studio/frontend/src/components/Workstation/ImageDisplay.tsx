//ImageDisplay component - displays the currently selected image with transitions
import{useState,useEffect,useRef}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import{Loader2}from'lucide-react'
export function ImageDisplay(){
const{currentBatch,selectedIndex}=useWorkstation()
const currentImage=currentBatch[selectedIndex]
const[isLoading,setIsLoading]=useState(true)
const[isVisible,setIsVisible]=useState(false)
const prevIdRef=useRef<string|null>(null)
//Handle image transition on selection change
useEffect(()=>{if(!currentImage)return;if(prevIdRef.current!==currentImage.id){setIsVisible(false);setIsLoading(true);const t=setTimeout(()=>setIsVisible(true),50);prevIdRef.current=currentImage.id;return()=>clearTimeout(t)}},
[currentImage])
const handleLoad=()=>{setIsLoading(false)}
if(!currentImage)return null
const src=currentImage.path.startsWith('/')?`file://${currentImage.path}`:currentImage.path
return(<div className="flex-1 flex items-center justify-center p-4 bg-secondary/10 dark:bg-secondary/5 relative">{isLoading&&(<div className="absolute inset-0 flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground/50"/></div>)}<img src={src} alt={currentImage.prompt||'Generated image'} onLoad={handleLoad} className={`max-w-full max-h-full object-contain rounded-lg shadow-md transition-all duration-300 ease-out ${isVisible&&!isLoading?'opacity-100 scale-100':'opacity-0 scale-95'}`}/></div>)}
