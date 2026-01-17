import { Button } from '@/components/ui/button'
import { Telescope } from 'lucide-react'
import type { ResearchResult } from '@/lib/bridge'
//Extract title from report (first H1 or fallback)
function extractTitle(content:string):string{
const m=content.match(/^#\s+(.+)$/m)
return m?m[1].trim():'Research Complete'
}
//Extract executive summary (first 2-3 lines after title)
function extractSummary(content:string,maxLen=200):string{
const lines=content.split('\n').filter(l=>l.trim()&&!l.startsWith('#'))
const text=lines.slice(0,3).join(' ').trim()
return text.length>maxLen?text.slice(0,maxLen-3)+'...':text
}
interface Props {
research:ResearchResult
query:string
onViewReport:()=>void
}
export function DeepResearchCard({research,query,onViewReport}:Props){
const content=research.fullReport||research.finalSummary||''
const title=extractTitle(content)
const summary=extractSummary(content)
const sourceCount=research.sources?.length||0
return(
<div className="rounded-2xl border border-white/20 bg-white/80 dark:bg-black/60 backdrop-blur-xl p-6 shadow-float w-full max-w-md animate-fade-in-up relative overflow-hidden group">
{/* Subtle gradient overlay */}
<div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none"/>
<div className="flex flex-col space-y-4 relative z-10">
{/* Header with icon */}
<div className="flex items-start gap-3">
<div className="relative shrink-0">
<div className="absolute inset-0 bg-brand-500/20 blur-xl rounded-full"/>
<Telescope className="h-6 w-6 text-brand-500 relative z-10"/>
</div>
<div className="flex-1 min-w-0">
<h3 className="font-medium text-base leading-tight line-clamp-1">{title}</h3>
<p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{query}</p>
</div>
</div>
{/* Executive summary */}
{summary&&(<p className="text-sm text-foreground/80 leading-relaxed line-clamp-3">{summary}</p>)}
{/* Footer with sources count and action */}
<div className="flex items-center justify-between pt-2">
<span className="text-xs text-muted-foreground">{sourceCount>0?`${sourceCount} source${sourceCount>1?'s':''}`:''}</span>
<Button size="sm" onClick={onViewReport} className="bg-brand-500 hover:bg-brand-600 shadow-lg shadow-brand-500/20">View Full Report</Button>
</div>
</div>
</div>
)}
