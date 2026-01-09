//ImageBatchCard - shows loading/completed/failed states for batch image generation
import{useState,useEffect}from'react'
import{Check,ImageIcon}from'lucide-react'
import{Spinner}from'@/components/ui/spinner'
import{bridge,isPyWebView}from'@/lib/bridge'
import type{ImageProgressEvent}from'@/lib/bridge'
interface Props{tickets:Map<string,ImageProgressEvent>;expectedCount:number}
//Strip file:// prefix from path
function normalizePath(p:string):string{return p.startsWith('file://')?p.slice(7):p}
export function ImageBatchCard({tickets,expectedCount}:Props){
const[loadedUrls,setLoadedUrls]=useState<Map<string,string>>(new Map())
//Load images via bridge.getImageData when completed tickets have paths
useEffect(()=>{
const toLoad=Array.from(tickets.values()).filter(t=>t.status==='completed'&&(t.rawPath||t.path)&&!loadedUrls.has(t.ticketId))
if(toLoad.length===0)return
let cancelled=false
const loadImages=async()=>{
for(const ticket of toLoad){
if(cancelled)break
const rawPath=ticket.rawPath||normalizePath(ticket.path||'')
if(!rawPath)continue
try{
let dataUrl:string|null=null
if(isPyWebView()){dataUrl=await bridge.getImageData(rawPath)}
else{dataUrl=rawPath.startsWith('/')?`file://${rawPath}`:rawPath}
if(!cancelled&&dataUrl){setLoadedUrls(prev=>new Map(prev).set(ticket.ticketId,dataUrl!))}
}catch{/*ignore load errors*/}
}}
loadImages()
return()=>{cancelled=true}
},[tickets,loadedUrls])
if(tickets.size===0&&expectedCount===0)return null
const items=Array.from(tickets.values())
const completed=items.filter(t=>t.status==='completed').length
const failed=items.filter(t=>t.status==='failed').length
const total=Math.max(items.length,expectedCount)
const allDone=items.length>=expectedCount&&items.every(t=>t.status==='completed'||t.status==='failed'||t.status==='cancelled'||t.status==='timeout')
//Build slots - use tickets we have plus placeholders for expected count
const slots:Array<ImageProgressEvent|null>=[]
for(let i=0;i<total;i++){slots.push(items[i]||null)}
return(<div className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-background/80 backdrop-blur-sm p-4">
{/* Header */}
<div className="flex items-center gap-2 mb-3">{!allDone?(<Spinner className="h-4 w-4"/>):(<Check strokeWidth={1.5}className="h-4 w-4 text-primary"/>)}<span className="text-sm font-medium">{!allDone?`Generating ${total} image${total>1?'s':''}...`:failed>0?`Generated ${completed}/${total} images`:`Generated ${total} image${total>1?'s':''}`}</span></div>
{/* Image grid - responsive columns */}
<div className={`grid gap-2 ${total===1?'grid-cols-1':total<=4?'grid-cols-2':'grid-cols-3'}`}>{slots.map((ticket,i)=>{
const dataUrl=ticket?loadedUrls.get(ticket.ticketId):undefined
const isCompleted=ticket?.status==='completed'
const hasPath=!!(ticket?.rawPath||ticket?.path)
return(<div key={ticket?.ticketId||`slot-${i}`}className="aspect-square rounded-md overflow-hidden">{isCompleted&&dataUrl?(<img src={dataUrl}className="w-full h-full object-cover animate-in fade-in duration-300"alt=""loading="lazy"/>):isCompleted&&hasPath?(<div className="w-full h-full bg-neutral-100 dark:bg-neutral-800 relative overflow-hidden"><div className="absolute inset-0 -translate-x-full animate-[shimmer_2s_infinite] bg-gradient-to-r from-transparent via-white/40 dark:via-white/10 to-transparent"/><div className="absolute inset-0 flex items-center justify-center"><ImageIcon strokeWidth={1.5}className="h-6 w-6 text-muted-foreground/30"/></div></div>):ticket?.status==='failed'?(<div className="w-full h-full bg-brand-a10 flex items-center justify-center p-2"><span className="text-xs text-brand-600 dark:text-brand-500 text-center line-clamp-3">{ticket.error||'Failed'}</span></div>):ticket?.status==='cancelled'||ticket?.status==='timeout'?(<div className="w-full h-full bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center"><span className="text-xs text-muted-foreground">{ticket?.status==='timeout'?'Timeout':'Cancelled'}</span></div>):(<div className="w-full h-full bg-neutral-100 dark:bg-neutral-800 relative overflow-hidden"><div className="absolute inset-0 -translate-x-full animate-[shimmer_2s_infinite] bg-gradient-to-r from-transparent via-white/40 dark:via-white/10 to-transparent"/><div className="absolute inset-0 flex items-center justify-center"><ImageIcon strokeWidth={1.5}className="h-6 w-6 text-muted-foreground/30"/></div></div>)}</div>)})}</div>
</div>)}
