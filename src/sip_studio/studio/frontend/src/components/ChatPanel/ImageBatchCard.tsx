//ImageBatchCard - shows loading/completed/failed states for batch image generation
import{Check}from'lucide-react'
import{Spinner}from'@/components/ui/spinner'
import type{ImageProgressEvent}from'@/lib/bridge'
interface Props{tickets:Map<string,ImageProgressEvent>;expectedCount:number}
export function ImageBatchCard({tickets,expectedCount}:Props){
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
<div className={`grid gap-2 ${total===1?'grid-cols-1':total<=4?'grid-cols-2':'grid-cols-3'}`}>{slots.map((ticket,i)=>(<div key={ticket?.ticketId||`slot-${i}`}className="aspect-square rounded-md overflow-hidden">{ticket?.status==='completed'&&ticket.path?(<img src={ticket.path}className="w-full h-full object-cover"alt="Generated"loading="lazy"/>):ticket?.status==='failed'?(<div className="w-full h-full bg-brand-a10 flex items-center justify-center p-2"><span className="text-xs text-brand-600 dark:text-brand-500 text-center line-clamp-3">{ticket.error||'Failed'}</span></div>):ticket?.status==='cancelled'||ticket?.status==='timeout'?(<div className="w-full h-full bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center"><span className="text-xs text-muted-foreground">{ticket?.status==='timeout'?'Timeout':'Cancelled'}</span></div>):(<div className="w-full h-full bg-neutral-100 dark:bg-neutral-800 animate-pulse"/>)}</div>))}</div>
</div>)}
