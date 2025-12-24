//TrashView component - displays trashed images with restore/delete options
import{useCallback,useMemo}from'react'
import{useWorkstation,type GeneratedImage}from'../../context/WorkstationContext'
import{useBrand}from'../../context/BrandContext'
import{bridge}from'../../lib/bridge'
import{Button}from'../ui/button'
import{Tooltip,TooltipContent,TooltipProvider,TooltipTrigger}from'../ui/tooltip'
import{RotateCcw,Trash2,ArrowLeft}from'lucide-react'
interface TrashViewProps{onExit:()=>void}
export function TrashView({onExit}:TrashViewProps){
const{currentBatch,selectedIndex,setCurrentBatch,setSelectedIndex}=useWorkstation()
const{activeBrand}=useBrand()
const currentImage=currentBatch[selectedIndex]
//Calculate days until deletion (30 days from trashedAt)
const daysRemaining=useMemo(()=>{if(!currentImage)return null
const img=currentImage as GeneratedImage&{trashedAt?:string}
if(!img.trashedAt)return null
try{const trashedDate=new Date(img.trashedAt);const now=new Date();const diffMs=now.getTime()-trashedDate.getTime();const daysPassed=Math.floor(diffMs/(1000*60*60*24));return Math.max(0,30-daysPassed)}catch{return null}},[currentImage])
//Restore current image
const handleRestore=useCallback(async()=>{if(!currentImage||!activeBrand)return
try{await bridge.restoreImage(currentImage.id,activeBrand)
const newBatch=[...currentBatch];newBatch.splice(selectedIndex,1);setCurrentBatch(newBatch)
if(selectedIndex>=newBatch.length&&newBatch.length>0)setSelectedIndex(newBatch.length-1)
if(newBatch.length===0)onExit()}catch(e){console.error('Failed to restore image:',e)}},[currentImage,activeBrand,currentBatch,selectedIndex,setCurrentBatch,setSelectedIndex,onExit])
//Empty all trash
const handleEmptyTrash=useCallback(async()=>{if(!activeBrand)return
if(!window.confirm('Permanently delete all trashed images? This cannot be undone.'))return
try{await bridge.emptyTrash(activeBrand);setCurrentBatch([]);onExit()}catch(e){console.error('Failed to empty trash:',e)}},[activeBrand,setCurrentBatch,onExit])
if(currentBatch.length===0)return(<div className="flex-1 flex flex-col items-center justify-center text-muted-foreground"><Trash2 className="w-12 h-12 mb-4 opacity-50"/><p className="text-sm font-medium">Trash is empty</p><Button variant="ghost" size="sm" className="mt-4 gap-2" onClick={onExit}><ArrowLeft className="w-4 h-4"/>Back to Workstation</Button></div>)
return(<TooltipProvider><div className="flex-1 flex flex-col">
{/* Header */}
<div className="flex items-center justify-between px-4 py-2 border-b border-border/50 bg-background/50">
<div className="flex items-center gap-3"><Button variant="ghost" size="icon" className="h-8 w-8" onClick={onExit}><ArrowLeft className="w-4 h-4"/></Button><div className="flex items-center gap-2"><Trash2 className="w-4 h-4 text-muted-foreground"/><span className="text-sm font-medium">Trash</span><span className="text-xs text-muted-foreground">({currentBatch.length} items)</span></div></div>
<div className="flex items-center gap-2">
<Tooltip><TooltipTrigger asChild><Button variant="outline" size="sm" className="gap-1.5" onClick={handleRestore} disabled={!currentImage}><RotateCcw className="w-3.5 h-3.5"/>Restore</Button></TooltipTrigger><TooltipContent>Restore to unsorted</TooltipContent></Tooltip>
<Tooltip><TooltipTrigger asChild><Button variant="destructive" size="sm" className="gap-1.5" onClick={handleEmptyTrash}><Trash2 className="w-3.5 h-3.5"/>Empty Trash</Button></TooltipTrigger><TooltipContent>Permanently delete all</TooltipContent></Tooltip>
</div></div>
{/* Main image display */}
<div className="flex-1 relative flex items-center justify-center p-4 bg-secondary/20">
{currentImage&&(<><img src={`file://${currentImage.path}`} alt="Trashed image" className="max-w-full max-h-full object-contain rounded-lg shadow-lg"/>
{/* Days remaining badge */}
{daysRemaining!==null&&(<div className={`absolute bottom-6 left-1/2 -translate-x-1/2 px-3 py-1.5 rounded-full text-xs font-medium ${daysRemaining<=7?'bg-destructive/90 text-destructive-foreground':'bg-muted/90 text-muted-foreground'}`}>{daysRemaining===0?'Deleting today':daysRemaining===1?'1 day until deletion':`${daysRemaining} days until deletion`}</div>)}</>)}
</div>
{/* Thumbnail strip */}
{currentBatch.length>1&&(<div className="flex gap-2 p-3 overflow-x-auto border-t border-border/50 bg-background/50">{currentBatch.map((img,i)=>(<button key={img.id} onClick={()=>setSelectedIndex(i)} className={`flex-shrink-0 w-16 h-16 rounded-lg overflow-hidden border-2 transition-all ${i===selectedIndex?'border-primary shadow-md':'border-transparent hover:border-muted-foreground/30'}`}><img src={`file://${img.path}`} alt="" className="w-full h-full object-cover"/></button>))}</div>)}
</div></TooltipProvider>)}
