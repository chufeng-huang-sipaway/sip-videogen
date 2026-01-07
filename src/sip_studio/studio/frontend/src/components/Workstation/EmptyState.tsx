//EmptyState component - shown when workstation has no images to review with fade-in
import{useEffect,useState}from'react'
import{ImageIcon}from'lucide-react'
export function EmptyState(){
const[visible,setVisible]=useState(false)
useEffect(()=>{const t=setTimeout(()=>setVisible(true),100);return()=>clearTimeout(t)},[])
return(<div className={`flex-1 flex items-center justify-center p-8 transition-opacity duration-300 ${visible?'opacity-100':'opacity-0'}`}><div className="text-center max-w-sm"><div className={`inline-flex items-center justify-center w-16 h-16 rounded-full bg-muted/50 mb-4 transition-transform duration-500 ${visible?'scale-100':'scale-90'}`}><ImageIcon className="w-8 h-8 text-muted-foreground/60"/></div><h2 className="text-lg font-medium text-muted-foreground mb-2">No images to review</h2><p className="text-sm text-muted-foreground/60 leading-relaxed">Generate images using the chat, or select from sidebar</p></div></div>)}
