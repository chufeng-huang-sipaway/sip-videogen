import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Telescope, X } from 'lucide-react'
import type { PendingResearch } from '@/lib/bridge'
interface Props {research:PendingResearch&{status?:string;progressPercent?:number|null};onDismiss:()=>void;onViewResults?:()=>void}
export function ResearchProgress({research,onDismiss,onViewResults}:Props){
const elapsed=Math.max(0,Math.floor((Date.now()-new Date(research.startedAt).getTime())/60000))
const progressValue=research.progressPercent??undefined
const isComplete=research.status==='completed'
const isFailed=research.status==='failed'
return(
<div className="rounded-xl border border-border bg-card p-4 space-y-3 shadow-soft">
<div className="flex items-center justify-between">
<div className="flex items-center gap-2">
<Telescope className={`h-5 w-5 text-brand-500 ${!isComplete&&!isFailed?'animate-pulse':''}`}/>
<span className="font-medium">{isComplete?'Deep Research Complete':isFailed?'Deep Research Failed':'Deep Research in Progress'}</span>
</div>
<Button variant="ghost" size="icon" onClick={onDismiss} className="h-7 w-7"><X className="h-4 w-4"/></Button>
</div>
<p className="text-sm text-muted-foreground line-clamp-2">{research.query}</p>
{!isComplete&&!isFailed&&(<div className="space-y-1">
<Progress value={progressValue} className="h-1"/>
<div className="flex justify-between text-xs text-muted-foreground">
<span>{elapsed} min elapsed</span>
<span>Est. {research.estimatedMinutes} min</span>
</div>
</div>)}
{!isComplete&&!isFailed&&(<p className="text-xs text-warning">⚠️ Research continues in background. You can continue chatting.</p>)}
{isComplete&&onViewResults&&(<Button size="sm" onClick={onViewResults}>View Results</Button>)}
{isFailed&&(<p className="text-xs text-destructive">Research failed. Please try again.</p>)}
</div>)}
