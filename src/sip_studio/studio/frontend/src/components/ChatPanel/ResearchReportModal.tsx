import {Dialog,DialogContent,DialogHeader,DialogTitle} from '@/components/ui/dialog'
import {MarkdownContent} from './MarkdownContent'
import type {ResearchResult} from '@/lib/bridge'
import {ExternalLink,Telescope} from 'lucide-react'
interface Props{
research:ResearchResult|null
query:string
onClose:()=>void
}
export function ResearchReportModal({research,query,onClose}:Props){
if(!research)return null
const content=research.fullReport||research.finalSummary||''
const sources=research.sources||[]
return(
<Dialog open={!!research} onOpenChange={()=>onClose()}>
<DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
<DialogHeader>
<div className="flex items-center gap-2">
<Telescope className="h-5 w-5 text-brand-500"/>
<DialogTitle>Deep Research Report</DialogTitle>
</div>
{query&&<p className="text-sm text-muted-foreground mt-1">Query: {query}</p>}
</DialogHeader>
<div className="space-y-6 mt-4">
{/* Main report content */}
<div className="prose prose-sm dark:prose-invert max-w-none">
<MarkdownContent content={content}/>
</div>
{/* Sources section */}
{sources.length>0&&(
<div className="border-t pt-4">
<h4 className="text-sm font-medium text-muted-foreground mb-3">Sources ({sources.length})</h4>
<div className="grid gap-2">
{sources.map((src,i)=>(
<a key={`${src.url}-${i}`} href={src.url} target="_blank" rel="noopener noreferrer" className="flex items-start gap-2 p-2 rounded-lg hover:bg-muted/50 transition-colors group">
<ExternalLink className="h-4 w-4 shrink-0 mt-0.5 text-muted-foreground group-hover:text-primary"/>
<div className="min-w-0 flex-1">
<div className="text-sm font-medium text-foreground group-hover:text-primary line-clamp-1">{src.title||src.url}</div>
{src.snippet&&<div className="text-xs text-muted-foreground line-clamp-2 mt-0.5">{src.snippet}</div>}
<div className="text-xs text-muted-foreground/60 truncate mt-0.5">{src.url}</div>
</div>
</a>
))}
</div>
</div>
)}
</div>
</DialogContent>
</Dialog>
)}
