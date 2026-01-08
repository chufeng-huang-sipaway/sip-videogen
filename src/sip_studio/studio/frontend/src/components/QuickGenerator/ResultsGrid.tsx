//ResultsGrid - grid of generated images with download/send actions
import{useState,useEffect}from'react'
import{Download,Send,AlertCircle,Image as ImageIcon}from'lucide-react'
import{Button}from'@/components/ui/button'
import{ScrollArea}from'@/components/ui/scroll-area'
import{bridge,isPyWebView}from'@/lib/bridge'
import type{GeneratedImageEntry}from'@/hooks/useQuickGenerator'
interface ResultsGridProps{
images:GeneratedImageEntry[]
errors:string[]
onDownloadAll:()=>Promise<void>
onSendToChat:(paths:string[])=>void
isGenerating:boolean}
export function ResultsGrid({images,errors,onDownloadAll,onSendToChat,isGenerating}:ResultsGridProps){
const[thumbnails,setThumbnails]=useState<Record<string,string>>({})
const[selectedPaths,setSelectedPaths]=useState<string[]>([])
//Load thumbnails for generated images
useEffect(()=>{
if(!isPyWebView())return
images.forEach(async(img)=>{
if(thumbnails[img.path])return
try{const dataUrl=await bridge.getImageThumbnail(img.path);setThumbnails(prev=>({...prev,[img.path]:dataUrl}))}
catch{}})},[images,thumbnails])
const toggleSelect=(path:string)=>{
setSelectedPaths(prev=>prev.includes(path)?prev.filter(p=>p!==path):[...prev,path])}
const selectAll=()=>{setSelectedPaths(images.map(i=>i.path))}
const deselectAll=()=>{setSelectedPaths([])}
const handleSend=()=>{
if(selectedPaths.length===0)return
onSendToChat(selectedPaths)
setSelectedPaths([])}
if(images.length===0&&errors.length===0&&!isGenerating)return null
return(<div className="flex flex-col gap-3 mt-4">
{errors.length>0&&(<div className="flex flex-col gap-1">
{errors.map((err,i)=>(<div key={i} className="flex items-center gap-2 text-xs text-destructive bg-destructive/10 rounded px-2 py-1">
<AlertCircle className="h-3 w-3"/>
<span className="truncate">{err}</span>
</div>))}
</div>)}
{images.length>0&&(<>
<div className="flex items-center justify-between">
<span className="text-xs text-muted-foreground">{images.length} image{images.length!==1?'s':''} generated</span>
<div className="flex items-center gap-1">
<Button variant="ghost" size="sm" onClick={selectedPaths.length===images.length?deselectAll:selectAll} className="h-6 px-2 text-xs">
{selectedPaths.length===images.length?'Deselect All':'Select All'}
</Button>
</div>
</div>
<ScrollArea className="max-h-64">
<div className="grid grid-cols-3 gap-2 pr-2">
{images.map((img)=>{
const thumb=thumbnails[img.path]
const selected=selectedPaths.includes(img.path)
return(<div key={img.path} onClick={()=>toggleSelect(img.path)} className={`relative aspect-square rounded-lg border-2 cursor-pointer overflow-hidden transition-all ${selected?'border-primary ring-2 ring-primary/20':'border-border hover:border-primary/50'}`}>
{thumb?(<img src={thumb} alt="" className="w-full h-full object-cover"/>):(<div className="w-full h-full flex items-center justify-center bg-muted">
<ImageIcon className="h-6 w-6 text-muted-foreground/50"/>
</div>)}
{selected&&(<div className="absolute top-1 right-1 w-5 h-5 rounded-full bg-primary flex items-center justify-center">
<span className="text-xs text-primary-foreground font-medium">✓</span>
</div>)}
</div>)})}
</div>
</ScrollArea>
<div className="flex items-center gap-2 pt-2">
<Button variant="outline" size="sm" onClick={onDownloadAll} disabled={images.length===0||isGenerating} className="gap-1.5 flex-1">
<Download className="h-3.5 w-3.5"/>Download All
</Button>
<Button variant="outline" size="sm" onClick={handleSend} disabled={selectedPaths.length===0||isGenerating} className="gap-1.5 flex-1">
<Send className="h-3.5 w-3.5"/>Send to Chat
</Button>
</div>
</>)}
</div>)}
